import * as tf from '@tensorflow/tfjs-core';
import { LayersModel, loadLayersModel } from '@tensorflow/tfjs-layers';
import { bundleResourceIO } from '@tensorflow/tfjs-react-native';

// Scaler parameters exported from the Python notebook (scaler.json)
// Shape: { mean: number[], scale: number[] } — 36 values each (9 landmarks × 4 features)
// eslint-disable-next-line @typescript-eslint/no-var-requires
const scalerData: { mean: number[]; scale: number[] } = require('../assets/models/bicep_posture/scaler.json');

// ---------------------------------------------------------------------------
// Landmark indices (MediaPipe Pose — 33 points total)
// ---------------------------------------------------------------------------
const LM_NOSE           = 0;
const LM_LEFT_SHOULDER  = 11;
const LM_RIGHT_SHOULDER = 12;
const LM_LEFT_ELBOW     = 13;
const LM_RIGHT_ELBOW    = 14;
const LM_LEFT_WRIST     = 15;
const LM_RIGHT_WRIST    = 16;
const LM_LEFT_HIP       = 23;
const LM_RIGHT_HIP      = 24;

// The exact extraction order the Python scaler was trained on.
// Must match the notebook: NOSE, L_SHOULDER, R_SHOULDER, R_ELBOW, L_ELBOW, R_WRIST, L_WRIST, L_HIP, R_HIP
const FEATURE_LANDMARK_INDICES = [
  LM_NOSE,
  LM_LEFT_SHOULDER,
  LM_RIGHT_SHOULDER,
  LM_RIGHT_ELBOW,
  LM_LEFT_ELBOW,
  LM_RIGHT_WRIST,
  LM_LEFT_WRIST,
  LM_LEFT_HIP,
  LM_RIGHT_HIP,
];

// Rep-counting angle thresholds (degrees)
const STAGE_DOWN_THRESHOLD = 120; // arm is extended  → stage = "down"
const STAGE_UP_THRESHOLD   = 90;  // arm is curled    → stage = "up" → count rep

// Minimum landmark visibility to trust a point
const VISIBILITY_THRESHOLD = 0.5;

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------
export interface EngineResult {
  counter: number;
  isCorrect: boolean;
  correction: string;
}

// ---------------------------------------------------------------------------
// BicepEngine
// ---------------------------------------------------------------------------
export class BicepEngine {
  private postureModel: LayersModel | null = null;
  private counter = 0;
  private stage: 'up' | 'down' = 'down';
  private isLoaded = false;

  // -------------------------------------------------------------------------
  // loadModel()
  // Call once after mounting (e.g. inside useEffect).
  // Uses bundleResourceIO so Metro packs the weights into the JS bundle.
  // -------------------------------------------------------------------------
  async loadModel(): Promise<void> {
    if (this.isLoaded) return;

    try {
      // require() tells Metro to bundle these files at build-time
      const modelJson    = require('../assets/models/bicep_posture/model.json');
      const modelWeights = require('../assets/models/bicep_posture/group1-shard1of1.bin');

      this.postureModel = await loadLayersModel(
        bundleResourceIO(modelJson, modelWeights)
      );

      this.isLoaded = true;
      console.log('[BicepEngine] ✅ Model loaded successfully.');
    } catch (e) {
      console.error('[BicepEngine] ❌ Failed to load model:', e);
    }
  }

  // -------------------------------------------------------------------------
  // calculateAngle()
  // Returns the absolute angle (0–360°) at vertex `b` formed by points a-b-c.
  // Each point must have at least { x: number, y: number }.
  // -------------------------------------------------------------------------
  private calculateAngle(
    a: { x: number; y: number },
    b: { x: number; y: number },
    c: { x: number; y: number },
  ): number {
    const radians =
      Math.atan2(c.y - b.y, c.x - b.x) -
      Math.atan2(a.y - b.y, a.x - b.x);

    let deg = Math.abs((radians * 180.0) / Math.PI);
    if (deg > 180) deg = 360 - deg;
    return deg;
  }

  // -------------------------------------------------------------------------
  // standardScale()
  // Replicates sklearn StandardScaler: (val - mean) / scale
  // -------------------------------------------------------------------------
  private standardScale(features: number[]): number[] {
    return features.map(
      (val, i) => (val - scalerData.mean[i]) / scalerData.scale[i]
    );
  }

  // -------------------------------------------------------------------------
  // processFrame()
  // Main method — call every time a new set of landmarks arrives from camera.
  //
  // @param landmarks  Array[33] of { x, y, z?, visibility? } from MediaPipe
  // @returns          { counter, isCorrect, correction }
  // -------------------------------------------------------------------------
  processFrame(landmarks: any[]): EngineResult {
    // Guard: nothing to process
    if (!landmarks || landmarks.length === 0) {
      return { counter: this.counter, isCorrect: true, correction: 'Đang chờ khung hình...' };
    }

    // Model not ready yet — still return partial rep-count info
    if (!this.isLoaded || !this.postureModel) {
      return { counter: this.counter, isCorrect: true, correction: 'Đang tải mô hình AI...' };
    }

    // --- GATEKEEPER: right shoulder must be clearly visible ----------------
    const rightShoulder = landmarks[LM_RIGHT_SHOULDER];
    if (!rightShoulder || (rightShoulder.visibility ?? 0) < VISIBILITY_THRESHOLD) {
      return {
        counter: this.counter,
        isCorrect: false,
        correction: 'Vui lòng đứng trọn vẹn vào màn hình',
      };
    }

    const rightElbow = landmarks[LM_RIGHT_ELBOW];
    const rightWrist = landmarks[LM_RIGHT_WRIST];

    // --- MATH LOGIC: rep counting via joint angle --------------------------
    const angle = this.calculateAngle(rightShoulder, rightElbow, rightWrist);

    if (angle > STAGE_DOWN_THRESHOLD) {
      // Arm is fully extended → reset stage so next curl counts
      this.stage = 'down';
    } else if (angle < STAGE_UP_THRESHOLD && this.stage === 'down') {
      // Arm curled past threshold → complete one rep
      this.stage = 'up';
      this.counter += 1;
    }

    // --- ML LOGIC: posture evaluation via Neural Network -------------------

    // A. Extract exactly 36 features: (x, y, z, visibility) × 9 landmarks
    //    in the same order the Python scaler was fitted on.
    const rawFeatures: number[] = [];
    for (const idx of FEATURE_LANDMARK_INDICES) {
      const lm = landmarks[idx];
      if (lm) {
        rawFeatures.push(lm.x, lm.y, lm.z ?? 0, lm.visibility ?? 0);
      } else {
        rawFeatures.push(0, 0, 0, 0); // safety fallback for missing point
      }
    }

    // B. Standardise using exported scaler parameters
    const scaledFeatures = this.standardScale(rawFeatures);

    // C. Run inference — MUST dispose tensors to prevent memory leaks
    const inputTensor  = tf.tensor2d([scaledFeatures]);                          // shape [1, 36]
    const outputTensor = this.postureModel.predict(inputTensor) as tf.Tensor;   // shape [1, 1]
    const probability  = outputTensor.dataSync()[0];                             // single float
    tf.dispose([inputTensor, outputTensor]);                                     // 🧹 cleanup

    // D. Interpret prediction
    //    Training labels: C (0) = curled/good posture, L (1) = lean-back error
    //    probability > 0.5 → model says "L" → lean back detected
    let isCorrect   = true;
    let correction  = `Form chuẩn! (${angle.toFixed(0)}°)`;

    if (probability > 0.5) {
      // Model detected lean-back posture
      isCorrect  = false;
      correction = 'Cảnh báo: Lưng đang ngả về sau!';
    }

    // E. Additional geometric rule: elbow should NOT rise above shoulder
    if (rightElbow && rightShoulder && rightElbow.y < rightShoulder.y) {
      isCorrect  = false;
      correction = 'Hạ cùi chỏ xuống! Giữ cánh tay sát người.';
    }

    return {
      counter: this.counter,
      isCorrect,
      correction,
    };
  }

  // -------------------------------------------------------------------------
  // reset()
  // Resets rep counter and stage (e.g. when user starts a new session).
  // -------------------------------------------------------------------------
  reset(): void {
    this.counter = 0;
    this.stage   = 'down';
  }
}
