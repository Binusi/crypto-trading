"""Binance public klines DataProvider.

Why Binance vs. CoinGecko free: CoinGecko's free tier caps historical queries
at the last ~365 days (error 10012). Binance's public REST endpoint
`/api/v3/klines` returns full daily OHLCV history with no API key, no
authentication, and a 1200 weight/min rate limit that we never approach for
20 daily symbols.

Universe symbol mapping: every asset in `app/data/universe.py` has a
corresponding `<SYMBOL>USDT` pair on Binance. We hardcode the mapping below.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone

import pandas as pd
import requests

from app.core.config import settings
from app.core.logging import get_logger
from app.data import cache
from app.data.provider import DataProvider
from app.data.universe import by_id

log = get_logger(__name__)

BINANCE_BASE = "https://api.binance.com"
KLINES_LIMIT = 1000

# CoinGecko id -> Binance pair (USDT-quoted).
ID_TO_PAIR: dict[str, str] = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "binancecoin": "BNBUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "cardano": "ADAUSDT",
    "dogecoin": "DOGEUSDT",
    "tron": "TRXUSDT",
    "avalanche-2": "AVAXUSDT",
    "polkadot": "DOTUSDT",
    "matic-network": "MATICUSDT",
    "chainlink": "LINKUSDT",
    "litecoin": "LTCUSDT",
    "bitcoin-cash": "BCHUSDT",
    "near": "NEARUSDT",
    "cosmos": "ATOMUSDT",
    "uniswap": "UNIUSDT",
    "stellar": "XLMUSDT",
    "ethereum-classic": "ETCUSDT",
    "filecoin": "FILUSDT",
}


class BinanceError(RuntimeError):
    pass


class BinanceProvider(DataProvider):
    def __init__(self, base_url: str = BINANCE_BASE, request_delay_s: float = 0.25):
        self.base_url = base_url
        self.delay = request_delay_s
        self._last_call_ts = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call_ts
        wait = self.delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call_ts = time.monotonic()

    def _request(self, path: str, params: dict) -> list:
        url = f"{self.base_url}{path}"
        for attempt in range(5):
            self._throttle()
            try:
                resp = requests.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                log.warning("binance.network_error", attempt=attempt, err=str(e))
                time.sleep(2**attempt)
                continue
            if resp.status_code == 429:
                backoff = 2 ** (attempt + 1)
                log.warning("binance.rate_limited", attempt=attempt, backoff_s=backoff)
                time.sleep(backoff)
                continue
            if resp.status_code >= 500:
                log.warning("binance.server_error", status=resp.status_code, attempt=attempt)
                time.sleep(2**attempt)
                continue
            if resp.status_code != 200:
                raise BinanceError(f"GET {url} -> {resp.status_code}: {resp.text[:200]}")
            return resp.json()
        raise BinanceError(f"Exhausted retries for GET {url}")

    def _fetch_klines(self, pair: str, start: date, end: date) -> pd.DataFrame:
        # Walk forward in 1000-day chunks (Binance's max per call for daily).
        start_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp() * 1000) + 86_400_000

        rows: list[list] = []
        cursor = start_ms
        while cursor < end_ms:
            klines = self._request(
                "/api/v3/klines",
                params={
                    "symbol": pair,
                    "interval": "1d",
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": KLINES_LIMIT,
                },
            )
            if not klines:
                break
            rows.extend(klines)
            last_open = int(klines[-1][0])
            if len(klines) < KLINES_LIMIT:
                break
            cursor = last_open + 86_400_000

        if not rows:
            return pd.DataFrame(columns=cache.OHLCV_COLUMNS, index=pd.DatetimeIndex([], name="date"))

        df = pd.DataFrame(rows, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "n_trades", "taker_base", "taker_quote", "ignore",
        ])
        df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.normalize()
        df = df.set_index("date")
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = df[c].astype(float)
        df = df[cache.OHLCV_COLUMNS]
        # Dedupe in case of overlapping chunks.
        df = df[~df.index.duplicated(keep="last")].sort_index()
        return df

    def fetch(self, asset_id: str, start: date, end: date) -> pd.DataFrame:
        pair = ID_TO_PAIR.get(asset_id)
        if pair is None:
            asset = by_id(asset_id)
            log.warning("binance.unknown_asset", asset=asset_id, name=asset.name if asset else None)
            return pd.DataFrame(columns=cache.OHLCV_COLUMNS, index=pd.DatetimeIndex([], name="date"))

        cached = cache.load(asset_id)
        if cache.covers(cached, start, end):
            return cached.loc[
                (cached.index.date >= start) & (cached.index.date <= end)
            ].copy()

        log.info("binance.fetch", asset=asset_id, pair=pair, start=str(start), end=str(end))
        new_df = self._fetch_klines(pair, start, end)
        if new_df.empty:
            log.warning("binance.empty_response", asset=asset_id, pair=pair)
            if cached is not None:
                return cached.loc[
                    (cached.index.date >= start) & (cached.index.date <= end)
                ].copy()
            return new_df

        merged = cache.merge_and_save(asset_id, new_df)
        return merged.loc[
            (merged.index.date >= start) & (merged.index.date <= end)
        ].copy()
