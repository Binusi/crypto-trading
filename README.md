# crypto-trading

A simulation app that uses machine learning to make daily buy / sell / hold decisions across a universe of cryptocurrencies. Enter a starting portfolio value and a date range; the app replays that period day-by-day and shows how the portfolio would have evolved, plus a per-day decision log.

> Simulation only. Nothing here connects to a live exchange or moves real money.

## Architecture

```
crypto-trading/
├── backend/    FastAPI service. LightGBM model, day-by-day simulator, CoinGecko data.
└── frontend/   Expo (React Native) app. Two tabs: Simulate and Decisions.
```

## Quick start

1. **Backend** — see [backend/README.md](backend/README.md). Create a venv, install requirements, train the model once (`python -m app.ml.train`), then run `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
2. **Frontend** — see [frontend/README.md](frontend/README.md). `npm install`, set `EXPO_PUBLIC_API_URL` to your dev machine's LAN IP, then `npx expo start`. Scan the QR code with Expo Go on your phone (same Wi-Fi).

## How it works

The backend trains a single pooled **LightGBM** multi-class classifier across all assets, with `asset_id` as a categorical feature. Inputs are technical-indicator features (returns, RSI, MACD, Bollinger Bands, ATR, OBV, BTC market context). Labels are rolling-tertile (top 33% of next-day returns → Buy, bottom 33% → Sell). Validation is walk-forward expanding-window — random k-fold leaks the future and isn't valid for time series.

A deterministic allocator turns class probabilities into trades: `score = P(buy) − P(sell)`, take the top-K assets, distribute 90% of the portfolio proportionally, hold 10% cash, cap any single asset at 30%, charge 0.10% per trade, two-day cooldown.

Data comes from Binance's public klines endpoint (no API key, full history) and is cached locally as Parquet. The `DataProvider` abstraction lets you swap in CoinGecko (with a Pro key) or any other source in one file.

## License

MIT — see [LICENSE](LICENSE).
