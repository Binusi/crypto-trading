export type Action = "BUY" | "SELL";

export interface PortfolioPoint {
  date: string;
  value: number;
  cash: number;
  holdings_value: number;
}

export interface DecisionLogEntry {
  date: string;
  action: Action;
  asset: string;
  usd_amount: number;
  price: number;
  score: number;
}

export interface SimulationSummary {
  n_trades: number;
  n_buys: number;
  n_sells: number;
  max_drawdown_pct: number;
  sharpe: number;
}

export interface SimulateResponse {
  starting_capital: number;
  ending_value: number;
  total_return_pct: number;
  portfolio_series: PortfolioPoint[];
  decisions: DecisionLogEntry[];
  summary: SimulationSummary;
}

export interface SimulateRequest {
  start_date: string;
  end_date: string;
  starting_capital: number;
  universe?: string[];
  confidence_threshold?: number;
}

export interface AssetInfo {
  id: string;
  symbol: string;
  name: string;
}
