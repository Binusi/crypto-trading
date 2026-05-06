import { StyleSheet, Text, TextInput, View } from "react-native";

interface Props {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
}

export function MoneyInput({ label, value, onChangeText }: Props) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.field}>
        <Text style={styles.prefix}>$</Text>
        <TextInput
          style={styles.input}
          value={value}
          onChangeText={(t) => onChangeText(t.replace(/[^0-9.]/g, ""))}
          keyboardType="decimal-pad"
          placeholder="10000"
          placeholderTextColor="#94a3b8"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { marginBottom: 12 },
  label: { fontSize: 12, color: "#475569", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 },
  field: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#f8fafc",
    borderColor: "#cbd5e1",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
  },
  prefix: { color: "#475569", fontSize: 16, marginRight: 4 },
  input: { flex: 1, paddingVertical: 12, fontSize: 16, color: "#0f172a" },
});
