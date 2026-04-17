import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  Image,
  TouchableOpacity,
  ImageBackground,
  StyleSheet,
  StatusBar,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';

const PRIMARY = '#FF5E0E';
const GRAY_BG = '#1C1C1E';
const GRAY_TEXT = '#A1A1A1';

const CARD_SHADOW = Platform.select({
  ios: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  android: { elevation: 4 },
}) as object;

const categories = [
  { id: 'all', label: 'All', icon: 'barbell' },
  { id: 'strength', label: 'Strength', icon: 'barbell' },
  { id: 'treadmill', label: 'Treadmill', icon: 'fitness' },
  { id: 'bicycle', label: 'Bicycle', icon: 'bicycle' },
  { id: 'cardio', label: 'Cardio', icon: 'pulse' },
  { id: 'yoga', label: 'Yoga', icon: 'leaf' },
];

const workouts = [
  {
    id: 1,
    title: 'Bicep Curl',
    count: '10 Exercises',
    image: require('../../assets/bicepcurl.jpg'),
    category: 'strength',
  },
  {
    id: 2,
    title: 'Squat',
    count: '3 Exercises',
    image: require('../../assets/squat.jpg'),
    category: 'strength',
  },
  {
    id: 3,
    title: 'Treadmill Sprint',
    count: '8 Exercises',
    image: require('../../assets/bicepcurl.jpg'),
    category: 'treadmill',
  },
  {
    id: 4,
    title: 'Cycling Endurance',
    count: '12 Exercises',
    image: require('../../assets/squat.jpg'),
    category: 'bicycle',
  },
  {
    id: 5,
    title: 'HIIT Cardio',
    count: '6 Exercises',
    image: require('../../assets/bicepcurl.jpg'),
    category: 'cardio',
  },
  {
    id: 6,
    title: 'Yoga Flow',
    count: '5 Exercises',
    image: require('../../assets/squat.jpg'),
    category: 'yoga',
  },
  {
    id: 7,
    title: 'Shoulder Press',
    count: '7 Exercises',
    image: require('../../assets/bicepcurl.jpg'),
    category: 'strength',
  },
];

const programs = [
  {
    id: 1,
    category: 'Cardio',
    title: 'Simple Fasted Cardio',
    image: require('../../assets/program.jpg'),
    route: '/workout',
  },
  {
    id: 2,
    category: 'Chest',
    title: 'Hardcore Chest',
    image: require('../../assets/chest-program.jpg'),
  },
];

export default function HomeScreen() {
  const [activeCategory, setActiveCategory] = useState('all');

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'left', 'right']}>
      <LinearGradient
        colors={['rgba(255, 94, 14, 0.25)', '#0F0F0F', '#0F0F0F']}
        locations={[0, 0.35, 1]}
        style={StyleSheet.absoluteFillObject}
      />
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <ScrollView
        style={styles.scroll}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {/* ── Header ── */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hi GDGoC - er!</Text>
            <Text style={styles.welcomeLabel}>Welcome to</Text>
            <Text style={styles.appName}>PoseTracker</Text>
          </View>
          <TouchableOpacity activeOpacity={0.8}>
            <View style={styles.notifWrapper}>
              <Ionicons name="notifications" size={30} color={PRIMARY} />
              <View style={styles.badge}>
                <Text style={styles.badgeText}>1</Text>
              </View>
            </View>
          </TouchableOpacity>
        </View>

        {/* ── Search ── */}
        <View style={styles.searchBox}>
          <Ionicons name="search-outline" size={20} color={GRAY_TEXT} />
          <TextInput
            placeholder="Find your exercises.."
            placeholderTextColor={GRAY_TEXT}
            style={styles.searchInput}
          />
        </View>

        {/* ── Categories ── */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.categoryRow}
        >
          {categories.map((cat) => (
            <TouchableOpacity
              key={cat.id}
              activeOpacity={0.8}
              onPress={() => setActiveCategory(cat.id)}
              style={[
                styles.chip,
                activeCategory === cat.id ? styles.chipActive : styles.chipInactive,
              ]}
            >
              {activeCategory === cat.id && (
                <View style={styles.chipGlow} />
              )}
              <Ionicons
                name={cat.icon as any}
                size={18}
                color={activeCategory === cat.id ? '#fff' : '#666'}
                style={{ marginRight: 8 }}
              />
              <Text
                style={[
                  styles.chipText,
                  activeCategory === cat.id ? styles.chipTextActive : styles.chipTextInactive,
                ]}
              >
                {cat.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* ── Featured Workout ── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Featured Workout</Text>
          <TouchableOpacity activeOpacity={0.8}>
            <Text style={styles.seeAll}>See all</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.workoutRow}
        >
          {workouts.map((w) => (
            <TouchableOpacity
              key={w.id}
              activeOpacity={0.9}
              style={[styles.workoutCard, CARD_SHADOW]}
              onPress={() => {
                if (w.title === 'Bicep Curl') {
                  router.push('/bicep-workout' as any);
                } else if (w.title === 'Squat') {
                  router.push('/squat-workout' as any);
                }
              }}
            >
              <Image source={w.image} style={styles.workoutImage} resizeMode="cover" />
              <View style={styles.workoutInfo}>
                <Text style={styles.workoutTitle}>{w.title}</Text>
                <Text style={styles.workoutCount}>{w.count}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* ── Recommend for you ── */}
        <Text style={[styles.sectionTitle, styles.recommendTitle]}>Recommend for you</Text>

        {programs.map((p) => (
          <TouchableOpacity
            key={p.id}
            activeOpacity={0.9}
            style={[styles.programCard, CARD_SHADOW]}
            onPress={() => {
              if (p.route) {
                router.push(p.route as any);
              }
            }}
          >
            <ImageBackground
              source={p.image}
              style={styles.programBg}
              resizeMode="cover"
              imageStyle={styles.programBgImage}
            >
              <LinearGradient
                colors={[PRIMARY, 'rgba(255, 94, 14, 0.5)', 'rgba(0, 0, 0, 0.7)']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.gradientOverlay}
              />
              <View style={styles.programContent}>
                <Text style={styles.programNumber}>100+</Text>
                <Text style={styles.programTitle}>{p.title}</Text>
                <TouchableOpacity
                  style={styles.startBtn}
                  activeOpacity={0.85}
                  onPress={() => {
                    if (p.route) {
                      router.push(p.route as any);
                    }
                  }}
                >
                  <Text style={styles.startBtnText}>Join Now</Text>
                  <View style={styles.arrowCircle}>
                    <Ionicons name="arrow-forward" size={14} color="#fff" />
                  </View>
                </TouchableOpacity>
              </View>
            </ImageBackground>
          </TouchableOpacity>
        ))}

        <View style={styles.bottomSpacer} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#0F0F0F', // Fallback color
  },
  scroll: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 20,
  },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginTop: 24,
  },
  greeting: {
    fontSize: 20,
    fontWeight: '600',
    color: '#E0E0E0',
  },
  welcomeLabel: {
    fontSize: 16,
    color: GRAY_TEXT,
    marginTop: 2,
  },
  appName: {
    fontSize: 30,
    fontWeight: '800',
    color: PRIMARY,
  },
  notifWrapper: {
    marginTop: 4,
    position: 'relative',
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#0F0F0F',
    borderRadius: 10,
    width: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#333',
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#1a1a1a',
  },

  // Search
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GRAY_BG,
    borderRadius: 30,
    paddingHorizontal: 16,
    paddingVertical: 13,
    marginTop: 24,
    gap: 8,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 6,
      },
      android: { elevation: 2 },
    }),
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    color: '#E0E0E0',
  },

  // Categories
  categoryRow: {
    paddingVertical: 8,
    paddingRight: 4,
    gap: 12,
    marginTop: 20,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 28,
    position: 'relative',
  },
  chipGlow: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: PRIMARY,
    borderRadius: 28,
    opacity: 0.2,
    ...Platform.select({
      ios: {
        shadowColor: PRIMARY,
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.5,
        shadowRadius: 12,
      },
      android: { elevation: 8 },
    }),
  },
  chipActive: {
    backgroundColor: PRIMARY,
    ...Platform.select({
      ios: {
        shadowColor: PRIMARY,
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.4,
        shadowRadius: 10,
      },
      android: { elevation: 6 },
    }),
  },
  chipInactive: {
    backgroundColor: GRAY_BG,
    borderWidth: 1,
    borderColor: '#333',
  },
  chipText: {
    fontSize: 14,
    fontWeight: '600',
    zIndex: 10,
  },
  chipTextActive: {
    color: '#fff',
  },
  chipTextInactive: {
    color: '#666',
  },

  // Section headers
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 28,
    marginBottom: 14,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  seeAll: {
    fontSize: 15,
    fontWeight: '700',
    color: PRIMARY,
  },

  // Workout cards
  workoutRow: {
    paddingRight: 4,
    gap: 16,
  },
  workoutCard: {
    backgroundColor: '#1C1C1E',
    borderRadius: 20,
    overflow: 'hidden',
    width: 210,
    borderWidth: 1,
    borderColor: '#333',
  },
  workoutImage: {
    width: '100%',
    height: 130,
  },
  workoutInfo: {
    padding: 14,
  },
  workoutTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  workoutCount: {
    fontSize: 13,
    color: GRAY_TEXT,
    marginTop: 3,
  },

  // Recommend section
  recommendTitle: {
    marginTop: 28,
    marginBottom: 14,
  },

  // Program cards
  programCard: {
    borderRadius: 22,
    overflow: 'hidden',
    height: 200,
    marginBottom: 18,
  },
  programBg: {
    flex: 1,
    justifyContent: 'flex-start',
    paddingLeft: 24,
    paddingTop: 24,
  },
  programBgImage: {
    borderRadius: 22,
  },
  gradientOverlay: {
    ...StyleSheet.absoluteFillObject,
    borderRadius: 22,
  },
  programContent: {
    zIndex: 10,
    width: '50%',
  },
  programNumber: {
    fontSize: 52,
    fontWeight: '900',
    color: '#fff',
    lineHeight: 56,
  },
  programTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 16,
    marginTop: 4,
  },
  startBtn: {
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 24,
    gap: 10,
  },
  startBtnText: {
    color: PRIMARY,
    fontWeight: '700',
    fontSize: 14,
  },
  arrowCircle: {
    backgroundColor: PRIMARY,
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },

  bottomSpacer: {
    height: 0,
  },
});
