from datetime import date
from pathlib import Path

import pandas as pd

from app.core.config import settings

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def _path_for(asset_id: str, root: Path | None = None) -> Path:
    base = root or settings.data_cache_dir
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{asset_id}.parquet"


def load(asset_id: str, root: Path | None = None) -> pd.DataFrame | None:
    p = _path_for(asset_id, root)
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df


def save(asset_id: str, df: pd.DataFrame, root: Path | None = None) -> Path:
    p = _path_for(asset_id, root)
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df.to_parquet(p, engine="pyarrow")
    return p


def merge_and_save(asset_id: str, new_df: pd.DataFrame, root: Path | None = None) -> pd.DataFrame:
    """Merge new rows with existing cached rows, dedupe on index, save, return merged."""
    existing = load(asset_id, root)
    combined = new_df if existing is None else pd.concat([existing, new_df])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    save(asset_id, combined, root)
    return combined


def covers(df: pd.DataFrame | None, start: date, end: date) -> bool:
    if df is None or df.empty:
        return False
    idx_min = df.index.min().date()
    idx_max = df.index.max().date()
    return idx_min <= start and idx_max >= end
