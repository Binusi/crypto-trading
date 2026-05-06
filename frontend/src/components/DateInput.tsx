import { StyleSheet, Text, TextInput, View } from "react-native";

interface Props {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
}

export function DateInput({ label, value, onChangeText }: Props) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder="YYYY-MM-DD"
        placeholderTextColor="#94a3b8"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { marginBottom: 12 },
  label: { fontSize: 12, color: "#475569", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 },
  input: {
    backgroundColor: "#f8fafc",
    borderColor: "#cbd5e1",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    color: "#0f172a",
  },
});
