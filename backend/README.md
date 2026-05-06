# crypto-trading backend

FastAPI service that runs the crypto-trading simulation. A LightGBM 3-class classifier (Sell / Hold / Buy) is trained on technical-indicator features pooled across the asset universe; a deterministic top-K allocator turns predictions into trades; a day-by-day simulator replays a date range and returns the portfolio time series + decision log.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Train the model (one-time, then occasionally)

```bash
python -m app.ml.train
```

This fetches ~5 years of daily OHLCV from CoinGecko's free API for the top-20 universe (`app/data/universe.py`), engineers features, runs walk-forward validation, fits the final LightGBM model, and writes it to `models/latest.pkl`. First run takes ~5–15 minutes (rate-limited); the parquet cache in `data_cache/` makes re-runs much faster.

Useful flags:
```bash
python -m app.ml.train --years 3                 # shorter history
python -m app.ml.train --skip-walk-forward       # skip eval, just fit + save
python -m app.ml.train --end 2024-12-31          # custom end date
```

## Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

`--host 0.0.0.0` is required so your phone (running Expo Go on the same Wi-Fi) can reach it. Otherwise the dev machine binds only to localhost and the phone can't connect.

## Endpoints

- `GET /health` → `{"status": "ok"}`
- `GET /assets` → default universe `[{id, symbol, name}, ...]`
- `POST /simulate` → run a backtest

```bash
curl -s -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2023-01-01","end_date":"2023-12-31","starting_capital":10000}' \
  | python -m json.tool | head -40
```

OpenAPI docs at `http://localhost:8000/docs`.

## Tests

```bash
pytest
```

## Layout

```
app/
  api/          FastAPI routers (/health, /assets, /simulate)
  core/         settings + structlog
  data/         CoinGecko provider + parquet cache + universe
  ml/           features, labels, LightGBM wrapper, walk-forward eval, train CLI
  simulation/   Portfolio, Allocator, Simulator
  schemas/      Pydantic request/response models
models/         trained .pkl files (gitignored)
data_cache/     OHLCV parquet cache (gitignored)
tests/          pytest suite
```

## Data source

Default: **Binance public klines** (`/api/v3/klines`). No API key, full daily OHLCV history (years), real OHLC, generous rate limits. Implementation: `app/data/binance.py`.

We originally planned to use **CoinGecko's free API**, but CoinGecko's public tier now caps historical queries at the last ~365 days (error 10012, May 2026). The `CoinGeckoProvider` remains in the codebase (`app/data/coingecko.py`) and is wired through the `DataProvider` ABC — you can swap it back in if you have a CoinGecko Pro key (just edit `app/api/routes_simulate.py` and `app/ml/train.py`).

The local **parquet cache** (`data_cache/`) makes re-runs fast — first fetch takes ~30 s for the 20-asset universe, subsequent runs are offline.

## Caveats

- **Universe coverage**: Binance lists every default-universe asset as `<SYMBOL>USDT`. If an asset gets delisted, training will skip it (logs a warning). You can adjust `app/data/binance.py::ID_TO_PAIR` if you want different pairs.
- **Not investment advice.** Simulation only.
