import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { DateInput } from "../../src/components/DateInput";
import { MoneyInput } from "../../src/components/MoneyInput";
import { PortfolioChart } from "../../src/components/PortfolioChart";
import { Stat } from "../../src/components/Stat";
import { API_URL } from "../../src/config/env";
import { postSimulate } from "../../src/services/api";
import { useSimulationStore } from "../../src/state/simulationStore";

const ISO_RE = /^\d{4}-\d{2}-\d{2}$/;

export default function SimulateScreen() {
  const [capital, setCapital] = useState("10000");
  const [start, setStart] = useState("2023-01-01");
  const [end, setEnd] = useState("2023-12-31");

  const { lastResult, isLoading, error, backendReachable, setResult, setLoading, setError } =
    useSimulationStore();

  async function run() {
    const cap = Number(capital);
    if (!cap || cap <= 0) {
      Alert.alert("Invalid input", "Enter a starting capital greater than 0.");
      return;
    }
    if (!ISO_RE.test(start) || !ISO_RE.test(end)) {
      Alert.alert("Invalid date", "Use YYYY-MM-DD format for both dates.");
      return;
    }
    if (start >= end) {
      Alert.alert("Invalid range", "End date must be after start date.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await postSimulate({
        starting_capital: cap,
        start_date: start,
        end_date: end,
      });
      setResult(res);
    } catch (e: any) {
      setError(e?.message ?? "Simulation failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const r = lastResult;
  const returnTone =
    r == null ? "neutral" : r.total_return_pct >= 0 ? "good" : "bad";

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={{ flex: 1 }}
    >
      <ScrollView contentContainerStyle={styles.container}>
        {backendReachable === false && (
          <View style={styles.banner}>
            <Text style={styles.bannerTitle}>Backend unreachable</Text>
            <Text style={styles.bannerBody}>
              Couldn't reach {API_URL}. Check EXPO_PUBLIC_API_URL and that uvicorn is bound to 0.0.0.0.
            </Text>
          </View>
        )}

        <Text style={styles.heading}>Run a simulation</Text>
        <MoneyInput label="Starting capital" value={capital} onChangeText={setCapital} />
        <DateInput label="Start date" value={start} onChangeText={setStart} />
        <DateInput label="End date" value={end} onChangeText={setEnd} />

        <Pressable
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.button,
            pressed && { opacity: 0.85 },
            isLoading && { opacity: 0.6 },
          ]}
          onPress={run}
          disabled={isLoading}
        >
          {isLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Run Simulation</Text>}
        </Pressable>

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {r && (
          <>
            <View style={styles.statsRow}>
              <Stat label="Start" value={`$${r.starting_capital.toLocaleString()}`} />
              <Stat label="End" value={`$${r.ending_value.toLocaleString()}`} />
            </View>
            <View style={styles.statsRow}>
              <Stat
                label="Return"
                value={`${r.total_return_pct >= 0 ? "+" : ""}${r.total_return_pct.toFixed(2)}%`}
                tone={returnTone}
              />
              <Stat label="Max DD" value={`${r.summary.max_drawdown_pct.toFixed(2)}%`} tone="bad" />
              <Stat label="Sharpe" value={r.summary.sharpe.toFixed(2)} />
            </View>
            <Text style={styles.subheading}>Portfolio value</Text>
            <PortfolioChart series={r.portfolio_series} startingCapital={r.starting_capital} />
            <Text style={styles.tradeCount}>
              {r.summary.n_trades} trades ({r.summary.n_buys} buys, {r.summary.n_sells} sells)
            </Text>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, paddingBottom: 48, backgroundColor: "#fff", flexGrow: 1 },
  heading: { fontSize: 22, fontWeight: "700", color: "#0f172a", marginBottom: 16 },
  subheading: { fontSize: 14, fontWeight: "600", color: "#475569", marginTop: 16 },
  button: {
    marginTop: 8,
    backgroundColor: "#0ea5e9",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16, letterSpacing: 0.3 },
  statsRow: { flexDirection: "row", gap: 8, marginTop: 12 },
  banner: {
    backgroundColor: "#fef2f2",
    borderColor: "#fecaca",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  bannerTitle: { color: "#991b1b", fontWeight: "700", marginBottom: 4 },
  bannerBody: { color: "#991b1b", fontSize: 12 },
  errorBox: {
    marginTop: 12,
    backgroundColor: "#fef2f2",
    borderColor: "#fecaca",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
  },
  errorText: { color: "#991b1b", fontSize: 13 },
  tradeCount: { fontSize: 12, color: "#64748b", textAlign: "center", marginTop: 8 },
});
