import { useMemo } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";

import { DecisionRow } from "../../src/components/DecisionRow";
import { useSimulationStore } from "../../src/state/simulationStore";

export default function DecisionsScreen() {
  const lastResult = useSimulationStore((s) => s.lastResult);
  const sorted = useMemo(() => {
    const list = lastResult?.decisions ?? [];
    return [...list].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  }, [lastResult]);

  if (!lastResult || sorted.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>No decisions yet</Text>
        <Text style={styles.emptyBody}>
          Run a simulation on the Simulate tab to see the daily buy/sell log here.
        </Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: "#fff" }}>
      <View style={styles.header}>
        <Text style={styles.headerText}>
          {sorted.length} decisions • {lastResult.summary.n_buys} buys, {lastResult.summary.n_sells} sells
        </Text>
      </View>
      <FlatList
        data={sorted}
        keyExtractor={(d, i) => `${d.date}-${d.asset}-${d.action}-${i}`}
        renderItem={({ item }) => <DecisionRow entry={item} />}
        initialNumToRender={20}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  empty: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
    backgroundColor: "#fff",
  },
  emptyTitle: { fontSize: 18, fontWeight: "700", color: "#0f172a", marginBottom: 8 },
  emptyBody: { fontSize: 14, color: "#64748b", textAlign: "center" },
  header: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: "#f8fafc",
    borderBottomColor: "#e2e8f0",
    borderBottomWidth: 1,
  },
  headerText: { fontSize: 12, color: "#475569" },
});
