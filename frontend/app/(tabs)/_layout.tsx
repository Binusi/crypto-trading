import { Tabs } from "expo-router";
import { Text } from "react-native";

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 18, opacity: focused ? 1 : 0.6 }}>{label}</Text>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#0ea5e9",
        tabBarStyle: { borderTopColor: "#e2e8f0" },
        headerStyle: { borderBottomColor: "#e2e8f0", borderBottomWidth: 1 },
        headerTitleStyle: { fontWeight: "700" },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Simulate",
          tabBarIcon: ({ focused }) => <TabIcon label="📈" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="decisions"
        options={{
          title: "Decisions",
          tabBarIcon: ({ focused }) => <TabIcon label="📋" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
