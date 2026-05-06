import { Stack } from "expo-router";
import { useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { getHealth } from "../src/services/api";
import { useSimulationStore } from "../src/state/simulationStore";

export default function RootLayout() {
  const setBackendReachable = useSimulationStore((s) => s.setBackendReachable);

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then(() => {
        if (!cancelled) setBackendReachable(true);
      })
      .catch(() => {
        if (!cancelled) setBackendReachable(false);
      });
    return () => {
      cancelled = true;
    };
  }, [setBackendReachable]);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </SafeAreaProvider>
  );
}
