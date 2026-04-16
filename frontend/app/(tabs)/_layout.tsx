import React from 'react';
import { Tabs, useRouter } from 'expo-router';
import {
  View, TouchableOpacity, Platform,
  StyleSheet, Modal, Text,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

const PRIMARY = '#FF7A22';

type CenterBtnProps = { onPress?: () => void };

function CenterButton({ onPress }: CenterBtnProps) {
  return (
    <TouchableOpacity activeOpacity={0.85} onPress={onPress} style={styles.centerWrapper}>
      <View style={styles.centerCircle}>
        <MaterialCommunityIcons name="dumbbell" size={30} color="#fff" />
      </View>
    </TouchableOpacity>
  );
}

// Exercise options — key must match Django WebSocket route
const EXERCISES = [
  {
    key: 'bicep_curl',
    label: 'Bicep',
    icon: 'barbell-outline' as const,
  },
  {
    key: 'squat',
    label: 'Squat',
    icon: 'body-outline' as const,
  },
  {
    key: 'lunge',
    label: 'Lunge',
    icon: 'walk-outline' as const,
  },
  {
    key: 'plank',
    label: 'Plank',
    icon: 'fitness-outline' as const,
  },
];

export default function TabLayout() {
  const [showPoseModal, setShowPoseModal] = React.useState(false);
  const router = useRouter();

  const handleSelectExercise = (exerciseKey: string) => {
    setShowPoseModal(false);
    router.push({
      pathname: '/pose-tracker' as any,
      params: { exercise: exerciseKey },
    });
  };

  return (
    <>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: PRIMARY,
          tabBarInactiveTintColor: '#aaa',
          tabBarStyle: styles.tabBar,
          tabBarLabelStyle: styles.tabLabel,
          headerShown: false,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Home',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'home' : 'home-outline'} size={24} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="forum"
          options={{
            title: 'Forum',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'globe' : 'globe-outline'} size={24} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="pose"
          options={{
            tabBarLabel: '',
            tabBarButton: () => (
              <CenterButton onPress={() => setShowPoseModal(true)} />
            ),
          }}
        />
        <Tabs.Screen
          name="chat"
          options={{
            title: 'Chat',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'chatbubble' : 'chatbubble-outline'} size={24} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="profile"
          options={{
            title: 'Profile',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'person' : 'person-outline'} size={24} color={color} />
            ),
          }}
        />
      </Tabs>

      {/* Exercise Picker Modal */}
      <Modal visible={showPoseModal} transparent animationType="slide">
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowPoseModal(false)}
        >
          <View style={styles.modalContent}>

            <View style={styles.modalHandle} />

            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Choose Exercise</Text>
              <Text style={styles.modalSubtitle}>
                Select an activity to start pose tracking
              </Text>
            </View>

            <View style={styles.grid}>
              {EXERCISES.map((ex) => (
                <TouchableOpacity
                  key={ex.key}
                  style={styles.optionCard}
                  activeOpacity={0.8}
                  onPress={() => handleSelectExercise(ex.key)}
                >
                  <View style={styles.iconBox}>
                    <Ionicons name={ex.icon} size={34} color={PRIMARY} />
                  </View>
                  <Text style={styles.optionTitle}>{ex.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    height: 80,
    paddingBottom: Platform.OS === 'ios' ? 20 : 12,
    paddingTop: 8,
    borderTopWidth: 0,
    backgroundColor: '#fff',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -3 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
      },
      android: { elevation: 8 },
    }),
  },
  tabLabel: { fontSize: 11, fontWeight: '600' },
  centerWrapper: {
    top: -20,
    justifyContent: 'center',
    alignItems: 'center',
    ...Platform.select({
      ios: {
        shadowColor: PRIMARY,
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.4,
        shadowRadius: 12,
      },
      android: { elevation: 12 },
    }),
  },
  centerCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: PRIMARY,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#fff',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    padding: 24,
    paddingBottom: Platform.OS === 'ios' ? 48 : 32,
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#E0E0E0',
    alignSelf: 'center',
    marginBottom: 20,
  },
  modalHeader: {
    marginBottom: 24,
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#111',
    marginBottom: 6,
  },
  modalSubtitle: {
    fontSize: 15,
    color: '#666',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 16,
  },
  optionCard: {
    width: '47%',
    backgroundColor: '#F8F9FA',
    borderRadius: 20,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  iconBox: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#FFF0E5',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  optionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111',
  },
});
