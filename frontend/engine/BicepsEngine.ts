import * as tf from '@tensorflow/tfjs-core';
import '@tensorflow/tfjs-backend-cpu';
import { LayersModel, loadLayersModel } from '@tensorflow/tfjs-layers';
import { bundleResourceIO } from '@tensorflow/tfjs-react-native';
import scalerData from '../assets/models/bicep_posture/scaler.json';

// Danh sách điểm QUAN TRỌNG y hệt như Python
const IMPORTANT_LMS = [
  "NOSE", "LEFT_SHOULDER", "RIGHT_SHOULDER", "RIGHT_ELBOW",
  "LEFT_ELBOW", "RIGHT_WRIST", "LEFT_WRIST", "LEFT_HIP", "RIGHT_HIP"
];

// Map tên xương ra chỉ số (Index) của MediaPipe (từ 0 đến 32)
const LM_MAP: Record<string, number> = {
  "NOSE": 0, "LEFT_SHOULDER": 11, "RIGHT_SHOULDER": 12,
  "RIGHT_ELBOW": 14, "LEFT_ELBOW": 13, "RIGHT_WRIST": 16,
  "LEFT_WRIST": 15, "LEFT_HIP": 23, "RIGHT_HIP": 24
};

export class BicepEngine {
  private postureModel: LayersModel | null = null;
  private counter = 0;
  private stage = "down";
  private isLoaded = false;
  
  // Thông số từ OOP của ông
  private stageDownThreshold = 120;
  private stageUpThreshold = 90;

  async loadModel() {
    if (this.isLoaded) return;
    try {

      // Remove rn-webgl (needs native ExpoGL, not available in Expo Go) and use CPU instead.
      if (tf.engine().registryFactory['rn-webgl']) {
        try { tf.removeBackend('rn-webgl'); } catch {}
      }
      const ok = await tf.setBackend('cpu');
      await tf.ready();
      console.log("Động cơ TFJS đã nổ máy! Backend:", tf.getBackend(), "setBackend ok:", ok);
      const modelJson = require('../assets/models/bicep_posture/model.json');
      const modelWeights = require('../assets/models/bicep_posture/group1-shard1of1.bin');
      this.postureModel = await loadLayersModel(bundleResourceIO(modelJson, modelWeights));
      this.isLoaded = true;
      console.log("✅ Mô hình AI Tư Thế đã tải xong!");
    } catch (e) {
      console.error("Lỗi khi load AI Model:", e);
    }
  }

  // Cân bằng tọa độ
  private standardScale(features: number[]): number[] {
    return features.map((val, i) => (val - scalerData.mean[i]) / scalerData.scale[i]);
  }

  // Tính góc (Toán học)
  private calculateAngle(point1: any, point2: any, point3: any): number {
    const angleInRad = Math.atan2(point3.y - point2.y, point3.x - point2.x) - 
                       Math.atan2(point1.y - point2.y, point1.x - point2.x);
    let angleInDeg = Math.abs((angleInRad * 180.0) / Math.PI);
    return angleInDeg <= 180 ? angleInDeg : 360 - angleInDeg;
  }

  processFrame(landmarks: any[]) {
    if (!landmarks || landmarks.length === 0 || !this.isLoaded) {
      return { counter: this.counter, isCorrect: true, correction: "Đang chờ..." };
    }

    // Lấy điểm tay PHẢI để đếm Rep (Hoặc ông có thể viết logic tự chọn tay trái/phải)
    const rightShoulder = landmarks[12];
    const rightElbow = landmarks[14];
    const rightWrist = landmarks[16];

    // Gatekeeper
    if (!rightShoulder || rightShoulder.visibility < 0.5) {
      return { counter: this.counter, isCorrect: false, correction: "Vui lòng đứng trọn vẹn vào màn hình" };
    }

    // --- 1. ĐẾM REP (Dùng Toán Học như file Jupyter) ---
    const bicepCurlAngle = this.calculateAngle(rightShoulder, rightElbow, rightWrist);
    
    if (bicepCurlAngle > this.stageDownThreshold) {
      this.stage = "down";
    } else if (bicepCurlAngle < this.stageUpThreshold && this.stage === "down") {
      this.stage = "up";
      this.counter += 1;
    }

    // --- 2. PHÂN TÍCH FORM BẰNG MODEL AI (Thay cho KNN) ---
    // A. Trích xuất đúng 36 giá trị (x,y,z,v) của 9 điểm quan trọng
    const rowFeatures: number[] = [];
    for (const lmName of IMPORTANT_LMS) {
      const idx = LM_MAP[lmName];
      const kp = landmarks[idx];
      if (kp) {
        rowFeatures.push(kp.x, kp.y, kp.z || 0, kp.visibility || 0);
      } else {
        rowFeatures.push(0, 0, 0, 0); // Đề phòng điểm bị mất
      }
    }

    // B. Đẩy qua Scaler và Model
    const scaledFeatures = this.standardScale(rowFeatures);
    const inputTensor = tf.tensor2d([scaledFeatures]);
    const prediction = this.postureModel!.predict(inputTensor) as tf.Tensor;
    const probability = prediction.dataSync()[0]; // Lấy xác suất
    tf.dispose([inputTensor, prediction]); // Giải phóng bộ nhớ

    // C. Đánh giá Posture dựa trên xác suất Model AI
    let isCorrect = true;
    let correctionText = "Form chuẩn! (" + bicepCurlAngle.toFixed(0) + "°)";

    // Giả sử: L (1) là thẳng lưng/đúng, C (0) là ngả lưng/sai
    if (probability < 0.5) {
      isCorrect = false;
      correctionText = "Cảnh báo: Lưng đang ngả về sau! (AI Detect)";
    }

    // Thêm lỗi nhỏ: Nhấc cùi chỏ
    if (rightElbow.y < rightShoulder.y) {
       isCorrect = false;
       correctionText = "Hạ cùi chỏ xuống!";
    }

    return { 
      counter: this.counter, 
      isCorrect, 
      correction: correctionText
    };
  }
}