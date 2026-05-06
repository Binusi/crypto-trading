import { StyleSheet, Text, View } from "react-native";

import { DecisionLogEntry } from "../types/api";

interface Props {
  entry: DecisionLogEntry;
}

export function DecisionRow({ entry }: Props) {
  const isBuy = entry.action === "BUY";
  return (
    <View style={styles.row}>
      <View style={[styles.chip, { backgroundColor: isBuy ? "#dcfce7" : "#fee2e2" }]}>
        <Text style={[styles.chipText, { color: isBuy ? "#166534" : "#991b1b" }]}>{entry.action}</Text>
      </View>
      <View style={styles.middle}>
        <Text style={styles.asset}>{entry.asset}</Text>
        <Text style={styles.date}>{entry.date}</Text>
      </View>
      <View style={styles.right}>
        <Text style={styles.usd}>${entry.usd_amount.toLocaleString()}</Text>
        <Text style={styles.score}>score {entry.score.toFixed(2)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderBottomColor: "#e2e8f0",
    borderBottomWidth: 1,
    backgroundColor: "#fff",
  },
  chip: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  chipText: { fontSize: 12, fontWeight: "700", letterSpacing: 0.5 },
  middle: { flex: 1, marginLeft: 12 },
  asset: { fontSize: 16, fontWeight: "600", color: "#0f172a" },
  date: { fontSize: 12, color: "#64748b", marginTop: 2 },
  right: { alignItems: "flex-end" },
  usd: { fontSize: 15, fontWeight: "600", color: "#0f172a" },
  score: { fontSize: 11, color: "#64748b", marginTop: 2 },
});
