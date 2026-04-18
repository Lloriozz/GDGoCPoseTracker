import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Dimensions,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  StatusBar,
  Animated,
  Platform,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Line } from 'react-native-svg';
import { analyzeFrame } from '../modules/pose-analyzer';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
  [27, 31], [28, 32], [27, 29], [28, 30],
  [0, 1], [1, 2], [2, 3], [0, 4], [4, 5], [5, 6],
];

const SPEECH_COOLDOWN_MS = 4000;
const LANDMARK_VISIBILITY_THRESHOLD = 0.4;

type SessionStatus = 'IDLE' | 'RUNNING' | 'PAUSED';

export default function PoseTrackerScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ exercise?: string }>();
  const exercise = params.exercise ?? 'bicep_curl';

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  // Local inference state
  const isProcessingRef = useRef(false);
  const lastSpokenAtRef = useRef(0);
  const statusRef = useRef<SessionStatus>('IDLE');
  const cameraReadyRef = useRef(false);

  const animatedPoints = useRef(
    Array.from({ length: 33 }, () => new Animated.ValueXY({ x: -100, y: -100 }))
  ).current;

  const [sessionStatus, setSessionStatus] = useState<SessionStatus>('IDLE');
  const [isCameraReady, setIsCameraReady] = useState(false);
  // keep ref in sync so async callbacks see the latest value
  useEffect(() => {
    cameraReadyRef.current = isCameraReady;
    if (isCameraReady) addLog('Ready to start!');
  }, [isCameraReady]);
  const [landmarks, setLandmarks] = useState<any[]>([]);
  const [score, setScore] = useState(0);
  const [repCount, setRepCount] = useState(0);
  const [isCorrect, setIsCorrect] = useState(true);
  const [logHistory, setLogHistory] = useState<string[]>(['Initializing camera...']);

  useEffect(() => {
    statusRef.current = sessionStatus;
  }, [sessionStatus]);

  useEffect(() => {
    if (!permission?.granted) void requestPermission();
  }, [permission?.granted, requestPermission]);

  const addLog = useCallback((newLog: string) => {
    setLogHistory((prev) => {
      if (prev[0] === newLog) return prev;
      return [newLog, ...prev].slice(0, 3);
    });
  }, []);

  const updatePointsSmoothly = useCallback((newLandmarks: any[]) => {
    const animations = newLandmarks.map((lp, i) => {
      if (lp.visibility < LANDMARK_VISIBILITY_THRESHOLD) return null;
      return Animated.timing(animatedPoints[i], {
        toValue: { x: (1 - lp.x) * SCREEN_W, y: lp.y * SCREEN_H },
        duration: 80,
        useNativeDriver: true,
      });
    }).filter(Boolean);
    Animated.parallel(animations as any).start();
  }, [animatedPoints]);

  const handleBack = useCallback(() => {
    statusRef.current = 'IDLE';
    setSessionStatus('IDLE');
    Speech.stop();
    if (router.canGoBack()) router.back();
  }, [router]);

  // ── On-device inference loop ──────────────────────────────────────────────
  const captureAndAnalyze = useCallback(async () => {
    if (statusRef.current !== 'RUNNING' || !cameraRef.current || isProcessingRef.current || !cameraReadyRef.current) return;
    isProcessingRef.current = true;

    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.4,
        base64: true,
        exif: false,
        shutterSound: false,
      });

      if (photo?.base64) {
        const t0 = Date.now();
        const result = await analyzeFrame(photo.base64, exercise);
        console.log(`[PoseTracker] inference ${Date.now() - t0}ms`);

        if (result.landmarks?.length > 0) {
          setLandmarks(result.landmarks);
          updatePointsSmoothly(result.landmarks);
        } else {
          setLandmarks([]);
        }

        setScore(result.score ?? 0);
        setRepCount(result.counter ?? 0);
        setIsCorrect(result.isCorrect ?? true);

        if (result.correction) {
          addLog(result.correction);
          if (!result.isCorrect) {
            const now = Date.now();
            if (now - lastSpokenAtRef.current > SPEECH_COOLDOWN_MS) {
              lastSpokenAtRef.current = now;
              Speech.speak(result.correction, { language: 'vi-VN', rate: 1.1 });
            }
          }
        }
      }
    } catch (e) {
      console.warn('[PoseTracker] analyzeFrame error:', e);
    } finally {
      isProcessingRef.current = false;
      if (statusRef.current === 'RUNNING') {
        // Small yield so React can commit state updates before next frame
        setTimeout(captureAndAnalyze, 50);
      }
    }
  }, [exercise, addLog, updatePointsSmoothly]);

  const toggleSession = useCallback(() => {
    if (sessionStatus === 'IDLE' || sessionStatus === 'PAUSED') {
      if (!cameraReadyRef.current) { addLog('Camera not ready yet...'); return; }
      setSessionStatus('RUNNING');
      addLog('Session started!');
      setTimeout(captureAndAnalyze, 500);
    } else {
      setSessionStatus('PAUSED');
      addLog('Paused');
    }
  }, [sessionStatus, addLog, captureAndAnalyze]);

  const endSession = useCallback(() => {
    statusRef.current = 'IDLE';
    setSessionStatus('IDLE');
    setRepCount(0);
    setScore(0);
    setLandmarks([]);
    addLog('Session ended');
  }, [addLog]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* 1. CAMERA */}
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="front"
        onCameraReady={() => { cameraReadyRef.current = true; setIsCameraReady(true); }}
      />

      {/* 2. SKELETON OVERLAY */}
      {sessionStatus !== 'IDLE' && (
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
          {landmarks.length > 0 && (
            <Svg style={StyleSheet.absoluteFill}>
              {POSE_CONNECTIONS.map(([start, end], i) => {
                const p1 = landmarks[start];
                const p2 = landmarks[end];
                if (!p1 || !p2 || p1.visibility < LANDMARK_VISIBILITY_THRESHOLD || p2.visibility < LANDMARK_VISIBILITY_THRESHOLD) return null;
                return (
                  <Line
                    key={`line-${i}`}
                    x1={(1 - p1.x) * SCREEN_W} y1={p1.y * SCREEN_H}
                    x2={(1 - p2.x) * SCREEN_W} y2={p2.y * SCREEN_H}
                    stroke={isCorrect ? '#FF5E0E' : '#E63946'}
                    strokeWidth="4" strokeOpacity={0.85}
                  />
                );
              })}
            </Svg>
          )}
          {landmarks.length > 0 && animatedPoints.map((anim, index) => (
            <Animated.View
              key={`joint-${index}`}
              style={[styles.landmarkDot, {
                backgroundColor: isCorrect ? '#FF5E0E' : '#E63946',
                width: index > 10 ? 8 : 5,
                height: index > 10 ? 8 : 5,
                transform: anim.getTranslateTransform(),
              }]}
            />
          ))}
        </View>
      )}

      {/* 3. UI OVERLAY */}
      <SafeAreaView style={styles.overlaySafe} pointerEvents="box-none">
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.iconBtn}>
            <Ionicons name="chevron-back" size={28} color="white" />
          </TouchableOpacity>
          <View style={styles.headerTitleContainer}>
            <Text style={styles.exerciseTitle}>{exercise.replace(/_/g, ' ').toUpperCase()}</Text>
          </View>
          <View style={[styles.statusDot, { backgroundColor: '#FF5E0E' }]} />
        </View>

        <View style={{ flex: 1 }} pointerEvents="none" />

        <View style={styles.bottomHUD}>
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>REPS</Text>
              <Text style={styles.metricValue}>{repCount}</Text>
            </View>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>SCORE</Text>
              <Text style={[styles.metricValue, { color: isCorrect ? '#FF5E0E' : '#E63946' }]}>{score}%</Text>
            </View>
          </View>

          <View style={styles.logBox}>
            {logHistory.map((log, index) => (
              <Text
                key={index}
                style={[
                  styles.logText,
                  index === 0 ? styles.logTextPrimary : styles.logTextSecondary,
                  { opacity: 1 - index * 0.4 },
                ]}
                numberOfLines={1}
              >
                {index === 0 ? `👉 ${log}` : log}
              </Text>
            ))}
          </View>

          <View style={styles.controlsRow}>
            {sessionStatus !== 'IDLE' && (
              <TouchableOpacity style={styles.endBtn} onPress={endSession}>
                <Ionicons name="stop" size={24} color="#FFF" />
              </TouchableOpacity>
            )}
            <TouchableOpacity
              style={[styles.mainBtn, { backgroundColor: sessionStatus === 'RUNNING' ? '#E63946' : '#FF5E0E', opacity: isCameraReady || sessionStatus !== 'IDLE' ? 1 : 0.4 }]}
              onPress={toggleSession}
            >
              <Ionicons
                name={sessionStatus === 'RUNNING' ? 'pause' : 'play'}
                size={24} color="white"
                style={{ marginRight: 8 }}
              />
              <Text style={styles.mainBtnText}>
                {sessionStatus === 'IDLE' ? 'START' : sessionStatus === 'PAUSED' ? 'RESUME' : 'PAUSE'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  landmarkDot: { position: 'absolute', borderRadius: 10, zIndex: 10, borderColor: 'white', borderWidth: 1 },
  overlaySafe: { flex: 1, justifyContent: 'space-between' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 10 },
  iconBtn: { padding: 8, backgroundColor: 'rgba(0,0,0,0.4)', borderRadius: 20 },
  headerTitleContainer: { backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 15 },
  exerciseTitle: { color: 'white', fontSize: 16, fontWeight: '800', letterSpacing: 1 },
  statusDot: { width: 14, height: 14, borderRadius: 7, borderWidth: 2, borderColor: 'white' },
  bottomHUD: { backgroundColor: 'rgba(15, 15, 15, 0.85)', borderTopLeftRadius: 30, borderTopRightRadius: 30, padding: 20, paddingBottom: Platform.OS === 'ios' ? 10 : 20 },
  metricsRow: { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 15 },
  metricBox: { alignItems: 'center' },
  metricLabel: { color: '#888', fontSize: 12, fontWeight: '700', letterSpacing: 1, marginBottom: 4 },
  metricValue: { color: 'white', fontSize: 40, fontWeight: '900' },
  logBox: { backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 15, padding: 15, marginBottom: 20, minHeight: 90, justifyContent: 'center' },
  logText: { color: 'white', fontWeight: '600', textAlign: 'center', marginBottom: 4 },
  logTextPrimary: { fontSize: 16, color: '#FF5E0E' },
  logTextSecondary: { fontSize: 14, color: '#AAA' },
  controlsRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 15 },
  mainBtn: { flex: 1, flexDirection: 'row', height: 56, borderRadius: 28, justifyContent: 'center', alignItems: 'center', elevation: 5, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 5, shadowOffset: { width: 0, height: 3 } },
  mainBtnText: { color: 'white', fontSize: 16, fontWeight: '800', letterSpacing: 1 },
  endBtn: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#333', justifyContent: 'center', alignItems: 'center' },
});