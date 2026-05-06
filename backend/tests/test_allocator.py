from datetime import date

from app.simulation.allocator import Allocator, AllocatorConfig


def _cfg(**overrides) -> AllocatorConfig:
    base = dict(
        confidence_threshold=0.10,
        top_k=5,
        cash_reserve_frac=0.10,
        max_asset_weight=0.30,
        transaction_cost=0.001,
        min_trade_frac=0.005,
        cooldown_days=2,
    )
    base.update(overrides)
    return AllocatorConfig(**base)


def test_target_weights_filter_and_normalize():
    a = Allocator(_cfg())
    weights = a.target_weights({"BTC": 0.4, "ETH": 0.2, "DOGE": 0.05, "SOL": -0.1})
    assert "DOGE" not in weights
    assert "SOL" not in weights
    assert abs(sum(weights.values()) - 0.90) < 1e-9


def test_target_weights_per_asset_cap():
    a = Allocator(_cfg(max_asset_weight=0.30))
    weights = a.target_weights({"BTC": 0.99, "ETH": 0.20, "SOL": 0.20, "DOGE": 0.20})
    assert weights["BTC"] <= 0.30 + 1e-9
    assert abs(sum(weights.values()) - 0.90) < 1e-6


def test_min_trade_skip_below_threshold():
    # With cap=0.30, 1-asset target weight is capped at 0.30 -> $300 of a $1000 book.
    # Current $295 -> diff $5 (0.5%), below min_trade_frac=5% -> no orders.
    a = Allocator(_cfg(min_trade_frac=0.05))
    orders = a.build_trades(
        today=date(2023, 6, 1),
        scores={"BTC": 0.5},
        prices={"BTC": 100.0},
        portfolio_value=1000.0,
        current_units={"BTC": 2.95},
        last_buy_date={},
        last_sell_date={},
    )
    assert orders == []


def test_trade_emitted_above_threshold():
    a = Allocator(_cfg(min_trade_frac=0.005))
    orders = a.build_trades(
        today=date(2023, 6, 1),
        scores={"BTC": 0.5},
        prices={"BTC": 100.0},
        portfolio_value=1000.0,
        current_units={},  # nothing held -> wants to buy ~$300
        last_buy_date={},
        last_sell_date={},
    )
    assert any(o.action == "BUY" and o.asset_id == "BTC" for o in orders)


def test_cooldown_blocks_sell_after_buy():
    a = Allocator(_cfg(cooldown_days=2))
    orders = a.build_trades(
        today=date(2023, 6, 1),
        scores={"BTC": -0.5},  # negative score -> no target weight -> wants to fully sell
        prices={"BTC": 100.0},
        portfolio_value=1000.0,
        current_units={"BTC": 5.0},
        last_buy_date={"BTC": date(2023, 5, 31)},
        last_sell_date={},
    )
    assert all(o.action != "SELL" for o in orders)
