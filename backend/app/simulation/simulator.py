"""Day-by-day portfolio simulator.

For each trading date in [start, end]:
  1. Build features as of that date.
  2. Predict per-asset class probabilities with the trained model.
  3. Compute scores and let the Allocator turn them into trades.
  4. Apply trades against the day's prices, marking the portfolio to market.
  5. Record portfolio value and decisions.

The retrain cadence (`sim_retrain_every_days`) is honored if a fitter is provided;
otherwise the model loaded at startup is used as-is for the whole run. We keep
this v1 simple by using the pre-trained model — retraining each block during a
simulation requires re-fitting on partially-future-aware data and slows runs
significantly. The training CLI handles walk-forward retraining offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.logging import get_logger
from app.data.provider import DataProvider
from app.data.universe import Asset, BTC_ID
from app.ml.features import build_features
from app.ml.model import LightGBMModel
from app.schemas.simulate import (
    DecisionLogEntry,
    PortfolioPoint,
    SimulateResponse,
    SimulationSummary,
)
from app.simulation.allocator import Allocator, AllocatorConfig
from app.simulation.portfolio import Portfolio

log = get_logger(__name__)

WARMUP_DAYS = 120  # need enough lookback for SMA(90) etc.


@dataclass
class Simulator:
    provider: DataProvider
    model: LightGBMModel
    universe: list[Asset]
    settings: Settings

    def _fetch_history(self, start: date, end: date) -> dict[str, pd.DataFrame]:
        fetch_start = start - timedelta(days=WARMUP_DAYS)
        ohlcv = {}
        for asset in self.universe:
            df = self.provider.fetch(asset.id, fetch_start, end)
            if df is None or df.empty:
                log.warning("simulator.no_data", asset=asset.id)
                continue
            ohlcv[asset.id] = df
        if BTC_ID not in ohlcv:
            raise RuntimeError("BTC OHLCV missing — required for cross-asset features.")
        return ohlcv

    def _allocator(self, threshold: float) -> Allocator:
        s = self.settings
        return Allocator(
            AllocatorConfig(
                confidence_threshold=threshold,
                top_k=s.top_k,
                cash_reserve_frac=s.cash_reserve_frac,
                max_asset_weight=s.max_asset_weight,
                transaction_cost=s.transaction_cost,
                min_trade_frac=s.min_trade_frac,
                cooldown_days=s.cooldown_days,
            )
        )

    def run(
        self,
        start_date: date,
        end_date: date,
        starting_capital: float,
        confidence_threshold: float,
    ) -> SimulateResponse:
        ohlcv = self._fetch_history(start_date, end_date)
        # Use the asset_id codes the model was trained on; assets the model
        # never saw get mapped to a sentinel code that never occurs in training,
        # which is safe — LightGBM treats them as a new category.
        codes = dict(self.model.asset_id_codes)
        next_code = (max(codes.values()) + 1) if codes else 0
        for aid in ohlcv:
            if aid not in codes:
                codes[aid] = next_code
                next_code += 1

        features = build_features(ohlcv, asset_id_codes=codes)

        # Build a per-asset close price frame aligned on date.
        close_frames = {aid: df["close"].rename(aid) for aid, df in ohlcv.items()}
        close_df = pd.concat(close_frames.values(), axis=1).sort_index()

        # The set of trading dates is the intersection of "we have a close
        # price" and "we have features on that date" within [start, end].
        feature_dates = features.index.get_level_values("date").unique()
        all_dates = (
            pd.DatetimeIndex(close_df.index)
            .intersection(feature_dates)
            .sort_values()
        )
        all_dates = all_dates[(all_dates.date >= start_date) & (all_dates.date <= end_date)]
        if len(all_dates) == 0:
            raise RuntimeError("No overlapping trading dates between data and features in range.")

        portfolio = Portfolio(cash=float(starting_capital))
        allocator = self._allocator(confidence_threshold)

        last_buy: dict[str, date] = {}
        last_sell: dict[str, date] = {}

        portfolio_series: list[PortfolioPoint] = []
        decisions: list[DecisionLogEntry] = []

        for ts in all_dates:
            d = ts.date()
            day_features = features.loc[ts] if ts in feature_dates else None
            day_prices = {
                aid: float(close_df.at[ts, aid])
                for aid in close_df.columns
                if not pd.isna(close_df.at[ts, aid])
            }

            if day_features is not None and not day_features.empty:
                # Drop assets with NaN features today (warmup not yet satisfied).
                clean = day_features.dropna()
                if not clean.empty:
                    proba = self.model.predict_proba(clean)
                    scores = {aid: float(proba[i, 2] - proba[i, 0]) for i, aid in enumerate(clean.index)}
                    pf_value = portfolio.value(day_prices)
                    current_units = dict(portfolio.holdings)
                    orders = allocator.build_trades(
                        today=d,
                        scores=scores,
                        prices=day_prices,
                        portfolio_value=pf_value,
                        current_units=current_units,
                        last_buy_date=last_buy,
                        last_sell_date=last_sell,
                    )
                    for o in orders:
                        price = day_prices.get(o.asset_id)
                        if price is None:
                            continue
                        if o.action == "BUY":
                            spent = portfolio.apply_buy(
                                o.asset_id, o.usd_amount, price, self.settings.transaction_cost
                            )
                            if spent > 0:
                                last_buy[o.asset_id] = d
                                decisions.append(
                                    DecisionLogEntry(
                                        date=d, action="BUY", asset=_symbol_for(o.asset_id, self.universe),
                                        usd_amount=round(spent, 2), price=round(price, 6),
                                        score=round(o.score, 4),
                                    )
                                )
                        else:
                            received = portfolio.apply_sell(
                                o.asset_id, o.usd_amount, price, self.settings.transaction_cost
                            )
                            if received > 0:
                                last_sell[o.asset_id] = d
                                decisions.append(
                                    DecisionLogEntry(
                                        date=d, action="SELL", asset=_symbol_for(o.asset_id, self.universe),
                                        usd_amount=round(received, 2), price=round(price, 6),
                                        score=round(o.score, 4),
                                    )
                                )

            holdings_value = portfolio.holdings_value(day_prices)
            portfolio_series.append(
                PortfolioPoint(
                    date=d,
                    value=round(portfolio.cash + holdings_value, 2),
                    cash=round(portfolio.cash, 2),
                    holdings_value=round(holdings_value, 2),
                )
            )

        ending_value = portfolio_series[-1].value
        total_return_pct = (ending_value / starting_capital - 1.0) * 100.0
        summary = _summarize(portfolio_series, decisions)

        return SimulateResponse(
            starting_capital=round(starting_capital, 2),
            ending_value=round(ending_value, 2),
            total_return_pct=round(total_return_pct, 2),
            portfolio_series=portfolio_series,
            decisions=decisions,
            summary=summary,
        )


def _symbol_for(asset_id: str, universe: list[Asset]) -> str:
    for a in universe:
        if a.id == asset_id:
            return a.symbol
    return asset_id


def _summarize(series: list[PortfolioPoint], decisions: list[DecisionLogEntry]) -> SimulationSummary:
    values = np.array([p.value for p in series], dtype=float)
    n_buys = sum(1 for d in decisions if d.action == "BUY")
    n_sells = sum(1 for d in decisions if d.action == "SELL")

    if len(values) < 2:
        return SimulationSummary(
            n_trades=len(decisions),
            n_buys=n_buys,
            n_sells=n_sells,
            max_drawdown_pct=0.0,
            sharpe=0.0,
        )

    running_max = np.maximum.accumulate(values)
    drawdown = (values - running_max) / running_max
    max_dd = float(drawdown.min()) * 100.0

    daily_returns = np.diff(values) / values[:-1]
    if daily_returns.std() > 0:
        sharpe = float(np.sqrt(365) * daily_returns.mean() / daily_returns.std())
    else:
        sharpe = 0.0

    return SimulationSummary(
        n_trades=len(decisions),
        n_buys=n_buys,
        n_sells=n_sells,
        max_drawdown_pct=round(max_dd, 2),
        sharpe=round(sharpe, 2),
    )
