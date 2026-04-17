from pathlib import Path
import math

import joblib
import numpy as np
import warnings

warnings.filterwarnings("ignore", message="X does not have valid feature names")
# Bỏ import pandas vì nó làm chậm tốc độ load và chiếm nhiều RAM
MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

class SquatCoachEngine:
    # ... (Giữ nguyên các mảng IMPORTANT_LM_NAMES, IMPORTANT_LMS và THRESHOLDS) ...
    IMPORTANT_LM_NAMES = [
        "NOSE", "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP",
        "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE", "RIGHT_ANKLE",
    ]
    IMPORTANT_LMS = [0, 11, 12, 23, 24, 25, 26, 27, 28]

    PREDICTION_THRESHOLD = 0.65
    VIS_THRESH = 0.55
    FOOT_SHOULDER_RATIO_THRESHOLDS = (1.2, 2.8)
    KNEE_FOOT_RATIO_THRESHOLDS = {
        "up": (0.5, 1.0),
        "middle": (0.7, 1.0),
        "down": (0.7, 1.1),
    }

    def __init__(self):
        model_path = MODEL_DIR / "squat_model.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"Missing squat model at {model_path}")

        self.model = joblib.load(model_path)
        self.counter = 0
        self.current_stage = ""

    @staticmethod
    def _distance(p1, p2):
        # Tối ưu: Dùng hypotenuse của Python C-core nhanh hơn tính thủ công
        return math.hypot(p2.x - p1.x, p2.y - p1.y)

    @staticmethod
    def _normalize_stage(prediction):
        if isinstance(prediction, str):
            return "down" if prediction.lower().startswith("down") else "up"
        try:
            return "down" if int(prediction) == 0 else "up"
        except (TypeError, ValueError):
            return "up"

    def _analyze_placement(self, landmarks):
        # Lấy Index chân từ MediaPipe (Lưu ý: Ankle (Mắt cá) hay Foot_Index (Mũi chân)?)
        # Ở đây tôi đổi 31, 32 (Foot Index) thành 27, 28 (Ankle) để đồng bộ với IMPORTANT_LMS
        l_sh = landmarks[11]
        r_sh = landmarks[12]
        l_knee = landmarks[25]
        r_knee = landmarks[26]
        l_ankle = landmarks[27] 
        r_ankle = landmarks[28]

        # Kiểm tra nhanh: Nếu khuất 1 trong 6 điểm thì bỏ qua tính toán
        if min(
            l_ankle.visibility, r_ankle.visibility,
            l_knee.visibility, r_knee.visibility,
            l_sh.visibility, r_sh.visibility
        ) < self.VIS_THRESH:
            return "unknown", "unknown"

        shoulder_w = self._distance(l_sh, r_sh)
        foot_w = self._distance(l_ankle, r_ankle) # Tính khoảng cách gót chân (Mắt cá) thay vì mũi chân
        
        # Ngăn lỗi Division by Zero
        if shoulder_w < 0.001 or foot_w < 0.001:
            return "unknown", "unknown"

        foot_shoulder_ratio = round(foot_w / shoulder_w, 1)
        lo, hi = self.FOOT_SHOULDER_RATIO_THRESHOLDS
        feet_status = "too tight" if foot_shoulder_ratio < lo else "too wide" if foot_shoulder_ratio > hi else "correct"

        # Tính toán khoảng cách gối
        stage_key = self.current_stage if self.current_stage in self.KNEE_FOOT_RATIO_THRESHOLDS else "middle"
        knee_w = self._distance(l_knee, r_knee)
        knee_foot_ratio = round(knee_w / foot_w, 1)
        kmin, kmax = self.KNEE_FOOT_RATIO_THRESHOLDS[stage_key]
        
        knee_status = "too tight" if knee_foot_ratio < kmin else "too wide" if knee_foot_ratio > kmax else "correct"

        return feet_status, knee_status

    def process_frame(self, landmarks):
        # Trích xuất đúng 36 features (Nhanh hơn List Comprehension)
        row = []
        for idx in self.IMPORTANT_LMS:
            lm = landmarks[idx]
            row.extend([lm.x, lm.y, lm.z, lm.visibility])

        # Đưa thẳng vào numpy array (Không cần tạo pandas.DataFrame)
        X = np.array([row])

        try:
            # Model nhận input 2D array
            predicted_class = self.model.predict(X)[0]
            probs = self.model.predict_proba(X)[0]
            prob = float(np.max(probs))
        except Exception as e:
            return {
                "counter": self.counter,
                "score": 0,
                "is_correct": False,
                "correction": "Đang định vị tư thế...", # Câu này thân thiện hơn là nhả cái "Model Error"
            }

        stage = self._normalize_stage(predicted_class)

        # Chống đếm đúp (Debounce)
        if stage == "down" and prob >= self.PREDICTION_THRESHOLD:
            self.current_stage = "down"
        elif (
            self.current_stage == "down"
            and stage == "up"
            and prob >= self.PREDICTION_THRESHOLD
        ):
            self.current_stage = "up"
            self.counter += 1

        # Check form
        feet_status, knee_status = self._analyze_placement(landmarks)

        feedback = []
        if feet_status == "too tight":
            feedback.append("Đứng rộng chân hơn một chút!")
        elif feet_status == "too wide":
            feedback.append("Khép chân lại gần vai hơn!")

        if feet_status == "correct":
            if knee_status == "too tight":
                feedback.append("Đẩy đầu gối ra ngoài!")
            elif knee_status == "too wide":
                feedback.append("Giữ gối thẳng hàng với mũi chân!")

        is_correct = len(feedback) == 0
        correction_text = " - ".join(feedback) if feedback else "Form rất nét, tiếp tục!"

        return {
            "counter": self.counter,
            "score": round(prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text,
            "stage": self.current_stage or stage,
            "feet": feet_status,
            "knee": knee_status,
        }