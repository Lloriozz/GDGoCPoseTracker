import React, { useCallback, useMemo, useRef, useState } from 'react';
import {
  Platform,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import {
  QuickPoseView,
  QuickPoseThresholdCounter,
  type QuickPoseViewRef,
  type QuickPoseUpdateEvent,
  type QuickPoseStyle,
} from '@quickpose/react-native';

const QUICKPOSE_SDK_KEY = process.env.EXPO_PUBLIC_QUICKPOSE_SDK_KEY ?? '';

// --- Per-exercise configuration ---
interface ExerciseConfig {
  feature: string;
  label: string;
  isHold: boolean; // plank = hold timer, others = rep counter
}

const EXERCISE_CONFIG: Record<string, ExerciseConfig> = {
  bicep_curl: { feature: 'fitness.bicepCurls', label: 'Bicep Curls', isHold: false },
  squat:      { feature: 'fitness.squats',     label: 'Squats',      isHold: false },
  lunge:      { feature: 'fitness.lunges.left', label: 'Lunges',     isHold: false },
  plank:      { feature: 'fitness.plank',      label: 'Plank',       isHold: true  },
};

const DEFAULT_CONFIG: ExerciseConfig = {
  feature: 'overlay.wholeBody', label: 'Pose', isHold: false,
};

// Conditional styling — green highlight when score ≥ 80%
const GREEN_HIGHLIGHT_STYLE: QuickPoseStyle = {
  conditionalColors: [{ min: 0.8, color: '#4ADE80' }],
};

export default function QuickPoseTrackerScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ exercise?: string }>();
  const exercise = params.exercise ?? 'squat';

  const config = EXERCISE_CONFIG[exercise] ?? DEFAULT_CONFIG;
  const poseRef = useRef<QuickPoseViewRef>(null);

  // Rep counter (bicep, squat, lunge)
  const counter = useMemo(() => new QuickPoseThresholdCounter(), []);

  // Hold timer for plank — track seconds in the pose
  const holdStartRef = useRef<number | null>(null);

  // Feature styles — apply green highlight to the active feature
  const featureStyles = useMemo(
    () => ({ [config.feature]: GREEN_HIGHLIGHT_STYLE }),
    [config.feature]
  );

  // UI state
  const [feedbackText, setFeedbackText] = useState<string | null>(null);
  const [repCount, setRepCount] = useState(0);
  const [holdTime, setHoldTime] = useState(0);
  const [currentValue, setCurrentValue] = useState<number | null>(null);
  const [isPersonDetected, setIsPersonDetected] = useState(false);
  const [feedbackHistory, setFeedbackHistory] = useState<string[]>([]);

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const handleShare = useCallback(async () => {
    try {
      const summary = config.isHold
        ? `${config.label} — ${holdTime.toFixed(1)}s hold`
        : `${config.label} — ${repCount} reps`;
      await poseRef.current?.shareFrame(summary);
    } catch {
      // user dismissed share sheet
    }
  }, [config, repCount, holdTime]);

  const handleUpdate = useCallback(
    (event: QuickPoseUpdateEvent) => {
      const { results, feedbacks } = event.nativeEvent;

      // results is Record<string, number> — get value for our feature
      const featureKeys = Object.keys(results);
      const hasResults = featureKeys.length > 0;

      if (hasResults) {
        const value = results[featureKeys[0]!]!;
        setCurrentValue(value);

        if (config.isHold) {
          // Plank: track hold duration while value is above threshold
          if (value > 0.2) {
            if (holdStartRef.current === null) holdStartRef.current = Date.now();
            setHoldTime((Date.now() - holdStartRef.current) / 1000);
          } else {
            holdStartRef.current = null;
          }
        } else {
          // Bicep, Squat, Lunge: count reps via threshold crossing
          const state = counter.count(value);
          setRepCount(state.count);
        }
      } else {
        setCurrentValue(null);
        holdStartRef.current = null;
      }

      // --- Feedback priority (matching QuickPose docs) ---
      // 1. If result exists → user is performing, show feedback only if required
      // 2. If no result + feedback → body position / joint visibility correction
      // 3. If nothing → no person detected
      const fbKeys = Object.keys(feedbacks);
      const hasFeedback = fbKeys.length > 0;

      if (hasResults && !hasFeedback) {
        // Performing correctly — no corrections needed
        setFeedbackText(null);
        setIsPersonDetected(true);
      } else if (hasFeedback) {
        // Corrections needed (body position / joint visibility / exercise rule)
        const allFeedback = fbKeys.map((k) => feedbacks[k]!).filter(Boolean);
        const primary = allFeedback[0] ?? null;
        setFeedbackText(primary);
        setIsPersonDetected(hasResults);

        if (primary) {
          setFeedbackHistory((prev) => {
            if (prev[0] === primary) return prev;
            return [primary, ...prev].slice(0, 3);
          });
        }
      } else {
        // No results and no feedback → no person detected
        setFeedbackText('Stand in frame to begin');
        setIsPersonDetected(false);
      }
    },
    [counter, config]
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* QuickPose Camera + Skeleton overlay with conditional styling */}
      <QuickPoseView
        ref={poseRef}
        sdkKey={QUICKPOSE_SDK_KEY}
        features={[config.feature]}
        featureStyles={featureStyles}
        useFrontCamera={true}
        style={StyleSheet.absoluteFill}
        onUpdate={handleUpdate}
      />

      {/* UI Overlay */}
      <SafeAreaView style={styles.overlaySafe} pointerEvents="box-none">
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.iconBtn}>
            <Ionicons name="chevron-back" size={28} color="white" />
          </TouchableOpacity>
          <View style={styles.headerTitleContainer}>
            <Text style={styles.exerciseTitle}>{config.label.toUpperCase()}</Text>
          </View>
          <TouchableOpacity onPress={handleShare} style={styles.iconBtn}>
            <Ionicons name="share-outline" size={24} color="white" />
          </TouchableOpacity>
        </View>

        {/* Floating Feedback Banner — posture correction overlay */}
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }} pointerEvents="none">
          {feedbackText && (
            <View
              style={[
                styles.feedbackBanner,
                !isPersonDetected && styles.feedbackBannerWarning,
              ]}
            >
              <Ionicons
                name={isPersonDetected ? 'alert-circle' : 'body-outline'}
                size={20}
                color="white"
                style={{ marginRight: 8 }}
              />
              <Text style={styles.feedbackBannerText}>{feedbackText}</Text>
            </View>
          )}
        </View>

        {/* Bottom HUD */}
        <View style={styles.bottomHUD}>
          {/* Metrics */}
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>
                {config.isHold ? 'HOLD' : 'REPS'}
              </Text>
              <Text style={styles.metricValue}>
                {config.isHold ? `${holdTime.toFixed(1)}s` : repCount}
              </Text>
            </View>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>SCORE</Text>
              <Text
                style={[
                  styles.metricValue,
                  { fontSize: 20 },
                  currentValue !== null && currentValue >= 0.8 && { color: '#4ADE80' },
                ]}
              >
                {currentValue !== null
                  ? `${config.label}: ${Math.round(currentValue * 100)}%`
                  : 'Ready'}
              </Text>
            </View>
          </View>

          {/* Feedback Log */}
          <View style={styles.feedbackBox}>
            {!feedbackText && isPersonDetected ? (
              <Text style={[styles.feedbackLogText, { color: '#4ADE80' }]}>
                Great form! Keep going
              </Text>
            ) : (
              feedbackHistory.map((msg, index) => (
                <Text
                  key={index}
                  style={[
                    styles.feedbackLogText,
                    index === 0
                      ? styles.feedbackLogPrimary
                      : styles.feedbackLogSecondary,
                    { opacity: 1 - index * 0.35 },
                  ]}
                  numberOfLines={1}
                >
                  {index === 0 ? `▸ ${msg}` : msg}
                </Text>
              ))
            )}
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },

  overlaySafe: { flex: 1, justifyContent: 'space-between' },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 10,
  },
  iconBtn: {
    padding: 8,
    backgroundColor: 'rgba(0,0,0,0.4)',
    borderRadius: 20,
  },
  headerTitleContainer: {
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 15,
  },
  exerciseTitle: {
    color: 'white',
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: 1,
  },

  // Bottom HUD
  bottomHUD: {
    backgroundColor: 'rgba(15, 15, 15, 0.85)',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: 20,
    paddingBottom: Platform.OS === 'ios' ? 10 : 20,
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 15,
  },
  metricBox: { alignItems: 'center' },
  metricLabel: {
    color: '#888',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 4,
  },
  metricValue: {
    color: 'white',
    fontSize: 40,
    fontWeight: '900',
  },

  // Floating feedback banner (over camera)
  feedbackBanner: {
    backgroundColor: 'rgba(255, 94, 14, 0.85)',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 12,
    marginHorizontal: 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  feedbackBannerWarning: {
    backgroundColor: 'rgba(230, 57, 70, 0.85)',
  },
  feedbackBannerText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    flexShrink: 1,
  },

  // Feedback log (bottom HUD)
  feedbackBox: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 15,
    padding: 15,
    minHeight: 70,
    justifyContent: 'center',
  },
  feedbackLogText: {
    color: 'white',
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 3,
  },
  feedbackLogPrimary: {
    fontSize: 16,
    color: '#FF5E0E',
  },
  feedbackLogSecondary: {
    fontSize: 14,
    color: '#AAA',
  },
});
