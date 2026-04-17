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

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
  [27, 31], [28, 32], [27, 29], [28, 30],
  [0, 1], [1, 2], [2, 3], [0, 4], [4, 5], [5, 6],
];

const SPEECH_COOLDOWN_MS = 4000;
const LANDMARK_VISIBILITY_THRESHOLD = 0.5;
const _WS_HOST = process.env.EXPO_PUBLIC_API_IP ?? '124.197.18.178';
const WS_BASE_URL = `ws://${_WS_HOST}:8000/ws/pose`;

type SessionStatus = 'IDLE' | 'RUNNING' | 'PAUSED';

export default function PoseTrackerScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ exercise?: string }>();
  const exercise = params.exercise ?? 'bicep_curl';

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  
  // Quản lý luồng mạng
  const isProcessingRef = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const lastSpokenAtRef = useRef(0);

  // Quản lý Trạng thái Session
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>('IDLE');
  const statusRef = useRef<SessionStatus>('IDLE'); // Dùng ref để xài trong hàm async

  const animatedPoints = useRef(
    Array.from({ length: 33 }, () => new Animated.ValueXY({ x: -100, y: -100 }))
  ).current;

  // State giao diện
  const [isConnected, setIsConnected] = useState(false);
  const [landmarks, setLandmarks] = useState<any[]>([]);
  const [score, setScore] = useState(0);
  const [repCount, setRepCount] = useState(0);
  const [isCorrect, setIsCorrect] = useState(true);
  
  // Lịch sử Log (Lưu 3 dòng gần nhất)
  const [logHistory, setLogHistory] = useState<string[]>(['Sẵn sàng bắt đầu!']);

  // Cập nhật ref mỗi khi state thay đổi để hàm capture nhận được
  useEffect(() => {
    statusRef.current = sessionStatus;
  }, [sessionStatus]);

  const updatePointsSmoothly = useCallback((newLandmarks: any[]) => {
    const animations = newLandmarks.map((lp, i) => {
      if (lp.visibility < LANDMARK_VISIBILITY_THRESHOLD) return null;
      const targetX = (1 - lp.x) * SCREEN_W;
      const targetY = lp.y * SCREEN_H;

      return Animated.timing(animatedPoints[i], {
        toValue: { x: targetX, y: targetY },
        duration: 100,
        useNativeDriver: true,
      });
    }).filter(Boolean);

    Animated.parallel(animations as any).start();
  }, [animatedPoints]);

  const handleBack = useCallback(() => {
    setSessionStatus('IDLE');
    Speech.stop();
    if (wsRef.current) wsRef.current.close();
    router.back();
  }, [router]);

  useEffect(() => {
    if (!permission?.granted) void requestPermission();
    addLog('Hệ thống Camera đã sẵn sàng', 'info');
  }, [permission?.granted, requestPermission, addLog]);

  // --- KẾT NỐI WEBSOCKET ---
  useEffect(() => {
    if (!permission?.granted) return;

    const wsUrl = `${WS_BASE_URL}/${exercise}/`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      addLog('Đã kết nối Server AI');
    };

    wsRef.current.onmessage = (e) => {
      const payload = JSON.parse(e.data);

      if (payload.type === 'no_detection') {
        addLog(payload.correction || 'Vui lòng đứng vào khung hình');
        setLandmarks([]);
      } else if (payload.type === 'success' && payload.landmarks) {
        setScore(payload.score ?? 0);
        setRepCount(payload.counter ?? 0);
        setIsCorrect(payload.is_correct ?? true);
        setLandmarks(payload.landmarks);

        if (payload.correction) addLog(payload.correction);

        // Đọc giọng nói nếu sai form
        if (!payload.is_correct && payload.correction) {
          const now = Date.now();
          if (now - lastSpokenAtRef.current > SPEECH_COOLDOWN_MS) {
            lastSpokenAtRef.current = now;
            Speech.speak(payload.correction, { language: 'vi-VN', rate: 1.1 });
          }
        }
        
        updatePointsSmoothly(payload.landmarks);
      }

      // PONG
      isProcessingRef.current = false;
      if (statusRef.current === 'RUNNING') {
        captureAndSendFrame();
      }
    };

    wsRef.current.onerror = () => {
      setIsConnected(false);
      addLog('Lỗi mất kết nối!');
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [exercise, permission?.granted]);

  // Hàm thêm Log mới nhất lên đầu, giữ tối đa 3 dòng
  const addLog = (newLog: string) => {
    setLogHistory((prev) => {
      if (prev[0] === newLog) return prev; // Chống spam cùng 1 câu
      return [newLog, ...prev].slice(0, 3);
    });
  };

  // --- CHỤP VÀ GỬI ẢNH ---
  const captureAndSendFrame = async () => {
    if (statusRef.current !== 'RUNNING' || !cameraRef.current || isProcessingRef.current) return;
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;

    isProcessingRef.current = true;

    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.05,
        base64: true,
        skipProcessing: true,
        exif: false,
        shutterSound: false,
      });

      if (photo?.base64) {
        wsRef.current.send(JSON.stringify({ frame: photo.base64 }));
      } else {
        isProcessingRef.current = false;
        if (statusRef.current === 'RUNNING') setTimeout(captureAndSendFrame, 50); 
      }
    } catch (e) {
      isProcessingRef.current = false;
      if (statusRef.current === 'RUNNING') setTimeout(captureAndSendFrame, 50);
    }
  };

  // --- ĐIỀU KHIỂN SESSION ---
  const toggleSession = () => {
    if (sessionStatus === 'IDLE' || sessionStatus === 'PAUSED') {
      setSessionStatus('RUNNING');
      addLog('Bắt đầu bài tập!');
      // Mồi phát súng đầu tiên để vòng lặp chạy
      setTimeout(captureAndSendFrame, 100);
    } else {
      setSessionStatus('PAUSED');
      addLog('Đã tạm dừng');
    }
  };

  const endSession = () => {
    setSessionStatus('IDLE');
    setRepCount(0);
    setScore(0);
    setLandmarks([]);
    addLog('Đã kết thúc buổi tập');
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* 1. LAYER CAMERA Ở DƯỚI CÙNG (TRÀN VIỀN) */}
      <CameraView 
        ref={cameraRef} 
        style={StyleSheet.absoluteFill} 
        facing="front" 
      />

      {/* 2. LAYER SKELETON */}
      {sessionStatus !== 'IDLE' && (
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
          {landmarks.length > 0 && (
            <Svg style={StyleSheet.absoluteFill}>
              {POSE_CONNECTIONS.map(([start, end], i) => {
                const p1 = landmarks[start];
                const p2 = landmarks[end];
                if (!p1 || !p2 || p1.visibility < LANDMARK_VISIBILITY_THRESHOLD || p2.visibility < LANDMARK_VISIBILITY_THRESHOLD) return null;
                return (
                  <Line key={`line-${i}`} x1={(1 - p1.x) * SCREEN_W} y1={p1.y * SCREEN_H} x2={(1 - p2.x) * SCREEN_W} y2={p2.y * SCREEN_H} stroke={isCorrect ? "#FF5E0E" : "#E63946"} strokeWidth="4" strokeOpacity={0.8} />
                );
              })}
            </Svg>
          )}

          {landmarks.length > 0 && animatedPoints.map((anim, index) => (
            <Animated.View key={`joint-${index}`} style={[styles.landmarkDot, { backgroundColor: isCorrect ? '#FF5E0E' : '#E63946', width: index > 10 ? 8 : 4, height: index > 10 ? 8 : 4, transform: anim.getTranslateTransform() }]} />
          ))}
        </View>
      )}

      {/* 3. LAYER UI OVERLAY */}
      <SafeAreaView style={styles.overlaySafe} pointerEvents="box-none">
        
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.iconBtn}>
            <Ionicons name="chevron-back" size={28} color="white" />
          </TouchableOpacity>
          <View style={styles.headerTitleContainer}>
            <Text style={styles.exerciseTitle}>{exercise.replace('_', ' ').toUpperCase()}</Text>
          </View>
          <View style={[styles.statusDot, { backgroundColor: isConnected ? '#FF5E0E' : '#E63946' }]} />
        </View>

        {/* KHOẢNG TRỐNG Ở GIỮA ĐỂ NHÌN CAMERA */}
        <View style={{ flex: 1 }} pointerEvents="none" />

        {/* BOTTOM HUD BẢNG ĐIỀU KHIỂN & LOGS */}
        <View style={styles.bottomHUD}>
          
          {/* Thông số Reps & Score */}
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>REPS</Text>
              <Text style={styles.metricValue}>{repCount}</Text>
            </View>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>ĐỘ CHUẨN</Text>
              <Text style={[styles.metricValue, { color: isCorrect ? '#FF5E0E' : '#E63946' }]}>{score}%</Text>
            </View>
          </View>

          {/* Hộp thoại Logs (Feedback gọn gàng) */}
          <View style={styles.logBox}>
            {logHistory.map((log, index) => (
              <Text 
                key={index} 
                style={[
                  styles.logText, 
                  index === 0 ? styles.logTextPrimary : styles.logTextSecondary,
                  { opacity: 1 - index * 0.4 } // Dòng cũ sẽ mờ dần
                ]}
                numberOfLines={1}
              >
                {index === 0 ? `👉 ${log}` : log}
              </Text>
            ))}
          </View>

          {/* Các nút điều khiển Session */}
          <View style={styles.controlsRow}>
            {sessionStatus !== 'IDLE' && (
              <TouchableOpacity style={styles.endBtn} onPress={endSession}>
                <Ionicons name="stop" size={24} color="#FFF" />
              </TouchableOpacity>
            )}

            <TouchableOpacity 
              style={[styles.mainBtn, { backgroundColor: sessionStatus === 'RUNNING' ? '#E63946' : '#FF5E0E' }]} 
              onPress={toggleSession}
            >
              <Ionicons 
                name={sessionStatus === 'RUNNING' ? "pause" : "play"} 
                size={24} 
                color="white" 
                style={{ marginRight: 8 }} 
              />
              <Text style={styles.mainBtnText}>
                {sessionStatus === 'IDLE' ? 'BẮT ĐẦU' : sessionStatus === 'PAUSED' ? 'TIẾP TỤC' : 'TẠM DỪNG'}
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
  
  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 10 },
  iconBtn: { padding: 8, backgroundColor: 'rgba(0,0,0,0.4)', borderRadius: 20 },
  headerTitleContainer: { backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 15 },
  exerciseTitle: { color: 'white', fontSize: 16, fontWeight: '800', letterSpacing: 1 },
  statusDot: { width: 14, height: 14, borderRadius: 7, borderWidth: 2, borderColor: 'white' },

  // Bottom HUD
  bottomHUD: { backgroundColor: 'rgba(15, 15, 15, 0.85)', borderTopLeftRadius: 30, borderTopRightRadius: 30, padding: 20, paddingBottom: Platform.OS === 'ios' ? 10 : 20 },
  
  // Metrics
  metricsRow: { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 15 },
  metricBox: { alignItems: 'center' },
  metricLabel: { color: '#888', fontSize: 12, fontWeight: '700', letterSpacing: 1, marginBottom: 4 },
  metricValue: { color: 'white', fontSize: 40, fontWeight: '900' },

  // Logs
  logBox: { backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 15, padding: 15, marginBottom: 20, minHeight: 90, justifyContent: 'center' },
  logText: { color: 'white', fontWeight: '600', textAlign: 'center', marginBottom: 4 },
  logTextPrimary: { fontSize: 16, color: '#FF5E0E' }, // Đổi highlight log sang Cam Signature
  logTextSecondary: { fontSize: 14, color: '#AAA' },

  // Controls
  controlsRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 15 },
  mainBtn: { flex: 1, flexDirection: 'row', height: 56, borderRadius: 28, justifyContent: 'center', alignItems: 'center', elevation: 5, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 5, shadowOffset: { width: 0, height: 3 } },
  mainBtnText: { color: 'white', fontSize: 16, fontWeight: '800', letterSpacing: 1 },
  endBtn: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#333', justifyContent: 'center', alignItems: 'center' },
});