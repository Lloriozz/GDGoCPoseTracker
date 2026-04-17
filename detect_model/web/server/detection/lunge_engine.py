import warnings
import joblib
import numpy as np
import math
from pathlib import Path

# Tắt cảnh báo spam log của scikit-learn
warnings.filterwarnings("ignore", message="X does not have valid feature names")

MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

class LungeCoachEngine:
    # Gom index ra class-level để không bị khởi tạo lại mỗi frame (Tăng tốc độ)
    IMPORTANT_LMS = [0, 11, 12, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
    
    def __init__(self):
        self.stage_model = joblib.load(MODEL_DIR / 'lunge_stage_model.pkl')
        self.err_model = joblib.load(MODEL_DIR / 'lunge_err_model.pkl')
        self.scaler = joblib.load(MODEL_DIR / 'lunge_input_scaler.pkl')

        self.current_stage = "init"
        self.counter = 0
        self.PREDICTION_PROB_THRESHOLD = 0.70
        self.KNEE_ANGLE_THRESHOLD = [60, 125]
        self.VIS_THRESH = 0.5 # Ngưỡng tin cậy của mắt camera

    def calculate_angle(self, a, b, c):
        # Tính góc 2D (Chỉ chính xác khi user quay ngang người - Side view)
        ang = math.degrees(math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x))
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def process_frame(self, landmarks):
        # Tối ưu siêu tốc 1: Dùng List Comprehension kiểu phẳng (Flattening) thay vì dùng vòng lặp và .extend()
        # Nhanh hơn khoảng 30% trong các vòng lặp xử lý liên tục
        row = [val for idx in self.IMPORTANT_LMS for val in (
            landmarks[idx].x, landmarks[idx].y, landmarks[idx].z, landmarks[idx].visibility
        )]
        
        # Scale input & Predict
        X_scaled = self.scaler.transform(np.array([row])) 
        
        try:
            stage_pred = self.stage_model.predict(X_scaled)[0] # 'I', 'M', 'D'
            stage_prob = float(np.max(self.stage_model.predict_proba(X_scaled)))
        except Exception as e:
            return {"counter": self.counter, "score": 0, "is_correct": False, "correction": "Đang định vị tư thế...", "stage": self.current_stage}

        # Logic đếm Rep (State Machine mượt mà)
        if stage_pred == 'D' and stage_prob >= self.PREDICTION_PROB_THRESHOLD:
            self.current_stage = "down"
        elif stage_pred == 'M' and stage_prob >= self.PREDICTION_PROB_THRESHOLD:
            self.current_stage = "mid"
        elif stage_pred == 'I' and stage_prob >= self.PREDICTION_PROB_THRESHOLD:
            if self.current_stage in ['down', 'mid']:
                self.counter += 1
            self.current_stage = "init"

        # Logic Sửa Form
        feedback = []
        is_correct = True

        # Tối ưu 2: CHỈ phân tích lỗi khi ở 'down' VÀ model xác suất cao
        if self.current_stage == "down":
            err_pred = self.err_model.predict(X_scaled)[0]
            err_prob = float(np.max(self.err_model.predict_proba(X_scaled)))
            
            # 1. Bắt lỗi đầu gối vượt mũi chân bằng Model AI
            if err_pred == 'L' and err_prob >= self.PREDICTION_PROB_THRESHOLD:
                feedback.append("Đầu gối đang vượt quá mũi chân!")
                is_correct = False
            else:
                # 2. Bắt lỗi góc gập gối bằng Toán học (Cần khiên chắn Visibility)
                # Đánh giá độ tin cậy của từng chân (Hông, Gối, Mắt cá)
                L_vis = min(landmarks[23].visibility, landmarks[25].visibility, landmarks[27].visibility)
                R_vis = min(landmarks[24].visibility, landmarks[26].visibility, landmarks[28].visibility)

                # Chỉ tính toán và bắt lỗi cái chân nào mà Camera NHÌN THẤY RÕ
                if L_vis > self.VIS_THRESH:
                    L_angle = self.calculate_angle(landmarks[23], landmarks[25], landmarks[27])
                    if not (self.KNEE_ANGLE_THRESHOLD[0] <= L_angle <= self.KNEE_ANGLE_THRESHOLD[1]):
                        feedback.append("Chân trái: Hạ gối vuông góc 90 độ!")
                        is_correct = False
                
                if R_vis > self.VIS_THRESH:
                    R_angle = self.calculate_angle(landmarks[24], landmarks[26], landmarks[28])
                    if not (self.KNEE_ANGLE_THRESHOLD[0] <= R_angle <= self.KNEE_ANGLE_THRESHOLD[1]):
                        feedback.append("Chân phải: Hạ gối vuông góc 90 độ!")
                        is_correct = False

        correction_text = " - ".join(feedback) if feedback else ("Form lunge tốt!" if self.current_stage == "down" else "Sẵn sàng...")

        return {
            "counter": self.counter,
            "score": round(stage_prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text,
            "stage": self.current_stage
        }