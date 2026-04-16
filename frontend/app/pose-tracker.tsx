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
import Svg, { Line } from 'react-native-svg';

import { POSE_API_BASE_URL } from '../constants/api'; // Chỉ cần giữ lại Base URL

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

// 33 điểm chuẩn Mediapipe
const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
  [27, 31], [28, 32], [27, 29], [28, 30],
  [0, 1], [1, 2], [2, 3], [0, 4], [4, 5], [5, 6],
];

const ANIMATION_DURATION = 80; // Giảm duration xuống để điểm chạy nhanh hơn, hợp với FPS cao
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
  const lastSpokenAtRef = useRef(0);
  
  // Ống nước WebSocket
  const ws = useRef<WebSocket | null>(null);

  // Animated values để nội suy chuyển động
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

  // --- HÀM CẬP NHẬT ĐIỂM MƯỢT MÀ ---
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

  const handleBack = useCallback(() => {
    captureEnabledRef.current = false;
    Speech.stop();
    ws.current?.close(); // Đóng socket khi back ra ngoài
    router.back();
  }, [router]);

  useEffect(() => {
    if (!permission?.granted) {
      void requestPermission();
    }
  }, [permission?.granted, requestPermission]);

  // --- HÀM BƠM ẢNH VÀO WEBSOCKET ---
  const captureAndAnalyzeFrame = useCallback(async () => {
    if (!captureEnabledRef.current || requestInFlightRef.current) return;
    if (!cameraRef.current || !ws.current || ws.current.readyState !== WebSocket.OPEN) {
      // Nếu socket chưa mở, chờ 100ms rồi thử lại
      if (captureEnabledRef.current) setTimeout(captureAndAnalyzeFrame, 100);
      return;
    }

    requestInFlightRef.current = true; // Khóa không cho chụp frame mới khi frame cũ chưa xử lý xong

    try {
      setProgressLabel('Streaming...');
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.1, // Nén tối đa để truyền siêu nhanh
        base64: true,
        skipProcessing: true,
        exif: false,
        shutterSound: false,
      });

      if (photo?.base64) {
        // Gửi qua WebSocket
        ws.current.send(JSON.stringify({ frame: photo.base64 }));
        // LƯU Ý: Không set requestInFlightRef = false ở đây. 
        // Ta sẽ mở khóa nó ở onmessage (Khi server đã trả lời xong)
      } else {
        requestInFlightRef.current = false;
        setTimeout(captureAndAnalyzeFrame, 30);
      }
    } catch (e) {
      console.error('[Camera] Error:', e);
      requestInFlightRef.current = false;
      setTimeout(captureAndAnalyzeFrame, 100);
    }
  }, []);

  // --- QUẢN LÝ KẾT NỐI WEBSOCKET ---
  useEffect(() => {
    if (!permission?.granted || !POSE_API_BASE_URL) return;

    // Chuyển đổi http:// thành ws://
    const wsUrl = POSE_API_BASE_URL.replace(/^http/, 'ws') + '/ws/pose/';
    console.log('[WS] Connecting to:', wsUrl);
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('[WS] Connected!');
      setIsConnected(true);
      setProgressLabel('Connected to Server');
      captureEnabledRef.current = true;
      captureAndAnalyzeFrame(); // Bắt đầu vòng lặp Real-time
    };

    ws.current.onmessage = (e) => {
      // Nhận được kết quả -> Mở khóa Camera để chụp frame tiếp theo lập tức
      requestInFlightRef.current = false; 

      const payload = JSON.parse(e.data);

      if (payload.type === 'no_detection' || payload.correction === 'Vui lòng đứng trọn vẹn vào khung hình!') {
        setProgressLabel('No pose detected');
        setCorrection(payload.correction || 'Step into frame');
        setLandmarks([]);
      } else if (payload.landmarks) {
        setProgressLabel('Pose detected');
        setScore(payload.score ?? 0);
        setRepCount(payload.counter ?? 0); // Đã đồng bộ chữ "counter" với Backend
        setIsCorrect(payload.is_correct ?? true);
        setCorrection(payload.correction);
        setLandmarks(payload.landmarks);

        if (!payload.is_correct && payload.correction) {
          const now = Date.now();
          if (now - lastSpokenAtRef.current > SPEECH_COOLDOWN_MS) {
            lastSpokenAtRef.current = now;
            Speech.speak(payload.correction, { language: 'vi-VN', rate: 1.0 });
          }
        }
        
        updatePointsSmoothly(payload.landmarks);
      }

      // Kích hoạt loop chụp ảnh ngay lập tức
      if (captureEnabledRef.current) {
        setTimeout(captureAndAnalyzeFrame, 20); // Delay 20ms để máy thở một chút
      }
    };

    ws.current.onerror = (e) => {
      console.error('[WS] Error:', e);
      setIsConnected(false);
      setProgressLabel('Connection Lost');
      requestInFlightRef.current = false; // Mở khóa để thử lại
    };

    ws.current.onclose = () => {
      console.log('[WS] Closed');
      setIsConnected(false);
      setProgressLabel('Disconnected');
    };

    return () => {
      captureEnabledRef.current = false;
      ws.current?.close();
      Speech.stop();
    };
  }, [permission?.granted, captureAndAnalyzeFrame]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* 1. Camera View */}
      <CameraView 
        ref={cameraRef} 
        style={StyleSheet.absoluteFill} 
        facing="front" 
      />

      {/* 2. Skeleton Layer (Vẽ đường nối SVG) */}
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        
        {landmarks.length > 0 && (
          <Svg style={StyleSheet.absoluteFill}>
            {POSE_CONNECTIONS.map(([start, end], i) => {
              const p1 = landmarks[start];
              const p2 = landmarks[end];
              
              if (!p1 || !p2 || p1.visibility < LANDMARK_VISIBILITY_THRESHOLD || p2.visibility < LANDMARK_VISIBILITY_THRESHOLD) {
                return null;
              }

              return (
                <Line
                  key={`line-${i}`}
                  x1={(1 - p1.x) * SCREEN_W}
                  y1={p1.y * SCREEN_H}
                  x2={(1 - p2.x) * SCREEN_W}
                  y2={p2.y * SCREEN_H}
                  stroke={isCorrect ? "#52B788" : "#E63946"}
                  strokeWidth="4"
                  strokeOpacity={0.8}
                />
              );
            })}
          </Svg>
        )}

        {/* 3. Landmarks Dots (Các điểm bám theo người) */}
        {landmarks.length > 0 && animatedPoints.map((anim, index) => (
          <Animated.View
            key={`joint-${index}`}
            style={[
              styles.landmarkDot,
              {
                backgroundColor: isCorrect ? '#52B788' : '#E63946',
                borderColor: 'white',
                borderWidth: 1,
                width: index > 10 ? 8 : 4,
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
            <Text style={styles.correctionText}>{correction || 'Đang kết nối AI...'}</Text>
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