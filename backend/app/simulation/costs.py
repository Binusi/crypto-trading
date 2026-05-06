from __future__ import annotations


def trade_fee(usd_amount: float, fee_rate: float) -> float:
    return abs(usd_amount) * fee_rate
