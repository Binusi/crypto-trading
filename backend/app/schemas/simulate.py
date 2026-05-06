from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SimulateRequest(BaseModel):
    start_date: date
    end_date: date
    starting_capital: float = Field(gt=0)
    universe: list[str] | None = None
    confidence_threshold: float | None = None

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, v: date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date")
        return v


class PortfolioPoint(BaseModel):
    date: date
    value: float
    cash: float
    holdings_value: float


class DecisionLogEntry(BaseModel):
    date: date
    action: Literal["BUY", "SELL"]
    asset: str
    usd_amount: float
    price: float
    score: float


class SimulationSummary(BaseModel):
    n_trades: int
    n_buys: int
    n_sells: int
    max_drawdown_pct: float
    sharpe: float


class SimulateResponse(BaseModel):
    starting_capital: float
    ending_value: float
    total_return_pct: float
    portfolio_series: list[PortfolioPoint]
    decisions: list[DecisionLogEntry]
    summary: SimulationSummary
