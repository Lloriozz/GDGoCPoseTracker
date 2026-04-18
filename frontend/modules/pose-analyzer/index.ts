import { requireNativeModule } from 'expo-modules-core';

let PoseAnalyzerNative: any = null;
try {
  PoseAnalyzerNative = requireNativeModule('PoseAnalyzer');
} catch {
  console.warn('[PoseAnalyzer] Native module not available — CoreML inference disabled.');
}

export interface Landmark {
  x: number;
  y: number;
  z: number;
  visibility: number;
}

export interface AnalysisResult {
  landmarks: Landmark[];
  correction: string;
  isCorrect: boolean;
  counter: number;
  score: number;
  stage?: string;
  error?: string;
}

/**
 * Analyze a single camera frame on-device using Vision + CoreML.
 *
 * @param base64Jpeg   Base64-encoded JPEG (no data: prefix needed)
 * @param exercise     One of: 'bicep_curl' | 'squat' | 'lunge' | 'plank'
 */
export async function analyzeFrame(
  base64Jpeg: string,
  exercise: string
): Promise<AnalysisResult> {
  if (!PoseAnalyzerNative) {
    return {
      landmarks: [],
      correction: 'CoreML not available — rebuild with npx expo run:ios',
      isCorrect: false,
      counter: 0,
      score: 0,
    };
  }
  return PoseAnalyzerNative.analyzeFrame(base64Jpeg, exercise);
}
