# crypto-trading frontend

Expo (React Native) app with two tabs: **Simulate** (input + results chart) and **Decisions** (per-day trade log). Talks to the FastAPI backend over the LAN.

Built to run in **Expo Go** — no custom dev client needed.

## Setup

```bash
cd frontend
npm install
```

## Configure the backend URL

Expo Go runs on your phone, so `localhost` won't work — you need the dev machine's LAN IP.

```bash
# macOS Wi-Fi:
ipconfig getifaddr en0

# Linux:
hostname -I | awk '{print $1}'
```

Copy the example env file and fill in your IP:

```bash
cp .env.example .env
# edit .env -> EXPO_PUBLIC_API_URL=http://192.168.x.y:8000
```

The phone must be on the same Wi-Fi network as your dev machine, and the backend must be running with `--host 0.0.0.0`.

## Run

```bash
npx expo start
```

Scan the QR code with Expo Go on your phone.

## Layout

```
app/                    expo-router file-based screens
  _layout.tsx           Stack root + backend health check on mount
  index.tsx             Redirect to (tabs)
  (tabs)/
    _layout.tsx         Tab navigator: Simulate | Decisions
    index.tsx           Simulate (inputs, run button, stats, chart)
    decisions.tsx       Decisions (FlatList of trade log)
src/
  components/           Stat, MoneyInput, DateInput, PortfolioChart, DecisionRow
  services/api.ts       Backend client (fetch wrapper)
  state/                Zustand store: lastResult, isLoading, error, backendReachable
  types/api.ts          TypeScript mirror of backend Pydantic schemas
  config/env.ts         Reads EXPO_PUBLIC_API_URL
```

## Tech choices

- **Expo Router** for file-based routing with the `(tabs)` group convention.
- **react-native-gifted-charts** for the line chart — pure JS, works in Expo Go (unlike `victory-native` v40+ which needs a custom dev client for Skia).
- **Zustand** as a tiny global store so the Simulate tab's last result is visible to the Decisions tab.

## Troubleshooting

**"Backend unreachable" banner / fetch errors**
- Check the URL in your `.env` matches your dev machine's current LAN IP (it changes when you switch networks).
- Confirm the backend is running with `--host 0.0.0.0`, not the default `127.0.0.1`.
- Confirm your phone is on the same Wi-Fi as the dev machine.
- macOS firewall sometimes blocks inbound connections to Python — check System Settings > Network > Firewall.

**Metro bundler stuck on "Starting…"**
- Quit Expo Go on the phone and reopen it.
- Try `npx expo start --tunnel` if your network blocks LAN connections (slower, requires ngrok-like routing).

**Chart not rendering**
- Make sure `react-native-svg` is installed (it's a peer dep of gifted-charts and was added by `npx expo install`).
