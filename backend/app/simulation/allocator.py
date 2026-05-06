"""Turn per-asset 3-class probabilities into trade orders.

Pipeline:
  1. score = P(buy) - P(sell) per asset
  2. Filter assets with score > confidence_threshold
  3. Take top K by score
  4. Distribute (1 - cash_reserve_frac) of portfolio proportionally to positive scores
  5. Cap per-asset at max_asset_weight
  6. Diff target weights vs. current holdings -> trade orders
  7. Drop trades smaller than min_trade_frac of portfolio (anti-churn)
  8. Honor per-asset cooldown (no sell within cooldown_days of last buy, vice versa)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class TradeOrder:
    asset_id: str
    action: str  # "BUY" | "SELL"
    usd_amount: float
    score: float


@dataclass
class AllocatorConfig:
    confidence_threshold: float
    top_k: int
    cash_reserve_frac: float
    max_asset_weight: float
    transaction_cost: float
    min_trade_frac: float
    cooldown_days: int


class Allocator:
    def __init__(self, cfg: AllocatorConfig):
        self.cfg = cfg

    def target_weights(self, scores: dict[str, float]) -> dict[str, float]:
        positive = {a: s for a, s in scores.items() if s > self.cfg.confidence_threshold}
        if not positive:
            return {}
        top = dict(sorted(positive.items(), key=lambda kv: kv[1], reverse=True)[: self.cfg.top_k])
        budget = 1.0 - self.cfg.cash_reserve_frac
        total = sum(top.values()) or 1.0
        weights = {a: budget * (s / total) for a, s in top.items()}

        # Apply per-asset cap, redistribute excess until stable.
        cap = self.cfg.max_asset_weight
        for _ in range(8):
            excess = 0.0
            free_assets = []
            for a, w in list(weights.items()):
                if w > cap:
                    excess += w - cap
                    weights[a] = cap
                else:
                    free_assets.append(a)
            if excess <= 1e-9 or not free_assets:
                break
            denom = sum(weights[a] for a in free_assets) or 1.0
            for a in free_assets:
                weights[a] += excess * (weights[a] / denom)
        return weights

    def build_trades(
        self,
        today: date,
        scores: dict[str, float],
        prices: dict[str, float],
        portfolio_value: float,
        current_units: dict[str, float],
        last_buy_date: dict[str, date],
        last_sell_date: dict[str, date],
    ) -> list[TradeOrder]:
        if portfolio_value <= 0:
            return []
        targets = self.target_weights(scores)

        assets = set(targets) | set(current_units)
        orders: list[TradeOrder] = []
        for a in assets:
            target_w = targets.get(a, 0.0)
            target_usd = target_w * portfolio_value
            cur_units = current_units.get(a, 0.0)
            price = prices.get(a)
            if price is None or price <= 0:
                continue
            cur_usd = cur_units * price
            diff = target_usd - cur_usd
            if abs(diff) < self.cfg.min_trade_frac * portfolio_value:
                continue

            if diff > 0:
                last_sell = last_sell_date.get(a)
                if last_sell and (today - last_sell).days < self.cfg.cooldown_days:
                    continue
                orders.append(TradeOrder(a, "BUY", diff, scores.get(a, 0.0)))
            else:
                last_buy = last_buy_date.get(a)
                if last_buy and (today - last_buy).days < self.cfg.cooldown_days:
                    continue
                orders.append(TradeOrder(a, "SELL", -diff, scores.get(a, 0.0)))
        # Process sells before buys so cash is available.
        orders.sort(key=lambda o: 0 if o.action == "SELL" else 1)
        return orders
