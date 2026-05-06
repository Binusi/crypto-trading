// Expo inlines `EXPO_PUBLIC_*` env vars at build time.
// Set EXPO_PUBLIC_API_URL in frontend/.env (see .env.example).
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
