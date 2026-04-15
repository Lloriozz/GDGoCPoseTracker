import joblib
import numpy as np
from pathlib import Path

# Khai báo đường dẫn chuẩn
MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

class PlankCoachEngine:
    def __init__(self):
        # Đường dẫn tới model trên H100
        self.model = joblib.load(MODEL_DIR / 'plank_model.pkl')
        self.scaler = joblib.load(MODEL_DIR / 'plank_input_scaler.pkl')
        self.PREDICTION_PROB_THRESHOLD = 0.6
        self.counter = 0 # Với Plank, ta thường không đếm Rep. Frontend sẽ tự lo đếm ngược thời gian.

    def process_frame(self, landmarks):
        # 1. Trích xuất đúng 17 điểm quan trọng theo code của ông
        IMPORTANT_LMS = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
        
        row = []
        for idx in IMPORTANT_LMS:
            lm = landmarks[idx]
            row.extend([lm.x, lm.y, lm.z, lm.visibility])
        
        # 2. Scale và Predict
        X_scaled = self.scaler.transform(np.array(row).reshape(1, -1))
        predicted_class = self.model.predict(X_scaled)[0] # 'C', 'L', 'H'
        prob = self.model.predict_proba(X_scaled).max()

        # 3. Phân tích lỗi Form
        feedback = []
        is_correct = True

        if prob >= self.PREDICTION_PROB_THRESHOLD:
            if predicted_class == "L":
                feedback.append("Đừng võng lưng! Siết chặt cơ bụng lại.")
                is_correct = False
            elif predicted_class == "H":
                feedback.append("Hông đang quá cao! Hạ thấp mông xuống.")
                is_correct = False
            elif predicted_class == "C":
                is_correct = True
        else:
            # Model không tự tin lắm (dưới 60%)
            feedback.append("Đang phân tích form...")
            is_correct = False

        # 4. Đóng gói kết quả gửi về Mobile
        correction_text = " - ".join(feedback) if not is_correct else "Giữ form rất tốt!"

        return {
            "counter": self.counter, # Luôn trả về 0 hoặc có thể nâng cấp đếm số frame giữ chuẩn form
            "score": round(prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text
        }