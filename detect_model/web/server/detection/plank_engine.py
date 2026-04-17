import warnings
import joblib
import numpy as np
from pathlib import Path

# Tắt cảnh báo spam log để tránh làm chậm Terminal của Server
warnings.filterwarnings("ignore", message="X does not have valid feature names")

MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

class PlankCoachEngine:
    # Tối ưu 1: Rút mảng này ra Class-level để không phải khởi tạo lại vùng nhớ mỗi 0.03s
    IMPORTANT_LMS = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]

    def __init__(self):
        self.model = joblib.load(MODEL_DIR / 'plank_model.pkl')
        self.scaler = joblib.load(MODEL_DIR / 'plank_input_scaler.pkl')
        self.PREDICTION_PROB_THRESHOLD = 0.6
        self.VIS_THRESH = 0.5 # Ngưỡng tin cậy của camera
        self.counter = 0

    def process_frame(self, landmarks):
        # Tối ưu 2: Khiên chắn Visibility (Đặc biệt quan trọng cho Plank)
        # Plank là tư thế nằm ngang, rất dễ bị khuất Camera. Nếu không thấy Vai hoặc Hông, cấm Model chạy để tránh "ảo giác".
        core_vis = min(
            landmarks[11].visibility, landmarks[12].visibility, # Vai
            landmarks[23].visibility, landmarks[24].visibility  # Hông
        )
        
        if core_vis < self.VIS_THRESH:
            return {
                "counter": self.counter,
                "score": 0,
                "is_correct": False,
                "correction": "Vui lòng để toàn bộ lưng và hông vào khung hình!"
            }

        # Tối ưu 3: Trích xuất mảng 1 chiều trực tiếp bằng List Comprehension phẳng
        row = [val for idx in self.IMPORTANT_LMS for val in (
            landmarks[idx].x, landmarks[idx].y, landmarks[idx].z, landmarks[idx].visibility
        )]
        
        # Scale và Predict (Truyền thẳng np.array([row]) là ma trận 2D, không cần tốn hàm .reshape)
        X_scaled = self.scaler.transform(np.array([row]))
        
        try:
            predicted_class = self.model.predict(X_scaled)[0] # 'C', 'L', 'H'
            prob = float(np.max(self.model.predict_proba(X_scaled)))
        except Exception as e:
            return {"counter": self.counter, "score": 0, "is_correct": False, "correction": "Đang định vị tư thế..."}

        # Phân tích lỗi Form
        feedback = []
        is_correct = True

        if prob >= self.PREDICTION_PROB_THRESHOLD:
            if predicted_class == "L":
                feedback.append("Võng lưng! Gồng chặt cơ bụng và nâng hông lên.")
                is_correct = False
            elif predicted_class == "H":
                feedback.append("Hông quá cao! Hạ thấp mông xuống tạo đường thẳng.")
                is_correct = False
            elif predicted_class == "C":
                is_correct = True
        else:
            # Model không tự tin lắm
            feedback.append("Đang phân tích form...")
            is_correct = False

        # Đóng gói kết quả
        correction_text = " - ".join(feedback) if not is_correct else "Giữ form rất tốt! Cố lên!"

        return {
            "counter": self.counter, 
            "score": round(prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text
        }