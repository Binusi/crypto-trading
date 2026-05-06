from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.core.config import settings
from app.data.provider import DataProvider
from app.data.universe import Asset
from app.ml.features import build_features
from app.ml.labels import make_labels
from app.ml.model import LightGBMModel
from app.simulation.simulator import Simulator


@dataclass
class _StubProvider(DataProvider):
    data: dict[str, pd.DataFrame]

    def fetch(self, asset_id: str, start: date, end: date) -> pd.DataFrame:
        df = self.data.get(asset_id)
        if df is None:
            return pd.DataFrame()
        return df.loc[(df.index.date >= start) & (df.index.date <= end)].copy()


def test_simulator_smoke(synthetic_ohlcv_by_asset):
    ohlcv = synthetic_ohlcv_by_asset
    codes = {aid: i for i, aid in enumerate(sorted(ohlcv))}
    X = build_features(ohlcv, asset_id_codes=codes)
    y = make_labels(ohlcv)
    common = X.index.intersection(y.index)
    X = X.loc[common]
    y = y.loc[common]
    valid = (y >= 0) & X.notna().all(axis=1)
    X = X.loc[valid]
    y = y.loc[valid]

    model = LightGBMModel(asset_id_codes=codes)
    model.fit(X, y, num_boost_round=80, early_stopping_rounds=None, valid_frac=0.1)

    universe = [
        Asset("bitcoin", "BTC", "Bitcoin"),
        Asset("ethereum", "ETH", "Ethereum"),
        Asset("solana", "SOL", "Solana"),
    ]
    provider = _StubProvider(data=ohlcv)
    sim = Simulator(provider=provider, model=model, universe=universe, settings=settings)

    # Pick a window well after warmup.
    first_date = list(ohlcv.values())[0].index.min().date()
    start = date(first_date.year, first_date.month, first_date.day)
    # Step start forward past warmup window.
    start = pd.Timestamp(start).date()
    start = (pd.Timestamp(start) + pd.Timedelta(days=200)).date()
    end = (pd.Timestamp(start) + pd.Timedelta(days=120)).date()

    result = sim.run(start_date=start, end_date=end, starting_capital=10_000.0, confidence_threshold=0.05)
    assert result.starting_capital == 10_000.0
    assert len(result.portfolio_series) > 0
    assert result.portfolio_series[0].value > 0
    assert result.portfolio_series[-1].value > 0
    assert result.summary.n_trades >= 0
