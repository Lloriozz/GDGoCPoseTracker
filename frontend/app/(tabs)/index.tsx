import React, { useMemo, useState } from 'react';
import {
  ImageSourcePropType,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { FloatingPtButton } from '../../components/home/FloatingPtButton';
import { ProgramBanner } from '../../components/home/ProgramBanner';
import { WorkoutCard } from '../../components/home/WorkoutCard';
import { shadows, theme } from '../../constants/theme';

const categories = ['All', 'Squad', 'Bicep'];

type Workout = {
  id: number;
  title: string;
  subtitle: string;
  image: ImageSourcePropType;
};

const workouts: Workout[] = [
  {
    id: 1,
    title: 'Bicep Curl',
    subtitle: '10 Exercises',
    image: require('../../assets/bicepcurl.jpg'),
  },
  {
    id: 2,
    title: 'Squat',
    subtitle: '3 Exercises',
    image: require('../../assets/squat.jpg'),
  },
];

const programs = [
  {
    id: 1,
    category: 'Cardio',
    title: 'Simple Fasted\nCardio',
    image: require('../../assets/program.jpg'),
  },
  {
    id: 2,
    category: 'Chest',
    title: 'Hardcore Chest',
    image: require('../../assets/program.jpg'),
  },
];

export default function HomeScreen() {
  const [activeCategory, setActiveCategory] = useState('All');

  const visibleWorkouts = useMemo(() => {
    if (activeCategory === 'All') {
      return workouts;
    }

    const normalizedCategory = activeCategory === 'Squad' ? 'squat' : activeCategory.toLowerCase();
    return workouts.filter((item) => item.title.toLowerCase().includes(normalizedCategory));
  }, [activeCategory]);

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
      <View style={styles.container}>
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
          <View style={styles.header}>
            <View>
              <Text style={styles.greeting}>Hi GDGoC - er!</Text>
              <Text style={styles.welcome}>Welcome to</Text>
              <Text style={styles.brand}>PoseTracker</Text>
            </View>
            <TouchableOpacity activeOpacity={0.88} style={styles.notificationButton}>
              <Ionicons name="notifications" size={30} color={theme.colors.primary} />
              <View style={styles.badge}>
                <Text style={styles.badgeText}>1</Text>
              </View>
            </TouchableOpacity>
          </View>

          <View style={[styles.searchBox, shadows.soft]}>
            <Ionicons name="search-outline" size={20} color={theme.colors.muted} />
            <TextInput
              placeholder="Find your exercises.."
              placeholderTextColor={theme.colors.muted}
              style={styles.searchInput}
            />
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryRow}>
            {categories.map((category) => {
              const active = category === activeCategory;

              return (
                <TouchableOpacity
                  key={category}
                  activeOpacity={0.88}
                  onPress={() => setActiveCategory(category)}
                  style={[styles.categoryChip, active ? styles.categoryChipActive : styles.categoryChipIdle]}
                >
                  <Text style={[styles.categoryText, active ? styles.categoryTextActive : styles.categoryTextIdle]}>
                    {category}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          <View style={styles.sectionHeader}>
            <Text style={styles.sectionHeaderTitle}>Featured Workout</Text>
            <TouchableOpacity activeOpacity={0.88}>
              <Text style={styles.seeAll}>See all</Text>
            </TouchableOpacity>
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.workoutRow}>
            {visibleWorkouts.map((workout) => (
              <WorkoutCard
                key={workout.id}
                image={workout.image}
                title={workout.title}
                subtitle={workout.subtitle}
              />
            ))}
          </ScrollView>

          <Text style={styles.sectionTitle}>Recommend for you</Text>

          {programs.map((program) => (
            <ProgramBanner
              key={program.id}
              category={program.category}
              title={program.title}
              image={program.image}
              onPress={() => router.push('/chatbot')}
            />
          ))}

          <View style={styles.bottomSpacer} />
        </ScrollView>

        <FloatingPtButton onPress={() => router.push('/chatbot')} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  container: {
    flex: 1,
    position: 'relative',
  },
  content: {
    paddingHorizontal: 14,
    paddingTop: theme.spacing.lg,
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  greeting: {
    color: theme.colors.text,
    fontSize: 20,
    fontWeight: '500',
  },
  welcome: {
    marginTop: 8,
    color: theme.colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  brand: {
    color: theme.colors.primary,
    fontSize: 38,
    fontWeight: '800',
    lineHeight: 42,
  },
  notificationButton: {
    position: 'relative',
    paddingTop: 4,
    paddingRight: 6,
  },
  badge: {
    position: 'absolute',
    top: -2,
    right: 2,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: theme.colors.white,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    color: theme.colors.primary,
    fontSize: 10,
    fontWeight: '700',
  },
  searchBox: {
    marginTop: 22,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: theme.radius.xl,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 18,
    color: theme.colors.text,
  },
  categoryRow: {
    paddingVertical: 4,
    gap: 10,
  },
  categoryChip: {
    borderRadius: theme.radius.round,
    paddingHorizontal: 22,
    paddingVertical: 10,
  },
  categoryChipActive: {
    backgroundColor: theme.colors.primary,
  },
  categoryChipIdle: {
    backgroundColor: theme.colors.surface,
  },
  categoryText: {
    fontSize: 16,
    fontWeight: '600',
  },
  categoryTextActive: {
    color: theme.colors.white,
  },
  categoryTextIdle: {
    color: '#444444',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 18,
    marginBottom: 14,
  },
  sectionHeaderTitle: {
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: '800',
  },
  sectionTitle: {
    marginTop: 18,
    marginBottom: 14,
    color: theme.colors.text,
    fontSize: 24,
    fontWeight: '800',
  },
  seeAll: {
    color: theme.colors.primary,
    fontSize: 16,
    fontWeight: '700',
  },
  workoutRow: {
    paddingRight: 6,
    gap: 14,
  },
  bottomSpacer: {
    height: 48,
  },
});
