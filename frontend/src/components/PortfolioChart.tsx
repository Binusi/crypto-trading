import { useMemo } from "react";
import { Dimensions, StyleSheet, Text, View } from "react-native";
import { LineChart } from "react-native-gifted-charts";

import { PortfolioPoint } from "../types/api";

interface Props {
  series: PortfolioPoint[];
  startingCapital: number;
}

export function PortfolioChart({ series, startingCapital }: Props) {
  const data = useMemo(() => {
    if (series.length === 0) return [];
    // Downsample to ~60 points for smoother rendering on large series.
    const step = Math.max(1, Math.floor(series.length / 60));
    const sampled = series.filter((_, i) => i % step === 0 || i === series.length - 1);
    return sampled.map((p, i) => ({
      value: p.value,
      label: i % Math.max(1, Math.floor(sampled.length / 5)) === 0 ? p.date.slice(5) : "",
    }));
  }, [series]);

  if (data.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No data yet.</Text>
      </View>
    );
  }

  const values = data.map((d) => d.value);
  const min = Math.min(...values, startingCapital);
  const max = Math.max(...values, startingCapital);
  const pad = (max - min) * 0.05 || 1;
  const width = Dimensions.get("window").width - 48;

  return (
    <View style={styles.wrap}>
      <LineChart
        data={data}
        width={width}
        height={200}
        thickness={2}
        color="#0ea5e9"
        startFillColor="#0ea5e9"
        endFillColor="#0ea5e9"
        startOpacity={0.25}
        endOpacity={0.02}
        areaChart
        hideDataPoints
        yAxisLabelPrefix="$"
        yAxisLabelSuffix=""
        yAxisTextStyle={{ color: "#64748b", fontSize: 10 }}
        xAxisLabelTextStyle={{ color: "#64748b", fontSize: 10 }}
        rulesColor="#e2e8f0"
        yAxisColor="#e2e8f0"
        xAxisColor="#e2e8f0"
        initialSpacing={8}
        spacing={Math.max(2, (width - 64) / Math.max(1, data.length - 1))}
        noOfSections={4}
        maxValue={max + pad}
        mostNegativeValue={min - pad}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 8 },
  empty: { paddingVertical: 24, alignItems: "center" },
  emptyText: { color: "#64748b" },
});
