from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest


def _synthetic_ohlcv(seed: int, n_days: int = 500, start: date = date(2022, 1, 1)) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    daily_log_returns = rng.normal(loc=0.0005, scale=0.03, size=n_days)
    price = 100.0 * np.exp(np.cumsum(daily_log_returns))
    high = price * (1 + np.abs(rng.normal(0, 0.005, n_days)))
    low = price * (1 - np.abs(rng.normal(0, 0.005, n_days)))
    open_ = price + rng.normal(0, 0.5, n_days)
    volume = rng.uniform(1e6, 5e6, n_days)
    idx = pd.DatetimeIndex([start + timedelta(days=i) for i in range(n_days)], name="date")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": price, "volume": volume},
        index=idx,
    )


@pytest.fixture
def synthetic_ohlcv_by_asset() -> dict[str, pd.DataFrame]:
    return {
        "bitcoin": _synthetic_ohlcv(seed=1),
        "ethereum": _synthetic_ohlcv(seed=2),
        "solana": _synthetic_ohlcv(seed=3),
    }
