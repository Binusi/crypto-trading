"""Rolling-tertile labels for per-asset Buy / Hold / Sell.

For each (asset, day t), look at the **next-day** log return r_{t+1} and assign
a class based on its tertile within the asset's last `window` days of next-day
returns. This adapts thresholds per asset and per volatility regime, producing
a roughly balanced 3-class problem.

Class encoding: 0 = Sell, 1 = Hold, 2 = Buy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2


def make_labels(
    ohlcv_by_asset: dict[str, pd.DataFrame],
    window: int = 60,
) -> pd.Series:
    """Return a Series indexed by `(date, asset)` with int values 0/1/2.

    The label at row (t, asset) describes the action you'd take at the close
    of day t, evaluated against the realized return from t to t+1.
    """
    pieces = []
    for aid, df in ohlcv_by_asset.items():
        close = df["close"]
        next_log_ret = np.log(close.shift(-1) / close)
        rolled = next_log_ret.rolling(window, min_periods=window // 2)
        q33 = rolled.quantile(1 / 3)
        q66 = rolled.quantile(2 / 3)

        labels = pd.Series(CLASS_HOLD, index=close.index, dtype="int64")
        labels[next_log_ret <= q33] = CLASS_SELL
        labels[next_log_ret >= q66] = CLASS_BUY
        labels[next_log_ret.isna()] = -1

        labels.index = pd.MultiIndex.from_product([labels.index, [aid]], names=["date", "asset"])
        pieces.append(labels)

    return pd.concat(pieces).sort_index().rename("label")
