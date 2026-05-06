import { StyleSheet, Text, View } from "react-native";

interface Props {
  label: string;
  value: string;
  tone?: "neutral" | "good" | "bad";
}

export function Stat({ label, value, tone = "neutral" }: Props) {
  const color = tone === "good" ? "#16a34a" : tone === "bad" ? "#dc2626" : "#0f172a";
  return (
    <View style={styles.box}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, { color }]} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 10,
    backgroundColor: "#f1f5f9",
    borderRadius: 8,
    minWidth: 90,
  },
  label: { fontSize: 11, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 },
  value: { fontSize: 16, fontWeight: "600" },
});
