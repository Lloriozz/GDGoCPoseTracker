import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Dimensions,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  StatusBar,
  Animated,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  getPoseAnalyzeUrl,
  getPoseCloseUrl,
  POSE_API_BASE_URL,
} from '../constants/api';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

// 33 điểm chuẩn Mediapipe
const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
  [27, 31], [28, 32], [27, 29], [28, 30],
  [0, 1], [1, 2], [2, 3], [0, 4], [4, 5], [5, 6],
];

const CAPTURE_INTERVAL_MS = 180; 
const ANIMATION_DURATION = 180; 
const SPEECH_COOLDOWN_MS = 4000;
const LANDMARK_VISIBILITY_THRESHOLD = 0.5;

export default function PoseTrackerScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ exercise?: string }>();
  const exercise = params.exercise ?? 'bicep_curl';

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const captureEnabledRef = useRef(false);
  const requestInFlightRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  const lastSpokenAtRef = useRef(0);

  // Animated values để nội suy chuyển động (giúp điểm lướt mượt theo người)
  const animatedPoints = useRef(
    Array.from({ length: 33 }, () => new Animated.ValueXY({ x: -100, y: -100 }))
  ).current;

  const [isConnected, setIsConnected] = useState(false);
  const [landmarks, setLandmarks] = useState<any[]>([]);
  const [correction, setCorrection] = useState('');
  const [score, setScore] = useState(0);
  const [repCount, setRepCount] = useState(0);
  const [isCorrect, setIsCorrect] = useState(true);
  const [progressLabel, setProgressLabel] = useState('Preparing camera...');

  // --- HÀM CẬP NHẬT ĐIỂM (CHÌA KHÓA ĐỂ ĐIỂM BÁM NGƯỜI) ---
  const updatePointsSmoothly = useCallback((newLandmarks: any[]) => {
    const animations = newLandmarks.map((lp, i) => {
      if (lp.visibility < LANDMARK_VISIBILITY_THRESHOLD) return null;
      
      /**
       * GIẢI THÍCH MAPPING:
       * point.x/y từ AI là 0 -> 1 (tỉ lệ so với bức ảnh)
       * Khi dùng camera trước (facing front), ảnh bị ngược, nên x = (1 - lp.x)
       */
      const targetX = (1 - lp.x) * SCREEN_W;
      const targetY = lp.y * SCREEN_H;

      return Animated.timing(animatedPoints[i], {
        toValue: { x: targetX, y: targetY },
        duration: ANIMATION_DURATION,
        useNativeDriver: true,
      });
    }).filter(Boolean);

    Animated.parallel(animations as any).start();
  }, [animatedPoints]);

  const closeSession = useCallback(async () => {
    if (!sessionIdRef.current) {
      return;
    }

    try {
      await fetch(getPoseCloseUrl(sessionIdRef.current), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current }),
      });
    } catch {
    } finally {
      sessionIdRef.current = null;
    }
  }, []);

  const handleBack = useCallback(() => {
    captureEnabledRef.current = false;
    Speech.stop();
    void closeSession();
    router.back();
  }, [closeSession, router]);

  useEffect(() => {
    if (!permission?.granted) {
      void requestPermission();
    }
  }, [permission?.granted, requestPermission]);

  const captureAndAnalyzeFrame = useCallback(async () => {
    if (!captureEnabledRef.current || requestInFlightRef.current) return;
    if (!cameraRef.current) return;
    if (!POSE_API_BASE_URL) {
      setIsConnected(false);
      setProgressLabel('Backend URL missing');
      setCorrection('Set EXPO_PUBLIC_POSE_API_BASE_URL to connect to the pose backend.');
      return;
    }

    requestInFlightRef.current = true;

    try {
      setProgressLabel('Capturing frame...');
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.15,
        base64: true,
        skipProcessing: true,
        exif: false,
        shutterSound: false,
      });

      if (!photo?.base64) throw new Error('No photo captured');

      const apiUrl = getPoseAnalyzeUrl(exercise, sessionIdRef.current ?? undefined);
      console.log('[PoseTracker] Sending request to:', apiUrl);
      setProgressLabel('Analyzing pose...');

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame: photo.base64 }),
      });

      console.log('[PoseTracker] Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[PoseTracker] Error response:', errorText);
        throw new Error(`Server error ${response.status}: ${errorText}`);
      }

      const payload = await response.json();
      console.log('[PoseTracker] Payload type:', payload.type, 'landmarks:', payload.landmarks?.length);

      if (payload.type === 'no_detection') {
        setIsConnected(true);
        setProgressLabel('No pose detected');
        setCorrection(payload.correction || payload.message || 'Step into frame');
        setLandmarks([]);
      } else if (payload.landmarks && Array.isArray(payload.landmarks)) {
        sessionIdRef.current = payload.session_id ?? sessionIdRef.current;
        const nextCorrect = payload.is_correct ?? true;
        const nextCorrection = payload.correction || 'Keep going!';

        setIsConnected(true);
        setProgressLabel('Pose detected');
        setScore(payload.score ?? 0);
        setRepCount(payload.rep_count ?? 0);
        setIsCorrect(nextCorrect);
        setCorrection(nextCorrection);
        setLandmarks(payload.landmarks);

        if (!nextCorrect && nextCorrection) {
          const now = Date.now();
          if (now - lastSpokenAtRef.current > SPEECH_COOLDOWN_MS) {
            lastSpokenAtRef.current = now;
            Speech.speak(nextCorrection, { language: 'en-US', rate: 0.95 });
          }
        }
        
        updatePointsSmoothly(payload.landmarks);
      } else {
        console.warn('[PoseTracker] Unexpected payload format:', payload);
        setProgressLabel('Unexpected server response');
        setCorrection('Unexpected response from server');
      }
    } catch (e) {
      console.error('[PoseTracker] Error:', e);
      setIsConnected(false);
      setProgressLabel('Connection failed');
      setCorrection(`Connection error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      requestInFlightRef.current = false;
      if (captureEnabledRef.current) {
        setTimeout(captureAndAnalyzeFrame, CAPTURE_INTERVAL_MS);
      }
    }
  }, [exercise, updatePointsSmoothly]);

  useEffect(() => {
    if (permission?.granted && POSE_API_BASE_URL) {
      captureEnabledRef.current = true;
      void captureAndAnalyzeFrame();
    }
    return () => {
      captureEnabledRef.current = false;
      Speech.stop();
      void closeSession();
    };
  }, [captureAndAnalyzeFrame, closeSession, permission?.granted]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* 1. Camera View - Luôn lấp đầy màn hình */}
      <CameraView 
        ref={cameraRef} 
        style={StyleSheet.absoluteFill} 
        facing="front" 
      />

      {/* 2. Skeleton Layer - Vẽ các đường nối giữa các khớp */}
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        {landmarks.length > 15 && POSE_CONNECTIONS.map(([start, end], i) => {
          // Lưu ý: Vẽ đường nối dùng Animated Values khá phức tạp bằng View, 
          // nhưng với 33 điểm bám sát người, chỉ cần hiển thị các Dots là đã đủ Pro.
          return null; 
        })}

        {/* 3. Landmarks Dots - Các điểm bám theo người */}
        {landmarks.length > 0 && animatedPoints.map((anim, index) => (
          <Animated.View
            key={`joint-${index}`}
            style={[
              styles.landmarkDot,
              {
                backgroundColor: isCorrect ? '#52B788' : '#E63946',
                borderColor: 'white',
                borderWidth: 1,
                width: index > 10 ? 8 : 4, // Điểm thân to hơn điểm mặt
                height: index > 10 ? 8 : 4,
                transform: anim.getTranslateTransform(),
              },
            ]}
          />
        ))}
      </View>

      {/* UI Overlay */}
      <SafeAreaView style={styles.overlaySafe}>
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack}>
            <Ionicons name="chevron-back" size={32} color="white" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.exerciseTitle}>{exercise.replace('_', ' ').toUpperCase()}</Text>
            <Text style={styles.progressText}>{progressLabel}</Text>
          </View>
          <View style={[styles.statusDot, { backgroundColor: isConnected ? '#52B788' : '#E63946' }]} />
        </View>

        <View style={styles.mainScore}>
          <Text style={styles.scoreText}>{score}</Text>
          <Text style={styles.repText}>{repCount} REPS</Text>
        </View>

        <View style={styles.footer}>
          <View style={[styles.banner, { borderLeftColor: isCorrect ? '#52B788' : '#E63946' }]}>
            <Text style={styles.correctionText}>{correction || 'Detecting Pose...'}</Text>
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  landmarkDot: { position: 'absolute', borderRadius: 10, zIndex: 10 },
  overlaySafe: { flex: 1, justifyContent: 'space-between', padding: 20 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  headerCenter: { flex: 1, alignItems: 'center', paddingHorizontal: 12 },
  exerciseTitle: { color: 'white', fontSize: 18, fontWeight: '900', letterSpacing: 1 },
  progressText: { color: 'rgba(255,255,255,0.9)', fontSize: 12, fontWeight: '600', marginTop: 4 },
  statusDot: { width: 12, height: 12, borderRadius: 6 },
  mainScore: { alignItems: 'center', marginTop: 40 },
  scoreText: { color: 'white', fontSize: 120, fontWeight: '900', textShadowColor: 'black', textShadowRadius: 10 },
  repText: { color: 'white', fontSize: 24, fontWeight: '800', backgroundColor: 'rgba(0,0,0,0.3)', paddingHorizontal: 20, borderRadius: 20 },
  footer: { marginBottom: 20 },
  banner: { backgroundColor: 'white', padding: 20, borderRadius: 15, borderLeftWidth: 8, minHeight: 85 },
  correctionText: { fontSize: 17, fontWeight: '800', color: '#111', flexWrap: 'wrap', flexShrink: 1 },
});