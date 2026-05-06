import time
from datetime import date, datetime, timezone

import pandas as pd
import requests

from app.core.config import settings
from app.core.logging import get_logger
from app.data import cache
from app.data.provider import DataProvider

log = get_logger(__name__)


class CoinGeckoError(RuntimeError):
    pass


class CoinGeckoProvider(DataProvider):
    """Fetches daily OHLCV from CoinGecko's free `/market_chart/range` endpoint.

    The free endpoint returns daily granularity automatically when the requested
    range is > 90 days. It returns prices, market caps, and total volumes. It
    does NOT return open/high/low — only close. We synthesize OHLC by treating
    `close` as `open=high=low=close` for that day; the technical indicators we
    use only need close + volume in practice (RSI, MACD, BB, returns), with
    high/low only entering the ATR / Parkinson features. ATR computed off
    close-only collapses to absolute close-to-close changes, which is a
    reasonable approximation for a daily simulator.
    """

    def __init__(self, base_url: str | None = None, request_delay_s: float | None = None):
        self.base_url = base_url or settings.coingecko_base_url
        self.delay = request_delay_s if request_delay_s is not None else settings.coingecko_request_delay_s
        self._last_call_ts = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call_ts
        wait = self.delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call_ts = time.monotonic()

    def _request(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}"
        for attempt in range(5):
            self._throttle()
            try:
                resp = requests.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                log.warning("coingecko.network_error", attempt=attempt, err=str(e))
                time.sleep(2**attempt)
                continue
            if resp.status_code == 429:
                backoff = 2 ** (attempt + 1)
                log.warning("coingecko.rate_limited", attempt=attempt, backoff_s=backoff)
                time.sleep(backoff)
                continue
            if resp.status_code >= 500:
                log.warning("coingecko.server_error", status=resp.status_code, attempt=attempt)
                time.sleep(2**attempt)
                continue
            if resp.status_code != 200:
                raise CoinGeckoError(f"GET {url} -> {resp.status_code}: {resp.text[:200]}")
            return resp.json()
        raise CoinGeckoError(f"Exhausted retries for GET {url}")

    def _fetch_range(self, asset_id: str, start: date, end: date) -> pd.DataFrame:
        # CoinGecko's `market_chart/range` expects unix-second timestamps.
        # Pad end by +1 day to ensure inclusive coverage of the end date.
        start_ts = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
        end_dt = datetime(end.year, end.month, end.day, tzinfo=timezone.utc)
        end_ts = int(end_dt.timestamp()) + 86400

        params = {"vs_currency": "usd", "from": start_ts, "to": end_ts}
        data = self._request(f"/coins/{asset_id}/market_chart/range", params=params)

        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        if not prices:
            return pd.DataFrame(columns=cache.OHLCV_COLUMNS, index=pd.DatetimeIndex([], name="date"))

        df_p = pd.DataFrame(prices, columns=["ts_ms", "close"])
        df_p["date"] = pd.to_datetime(df_p["ts_ms"], unit="ms").dt.normalize()
        df_p = df_p.groupby("date", as_index=True)["close"].last()

        df_v = pd.DataFrame(volumes, columns=["ts_ms", "volume"])
        df_v["date"] = pd.to_datetime(df_v["ts_ms"], unit="ms").dt.normalize()
        df_v = df_v.groupby("date", as_index=True)["volume"].sum()

        df = pd.concat([df_p, df_v], axis=1)
        # Synthesize O/H/L from close — see class docstring.
        df["open"] = df["close"]
        df["high"] = df["close"]
        df["low"] = df["close"]
        return df[cache.OHLCV_COLUMNS]

    def fetch(self, asset_id: str, start: date, end: date) -> pd.DataFrame:
        cached = cache.load(asset_id)
        if cache.covers(cached, start, end):
            return cached.loc[
                (cached.index.date >= start) & (cached.index.date <= end)
            ].copy()

        log.info("coingecko.fetch", asset=asset_id, start=str(start), end=str(end))
        new_df = self._fetch_range(asset_id, start, end)
        if new_df.empty:
            log.warning("coingecko.empty_response", asset=asset_id)
            if cached is not None:
                return cached.loc[
                    (cached.index.date >= start) & (cached.index.date <= end)
                ].copy()
            return new_df

        merged = cache.merge_and_save(asset_id, new_df)
        return merged.loc[
            (merged.index.date >= start) & (merged.index.date <= end)
        ].copy()
