import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Dimensions,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  StatusBar,
  Animated,
  ScrollView,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Line } from 'react-native-svg';

import {
  getPoseAnalyzeUrl,
  getPoseCloseUrl,
  POSE_API_BASE_URL,
} from '../constants/api';
import { BicepEngine } from '../engines/BicepEngine';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
  [27, 31], [28, 32], [27, 29], [28, 30],
  [0, 1], [1, 2], [2, 3], [0, 4], [4, 5], [5, 6],
];

const CAPTURE_INTERVAL_MS = 180;
const ANIMATION_DURATION = 150;
const SPEECH_COOLDOWN_MS = 4000;
const LANDMARK_VISIBILITY_THRESHOLD = 0.5;

// Kiểu dữ liệu cho Log
interface LogEntry {
  id: string;
  time: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

export default function PoseTrackerScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ exercise?: string }>();
  const exercise = params.exercise ?? 'bicep_curl';

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  
  // Trạng thái phiên tập
  const [sessionState, setSessionState] = useState<'idle' | 'running'>('idle');
  const sessionStateRef = useRef<'idle' | 'running'>('idle'); // Dùng ref để bypass closure trong loop
  
  const requestInFlightRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  const lastSpokenAtRef = useRef(0);
  const prevRepCountRef = useRef(0);
  const prevCorrectionRef = useRef('');

  // Hệ thống Logs
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const scrollViewRef = useRef<ScrollView>(null);

  const animatedPoints = useRef(
    Array.from({ length: 33 }, () => new Animated.ValueXY({ x: -100, y: -100 }))
  ).current;

  // --- ON-DEVICE ENGINE (bicep_curl only) ---
  // Instantiated once; persists across renders via ref
  const engineRef = useRef(new BicepEngine());

  const [isConnected, setIsConnected] = useState(false);
  const [landmarks, setLandmarks] = useState<any[]>([]);
  const [correction, setCorrection] = useState('Nhấn BẮT ĐẦU để tập luyện');
  const [score, setScore] = useState(0);
  const [repCount, setRepCount] = useState(0);
  const [isCorrect, setIsCorrect] = useState(true);

  // --- HÀM GHI LOG ---
  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    setLogs((prev) => {
      const newLogs = [...prev, { id: Date.now().toString() + Math.random(), time: timeStr, message, type }];
      return newLogs.slice(-20); // Giữ tối đa 20 log gần nhất
    });
  }, []);

  const updatePointsSmoothly = useCallback((newLandmarks: any[]) => {
    const animations = newLandmarks.map((lp, i) => {
      if (lp.visibility < LANDMARK_VISIBILITY_THRESHOLD) return null;
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
    if (!sessionIdRef.current) return;
    try {
      await fetch(getPoseCloseUrl(sessionIdRef.current), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current }),
      });
      addLog('Đã lưu kết quả bài tập.', 'info');
    } catch {
    } finally {
      sessionIdRef.current = null;
    }
  }, [addLog]);

  // --- CONTROL BUTTONS ---
  const toggleSession = () => {
    if (sessionState === 'idle') {
      setSessionState('running');
      sessionStateRef.current = 'running';
      setCorrection('Đang phân tích khung hình...');
      addLog('🚀 Bắt đầu Session Tập Luyện', 'info');
      captureAndAnalyzeFrame(); // Kích hoạt loop
    } else {
      setSessionState('idle');
      sessionStateRef.current = 'idle';
      setCorrection('Đã tạm dừng. Nhấn BẮT ĐẦU để tiếp tục.');
      addLog('⏸ Đã tạm dừng Session', 'warning');
      setLandmarks([]); // Xóa khung xương khi dừng
    }
  };

  const handleExit = useCallback(() => {
    setSessionState('idle');
    sessionStateRef.current = 'idle';
    Speech.stop();
    void closeSession();
    router.back();
  }, [closeSession, router]);

  useEffect(() => {
    if (!permission?.granted) void requestPermission();
    addLog('Hệ thống Camera đã sẵn sàng', 'info');
  }, [permission?.granted, requestPermission, addLog]);

  // Load the on-device TFJS model once on mount (bicep_curl only)
  useEffect(() => {
    if (exercise === 'bicep_curl') {
      engineRef.current.loadModel().then(() => {
        addLog('🤖 Mô hình AI On-Device đã sẵn sàng', 'success');
      });
    }
  // Only run once on mount — exercise won't change mid-session
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- CORE LOOP ---
  const captureAndAnalyzeFrame = useCallback(async () => {
    if (sessionStateRef.current !== 'running' || requestInFlightRef.current) return;
    if (!cameraRef.current) return;

    requestInFlightRef.current = true;

    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.15,
        base64: true,
        skipProcessing: true,
      });

      if (!photo?.base64) throw new Error('Không thể chụp ảnh');

      const apiUrl = getPoseAnalyzeUrl(exercise, sessionIdRef.current ?? undefined);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame: photo.base64 }),
      });

      if (!response.ok) throw new Error(`Lỗi máy chủ: ${response.status}`);

      const payload = await response.json();

      if (payload.type === 'no_detection') {
        setIsConnected(true);
        setCorrection(payload.correction || 'Vui lòng đứng vào khung hình');
        setLandmarks([]);
      } else if (payload.landmarks) {
        sessionIdRef.current = payload.session_id ?? sessionIdRef.current;

        // --- On-device engine overrides backend result for bicep_curl ---
        // For all other exercises, fall back to backend payload values.
        let nextCorrect: boolean;
        let nextCorrection: string;
        let currentReps: number;

        if (exercise === 'bicep_curl') {
          const engineResult = engineRef.current.processFrame(payload.landmarks);
          nextCorrect    = engineResult.isCorrect;
          nextCorrection = engineResult.correction;
          currentReps    = engineResult.counter;
        } else {
          nextCorrect    = payload.is_correct ?? true;
          nextCorrection = payload.correction || 'Tốt lắm, tiếp tục!';
          currentReps    = payload.counter ?? 0;
        }

        setIsConnected(true);
        setScore(payload.score ?? 0);
        setRepCount(currentReps);
        setIsCorrect(nextCorrect);
        setCorrection(nextCorrection);
        setLandmarks(payload.landmarks);

        // --- Bắt Event để ghi Log ---
        if (currentReps > prevRepCountRef.current) {
           addLog(`🔥 Hoàn thành Rep ${currentReps}`, 'success');
           prevRepCountRef.current = currentReps;
        }

        if (!nextCorrect && nextCorrection !== prevCorrectionRef.current) {
           addLog(`Cảnh báo: ${nextCorrection}`, 'error');
           prevCorrectionRef.current = nextCorrection;
        }

        if (nextCorrect) prevCorrectionRef.current = '';

        // --- Đọc Audio cảnh báo ---
        if (!nextCorrect && nextCorrection) {
          const now = Date.now();
          if (now - lastSpokenAtRef.current > SPEECH_COOLDOWN_MS) {
            lastSpokenAtRef.current = now;
            Speech.speak(nextCorrection, { language: 'vi-VN', rate: 1.0 });
          }
        }
        
        updatePointsSmoothly(payload.landmarks);
      }
    } catch (e) {
      setIsConnected(false);
      setCorrection('Mất kết nối với AI');
    } finally {
      requestInFlightRef.current = false;
      if (sessionStateRef.current === 'running') {
        setTimeout(captureAndAnalyzeFrame, CAPTURE_INTERVAL_MS);
      }
    }
  }, [exercise, updatePointsSmoothly, addLog]);

  useEffect(() => {
    return () => {
      sessionStateRef.current = 'idle';
      Speech.stop();
      void closeSession();
    };
  }, [closeSession]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* 1. Camera View */}
      <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="front" />

      {/* 2. Skeleton Layer */}
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
                  stroke={isCorrect ? "#52B788" : "#E63946"}
                  strokeWidth="5"
                  strokeOpacity={0.8}
                  strokeLinecap="round"
                />
              );
            })}
          </Svg>
        )}

        {landmarks.length > 0 && animatedPoints.map((anim, index) => (
          <Animated.View
            key={`joint-${index}`}
            style={[
              styles.landmarkDot,
              {
                backgroundColor: isCorrect ? '#52B788' : '#E63946',
                width: index > 10 ? 10 : 6,
                height: index > 10 ? 10 : 6,
                transform: anim.getTranslateTransform(),
              },
            ]}
          />
        ))}
      </View>

      {/* 3. UI Overlay */}
      <SafeAreaView style={styles.overlaySafe}>
        
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleExit} style={styles.exitBtn}>
            <Ionicons name="close" size={28} color="white" />
          </TouchableOpacity>
          <View style={styles.headerBadge}>
            <View style={[styles.statusDot, { backgroundColor: sessionState === 'running' ? (isConnected ? '#52B788' : '#F4A261') : '#6c757d' }]} />
            <Text style={styles.exerciseTitle}>{exercise.replace('_', ' ').toUpperCase()}</Text>
          </View>
          {/* Spacer */}
          <View style={{ width: 40 }} />
        </View>

        {/* HUD CHÍNH (Chỉ hiện khi đang chạy) */}
        <View style={styles.mainHud}>
          {sessionState === 'running' && (
            <>
              <Text style={styles.scoreText}>{score}</Text>
              <View style={styles.repBadge}>
                <Text style={styles.repText}>{repCount} REPS</Text>
              </View>
            </>
          )}
        </View>

        {/* BOTTOM SECTION */}
        <View style={styles.bottomSection}>
          
          {/* ACTIVITY LOG */}
          <View style={styles.logContainer}>
            <ScrollView 
              ref={scrollViewRef}
              showsVerticalScrollIndicator={false}
              onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
            >
              {logs.map((log) => (
                <Text key={log.id} style={styles.logLine}>
                  <Text style={styles.logTime}>[{log.time}] </Text>
                  <Text style={[
                    styles.logMessage,
                    log.type === 'success' && { color: '#52B788' },
                    log.type === 'error' && { color: '#E63946' },
                    log.type === 'warning' && { color: '#F4A261' },
                  ]}>{log.message}</Text>
                </Text>
              ))}
            </ScrollView>
          </View>

          {/* CORRECTION BANNER */}
          <View style={[styles.banner, { borderLeftColor: isCorrect ? '#52B788' : '#E63946' }]}>
            <Ionicons 
              name={isCorrect ? "checkmark-circle" : "alert-circle"} 
              size={24} 
              color={isCorrect ? '#52B788' : '#E63946'} 
              style={{ marginRight: 10 }}
            />
            <Text style={styles.correctionText}>{correction}</Text>
          </View>

          {/* CONTROLS */}
          <View style={styles.controlsRow}>
            <TouchableOpacity 
              style={[styles.controlBtn, { backgroundColor: sessionState === 'idle' ? '#52B788' : '#E63946' }]}
              onPress={toggleSession}
            >
              <Ionicons name={sessionState === 'idle' ? "play" : "stop"} size={28} color="white" />
              <Text style={styles.controlBtnText}>
                {sessionState === 'idle' ? 'BẮT ĐẦU' : 'DỪNG'}
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
  landmarkDot: { position: 'absolute', borderRadius: 10, zIndex: 10, borderColor: 'white', borderWidth: 1.5 },
  overlaySafe: { flex: 1, justifyContent: 'space-between' },
  
  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, marginTop: 10 },
  exitBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  headerBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 20 },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  exerciseTitle: { color: 'white', fontSize: 14, fontWeight: '700', letterSpacing: 1 },
  
  // HUD
  mainHud: { alignItems: 'center', marginTop: 20 },
  scoreText: { color: 'white', fontSize: 130, fontWeight: '900', textShadowColor: 'rgba(0,0,0,0.5)', textShadowRadius: 10, textShadowOffset: { width: 0, height: 4 } },
  repBadge: { backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 24, paddingVertical: 8, borderRadius: 25, marginTop: -15 },
  repText: { color: 'white', fontSize: 22, fontWeight: '800' },
  
  // Bottom Section
  bottomSection: { paddingHorizontal: 20, paddingBottom: 10 },
  
  // Terminal Log
  logContainer: { height: 100, backgroundColor: 'rgba(20, 20, 20, 0.7)', borderRadius: 12, padding: 12, marginBottom: 15, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  logLine: { fontSize: 12, marginBottom: 4, fontFamily: 'System' }, // Nếu ông cài font Mono (vd: Fira Code) thì đẹp hơn
  logTime: { color: '#888' },
  logMessage: { color: '#ddd', fontWeight: '500' },
  
  // Correction Banner
  banner: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.95)', padding: 16, borderRadius: 15, borderLeftWidth: 6, marginBottom: 15, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.25, shadowRadius: 3.84, elevation: 5 },
  correctionText: { fontSize: 16, fontWeight: '700', color: '#111', flex: 1 },
  
  // Controls
  controlsRow: { flexDirection: 'row', justifyContent: 'center' },
  controlBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 16, paddingHorizontal: 40, borderRadius: 30, shadowColor: "#000", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 4.65, elevation: 8 },
  controlBtnText: { color: 'white', fontSize: 18, fontWeight: '800', marginLeft: 10, letterSpacing: 1 },
});