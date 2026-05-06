from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class DataProvider(ABC):
    """Fetches daily OHLCV history for a single asset.

    Returns a DataFrame indexed by `date` (datetime64[ns]) with columns:
    `open, high, low, close, volume`.
    """

    @abstractmethod
    def fetch(self, asset_id: str, start: date, end: date) -> pd.DataFrame: ...
