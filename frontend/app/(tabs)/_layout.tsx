import React from 'react';
import { Tabs, useRouter } from 'expo-router';
import { Platform, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme } from '../../constants/theme';

function CenterButton({ onPress }: { onPress: () => void }) {
  return (
    <TouchableOpacity activeOpacity={0.88} onPress={onPress} style={styles.centerWrapper}>
      <View style={styles.centerCircle}>
        <MaterialCommunityIcons name="dumbbell" size={30} color={theme.colors.white} />
      </View>
    </TouchableOpacity>
  );
}

export default function TabsLayout() {
  const router = useRouter();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: '#222222',
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.label,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'home' : 'home-outline'} size={22} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="find-pt"
        options={{
          title: 'Find PT',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'people' : 'people-outline'} size={22} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="pose"
        options={{
          title: '',
          tabBarButton: () => <CenterButton onPress={() => router.push('/(tabs)/pose')} />,
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'chatbubble' : 'chatbubble-outline'} size={22} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="forum"
        options={{
          title: 'Forum',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'planet' : 'planet-outline'} size={22} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    height: 82,
    paddingTop: 8,
    paddingBottom: Platform.OS === 'ios' ? 18 : 12,
    borderTopWidth: 0,
    backgroundColor: theme.colors.white,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -3 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 8,
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
  },
  centerWrapper: {
    top: -22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  centerCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: theme.colors.primary,
    borderWidth: 4,
    borderColor: theme.colors.white,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.24,
    shadowRadius: 10,
    elevation: 10,
  },
});
