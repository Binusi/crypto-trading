import { API_URL } from "../config/env";
import { AssetInfo, SimulateRequest, SimulateResponse } from "../types/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text || path}`);
  }
  return (await res.json()) as T;
}

export function getHealth(): Promise<{ status: string }> {
  return http("/health");
}

export function getAssets(): Promise<AssetInfo[]> {
  return http("/assets");
}

export function postSimulate(req: SimulateRequest): Promise<SimulateResponse> {
  return http("/simulate", { method: "POST", body: JSON.stringify(req) });
}
