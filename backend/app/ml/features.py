"""Feature engineering for the LightGBM classifier.

Inputs: per-asset OHLCV DataFrames (datetime-indexed, columns open/high/low/close/volume).
Outputs: a single long DataFrame with one row per (date, asset_id) and feature columns.

Cross-asset features (BTC context, market breadth) are computed once and broadcast.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.universe import BTC_ID

FEATURE_COLUMNS_NUMERIC: list[str] = [
    "ret_1d", "ret_3d", "ret_7d", "ret_14d", "ret_30d",
    "ret_7d_z", "ret_30d_z",
    "sma_7_ratio", "sma_30_ratio", "sma_90_ratio",
    "ema_12_ratio", "ema_26_ratio",
    "macd", "macd_signal", "macd_hist",
    "roc_10", "roc_20",
    "rsi_14",
    "bb_pctb", "dist_from_high_30", "dist_from_low_30",
    "vol_realized_14", "atr_14_pct", "vol_parkinson_14",
    "volume_z_30", "obv_slope_14", "vw_ret_7d",
    "btc_ret_7d", "btc_vol_30", "corr_btc_30",
    "market_breadth",
    "dow",
]

ALL_FEATURE_COLUMNS: list[str] = FEATURE_COLUMNS_NUMERIC + ["asset_id"]


def _log_returns(close: pd.Series, n: int) -> pd.Series:
    return np.log(close / close.shift(n))


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    diff = close.diff()
    gain = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def _bollinger_pctb(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    upper = ma + k * sd
    lower = ma - k * sd
    return (close - lower) / (upper - lower).replace(0, np.nan)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def _parkinson_vol(high: pd.Series, low: pd.Series, n: int = 14) -> pd.Series:
    log_hl = np.log(high / low.replace(0, np.nan))
    return np.sqrt((1.0 / (4.0 * np.log(2.0))) * (log_hl**2).rolling(n).mean())


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff()).fillna(0)
    return (sign * volume).cumsum()


def _slope(series: pd.Series, n: int) -> pd.Series:
    """Linear-regression slope over a rolling window of n points, normalized by mean."""
    def _fit(window: np.ndarray) -> float:
        if np.any(np.isnan(window)):
            return np.nan
        x = np.arange(len(window), dtype=float)
        denom = (x.std() * window.std()) or np.nan
        if denom != denom or denom == 0:
            return np.nan
        slope = np.cov(x, window, ddof=0)[0, 1] / x.var()
        mean = window.mean() or np.nan
        if mean != mean or mean == 0:
            return np.nan
        return slope / abs(mean)

    return series.rolling(n).apply(_fit, raw=True)


def _per_asset_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-asset features given an OHLCV frame indexed by date."""
    out = pd.DataFrame(index=df.index)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    for n in (1, 3, 7, 14, 30):
        out[f"ret_{n}d"] = _log_returns(close, n)

    rolling_std_30 = _log_returns(close, 1).rolling(30).std()
    out["ret_7d_z"] = out["ret_7d"] / rolling_std_30.replace(0, np.nan)
    out["ret_30d_z"] = out["ret_30d"] / rolling_std_30.replace(0, np.nan)

    for n in (7, 30, 90):
        sma = close.rolling(n).mean()
        out[f"sma_{n}_ratio"] = close / sma.replace(0, np.nan) - 1.0

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    out["ema_12_ratio"] = close / ema_12.replace(0, np.nan) - 1.0
    out["ema_26_ratio"] = close / ema_26.replace(0, np.nan) - 1.0

    macd, signal, hist = _macd(close)
    out["macd"] = macd / close.replace(0, np.nan)
    out["macd_signal"] = signal / close.replace(0, np.nan)
    out["macd_hist"] = hist / close.replace(0, np.nan)

    out["roc_10"] = close.pct_change(10)
    out["roc_20"] = close.pct_change(20)

    out["rsi_14"] = _rsi(close, 14)

    out["bb_pctb"] = _bollinger_pctb(close, 20, 2.0)

    rolling_high_30 = close.rolling(30).max()
    rolling_low_30 = close.rolling(30).min()
    out["dist_from_high_30"] = close / rolling_high_30.replace(0, np.nan) - 1.0
    out["dist_from_low_30"] = close / rolling_low_30.replace(0, np.nan) - 1.0

    daily_log_ret = _log_returns(close, 1)
    out["vol_realized_14"] = daily_log_ret.rolling(14).std()
    out["atr_14_pct"] = _atr(high, low, close, 14) / close.replace(0, np.nan)
    out["vol_parkinson_14"] = _parkinson_vol(high, low, 14)

    vol_mean_30 = volume.rolling(30).mean()
    vol_std_30 = volume.rolling(30).std()
    out["volume_z_30"] = (volume - vol_mean_30) / vol_std_30.replace(0, np.nan)

    obv = _obv(close, volume)
    out["obv_slope_14"] = _slope(obv, 14)

    weights = volume / volume.rolling(7).sum().replace(0, np.nan)
    out["vw_ret_7d"] = (daily_log_ret * weights).rolling(7).sum()

    out["dow"] = pd.Series(out.index.dayofweek, index=out.index, dtype=float)
    return out


def _btc_context(btc_df: pd.DataFrame) -> pd.DataFrame:
    close = btc_df["close"]
    daily_log_ret = _log_returns(close, 1)
    ctx = pd.DataFrame(index=btc_df.index)
    ctx["btc_ret_7d"] = _log_returns(close, 7)
    ctx["btc_vol_30"] = daily_log_ret.rolling(30).std()
    ctx["btc_log_ret_1d"] = daily_log_ret
    return ctx


def build_features(
    ohlcv_by_asset: dict[str, pd.DataFrame],
    asset_id_codes: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Build the long-form feature frame across all assets.

    Parameters
    ----------
    ohlcv_by_asset : dict mapping CoinGecko asset_id -> OHLCV DataFrame.
    asset_id_codes : optional mapping asset_id -> integer code for LightGBM.
        If None, codes are assigned in sorted order of asset_ids.

    Returns
    -------
    DataFrame with a MultiIndex `(date, asset_id)` and columns ALL_FEATURE_COLUMNS.
    """
    if asset_id_codes is None:
        asset_id_codes = {aid: i for i, aid in enumerate(sorted(ohlcv_by_asset))}

    btc_df = ohlcv_by_asset.get(BTC_ID)
    if btc_df is None or btc_df.empty:
        raise ValueError("BTC OHLCV is required for cross-asset features.")
    btc_ctx = _btc_context(btc_df)

    # Market breadth: fraction of universe with close > SMA(30) on each day.
    breadth_components = []
    for aid, df in ohlcv_by_asset.items():
        sma30 = df["close"].rolling(30).mean()
        breadth_components.append((df["close"] > sma30).astype(float).rename(aid))
    breadth_df = pd.concat(breadth_components, axis=1)
    market_breadth = breadth_df.mean(axis=1).astype(float).rename("market_breadth")

    pieces = []
    for aid, df in ohlcv_by_asset.items():
        feat = _per_asset_features(df)
        feat = feat.join(btc_ctx[["btc_ret_7d", "btc_vol_30"]])

        # 30d rolling correlation with BTC daily returns.
        own_ret = _log_returns(df["close"], 1)
        feat["corr_btc_30"] = own_ret.rolling(30).corr(btc_ctx["btc_log_ret_1d"])

        feat = feat.join(market_breadth)
        feat["asset_id"] = asset_id_codes[aid]
        feat.index = pd.MultiIndex.from_product([feat.index, [aid]], names=["date", "asset"])
        pieces.append(feat[ALL_FEATURE_COLUMNS])

    return pd.concat(pieces).sort_index()
