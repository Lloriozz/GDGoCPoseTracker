from pathlib import Path
import math

import joblib
import numpy as np


MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"


class SquatCoachEngine:
    IMPORTANT_LMS = [0, 11, 12, 23, 24, 25, 26, 27, 28]
    PREDICTION_THRESHOLD = 0.7

    def __init__(self):
        model_path = MODEL_DIR / "squat_model.pkl"
        scaler_path = MODEL_DIR / "input_scaler.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Missing squat count model at {model_path}")
            
        # Load model chính
        self.model = joblib.load(model_path)
        
        # Kiểm tra scaler, nếu không có thì set là None thay vì raise lỗi
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
            print("✅ Loaded Squat Scaler")
        else:
            self.scaler = None
            print("⚠️ Warning: Squat Scaler not found, using raw landmarks or default scaling.")

    def calculate_distance(self, p1, p2):
        return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

    def _normalize_stage(self, prediction):
        if isinstance(prediction, str):
            return "down" if prediction.lower() == "down" else "up"

        try:
            return "down" if int(prediction) == 0 else "up"
        except (TypeError, ValueError):
            return "up"

    def process_frame(self, landmarks):
        row = []
        for idx in self.IMPORTANT_LMS:
            lm = landmarks[idx]
            row.extend([lm.x, lm.y, lm.z, lm.visibility])

        X_scaled = self.scaler.transform(np.array(row, dtype=float).reshape(1, -1))
        prediction = self.model.predict(X_scaled)
        prob = float(np.max(self.count_model.predict_proba(X_scaled)))

        stage = self._normalize_stage(prediction)
        if stage == "down" and prob >= self.PREDICTION_THRESHOLD:
            self.current_stage = "down"
        elif (
            self.current_stage == "down"
            and stage == "up"
            and prob >= self.PREDICTION_THRESHOLD
        ):
            self.current_stage = "up"
            self.counter += 1

        feedback = []

        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_foot = landmarks[31]
        right_foot = landmarks[32]
        left_knee = landmarks[25]
        right_knee = landmarks[26]

        if (
            left_shoulder.visibility > 0.6
            and right_shoulder.visibility > 0.6
            and left_foot.visibility > 0.6
            and right_foot.visibility > 0.6
        ):
            shoulder_width = self.calculate_distance(left_shoulder, right_shoulder)
            foot_width = self.calculate_distance(left_foot, right_foot)

            if shoulder_width > 0:
                ratio_ft_sh = foot_width / shoulder_width
                if ratio_ft_sh < 1.2:
                    feedback.append("Spread your feet wider!")
                elif ratio_ft_sh > 2.8:
                    feedback.append("Narrow your stance!")

            if (
                self.current_stage == "down"
                and foot_width > 0
                and left_knee.visibility > 0.6
                and right_knee.visibility > 0.6
            ):
                knee_width = self.calculate_distance(left_knee, right_knee)
                ratio_kn_ft = knee_width / foot_width
                if ratio_kn_ft < 0.7:
                    feedback.append("Push your knees out!")

        is_correct = len(feedback) == 0
        correction_text = " - ".join(feedback) if feedback else "Great form!"

        return {
            "counter": self.counter,
            "score": round(prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text,
        }
