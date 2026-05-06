from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Portfolio:
    cash: float
    holdings: dict[str, float] = field(default_factory=dict)  # asset_id -> units

    def value(self, prices: dict[str, float]) -> float:
        return self.cash + self.holdings_value(prices)

    def holdings_value(self, prices: dict[str, float]) -> float:
        total = 0.0
        for aid, units in self.holdings.items():
            p = prices.get(aid)
            if p is None:
                continue
            total += units * p
        return total

    def units_of(self, asset_id: str) -> float:
        return self.holdings.get(asset_id, 0.0)

    def apply_buy(self, asset_id: str, usd: float, price: float, fee_rate: float) -> float:
        """Spend `usd` on `asset_id` at `price`, charging a fee. Returns USD spent (incl. fee)."""
        if usd <= 0 or price <= 0:
            return 0.0
        fee = usd * fee_rate
        gross = usd + fee
        if gross > self.cash:
            usd = max(0.0, self.cash / (1.0 + fee_rate))
            fee = usd * fee_rate
            gross = usd + fee
        if usd <= 0:
            return 0.0
        units = usd / price
        self.cash -= gross
        self.holdings[asset_id] = self.holdings.get(asset_id, 0.0) + units
        return gross

    def apply_sell(self, asset_id: str, usd: float, price: float, fee_rate: float) -> float:
        """Sell up to `usd` worth of `asset_id` at `price`. Returns USD received (after fee)."""
        if usd <= 0 or price <= 0:
            return 0.0
        held = self.holdings.get(asset_id, 0.0)
        max_usd = held * price
        usd = min(usd, max_usd)
        if usd <= 0:
            return 0.0
        units = usd / price
        fee = usd * fee_rate
        net = usd - fee
        self.holdings[asset_id] = held - units
        if self.holdings[asset_id] <= 1e-12:
            del self.holdings[asset_id]
        self.cash += net
        return net
