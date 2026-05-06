import { create } from "zustand";

import { SimulateResponse } from "../types/api";

interface SimulationState {
  lastResult: SimulateResponse | null;
  isLoading: boolean;
  error: string | null;
  backendReachable: boolean | null;

  setResult: (r: SimulateResponse | null) => void;
  setLoading: (b: boolean) => void;
  setError: (e: string | null) => void;
  setBackendReachable: (b: boolean | null) => void;
}

export const useSimulationStore = create<SimulationState>((set) => ({
  lastResult: null,
  isLoading: false,
  error: null,
  backendReachable: null,
  setResult: (r) => set({ lastResult: r }),
  setLoading: (b) => set({ isLoading: b }),
  setError: (e) => set({ error: e }),
  setBackendReachable: (b) => set({ backendReachable: b }),
}));
