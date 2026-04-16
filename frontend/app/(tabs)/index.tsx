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

const PRIMARY = '#FF7A22';
const GRAY_BG = '#F4F4F4';
const GRAY_TEXT = '#888';

const CARD_SHADOW = Platform.select({
  ios: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  android: { elevation: 4 },
}) as object;

const categories = ['All', 'Squad', 'Bicep'];

const workouts = [
  {
    id: 1,
    title: 'Bicep Curl',
    count: '10 Exercises',
    image: require('../../assets/bicepcurl.jpg'),
  },
  {
    id: 2,
    title: 'Squat',
    count: '3 Exercises',
    image: require('../../assets/squat.jpg'),
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
    image: require('../../assets/program.jpg'),
  },
];

export default function HomeScreen() {
  const [activeCategory, setActiveCategory] = useState('All');

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#fff" />
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
              key={cat}
              activeOpacity={0.8}
              onPress={() => setActiveCategory(cat)}
              style={[
                styles.chip,
                activeCategory === cat ? styles.chipActive : styles.chipInactive,
              ]}
            >
              <Text
                style={[
                  styles.chipText,
                  activeCategory === cat ? styles.chipTextActive : styles.chipTextInactive,
                ]}
              >
                {cat}
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
          >
            <ImageBackground
              source={p.image}
              style={styles.programBg}
              resizeMode="cover"
              imageStyle={styles.programBgImage}
            >
              <View style={styles.overlay} />
              <View style={styles.programContent}>
                <Text style={styles.programCategory}>{p.category}</Text>
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
                  <Text style={styles.startBtnText}>Start Program</Text>
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
    backgroundColor: '#fff',
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
    color: '#1a1a1a',
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
    backgroundColor: '#fff',
    borderRadius: 10,
    width: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#e0e0e0',
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
    color: '#1a1a1a',
  },

  // Categories
  categoryRow: {
    paddingVertical: 4,
    paddingRight: 4,
    gap: 10,
    marginTop: 20,
  },
  chip: {
    paddingHorizontal: 22,
    paddingVertical: 10,
    borderRadius: 24,
  },
  chipActive: {
    backgroundColor: PRIMARY,
  },
  chipInactive: {
    backgroundColor: GRAY_BG,
  },
  chipText: {
    fontSize: 15,
    fontWeight: '600',
  },
  chipTextActive: {
    color: '#fff',
  },
  chipTextInactive: {
    color: '#444',
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
    color: '#1a1a1a',
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
    backgroundColor: '#fff',
    borderRadius: 20,
    overflow: 'hidden',
    width: 210,
    borderWidth: 1,
    borderColor: '#f0f0f0',
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
    color: '#1a1a1a',
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
    justifyContent: 'flex-end',
  },
  programBgImage: {
    borderRadius: 22,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.45)',
    borderRadius: 22,
  },
  programContent: {
    padding: 20,
  },
  programCategory: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
    fontWeight: '500',
    marginBottom: 4,
  },
  programTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#fff',
    marginBottom: 12,
  },
  startBtn: {
    backgroundColor: PRIMARY,
    alignSelf: 'flex-start',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
  },
  startBtnText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },

  bottomSpacer: {
    height: 20,
  },
});
