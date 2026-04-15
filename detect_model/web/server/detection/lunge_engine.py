import joblib
import numpy as np
import math
from pathlib import Path

# Khai báo đường dẫn chuẩn
MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

class LungeCoachEngine:
    def __init__(self):
        # Đường dẫn tới model trên H100 (Ông nhớ sửa lại đường dẫn cho chuẩn nhé)
        self.stage_model = joblib.load(MODEL_DIR / 'lunge_stage_model.pkl')
        self.err_model = joblib.load(MODEL_DIR / 'lunge_err_model.pkl')
        self.scaler = joblib.load(MODEL_DIR / 'lunge_input_scaler.pkl')

        self.current_stage = "init"
        self.counter = 0
        self.PREDICTION_PROB_THRESHOLD = 0.8
        self.KNEE_ANGLE_THRESHOLD = [60, 125]

    def calculate_angle(self, a, b, c):
        # Tính góc giữa 3 điểm
        ang = math.degrees(math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x))
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def process_frame(self, landmarks):
        # 1. Trích xuất đúng 13 điểm quan trọng (Theo code của ông)
        IMPORTANT_LMS = [0, 11, 12, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
        
        row = []
        for idx in IMPORTANT_LMS:
            lm = landmarks[idx]
            row.extend([lm.x, lm.y, lm.z, lm.visibility])
        
        # 2. Scale và Predict Stage
        X_scaled = self.scaler.transform(np.array(row).reshape(1, -1))
        stage_pred = self.stage_model.predict(X_scaled)[0] # 'I', 'M', 'D'
        stage_prob = self.stage_model.predict_proba(X_scaled).max()

        # 3. Logic đếm Rep
        if stage_pred == 'D' and stage_prob >= self.PREDICTION_PROB_THRESHOLD:
            if self.current_stage in ['init', 'mid']:
                self.counter += 1
            self.current_stage = "down"
        elif stage_pred == 'M' and stage_prob >= self.PREDICTION_PROB_THRESHOLD:
            self.current_stage = "mid"
        elif stage_pred == 'I' and stage_prob >= self.PREDICTION_PROB_THRESHOLD:
            self.current_stage = "init"

        # 4. Logic Sửa Form (Chỉ bắt lỗi khi đang ở trạng thái DOWN)
        feedback = []
        is_correct = True
        score = stage_prob # Lấy điểm tự tin của pose

        if self.current_stage == "down":
            # --- Check lỗi 1: Knee Over Toe (Đầu gối vượt mũi chân) bằng Model ---
            err_pred = self.err_model.predict(X_scaled)[0] # 'L' (Lỗi) hoặc 'C' (Chuẩn)
            err_prob = self.err_model.predict_proba(X_scaled).max()
            
            if err_pred == 'L' and err_prob >= self.PREDICTION_PROB_THRESHOLD:
                feedback.append("Đầu gối đang vượt quá mũi chân!")
                is_correct = False
            else:
                # --- Check lỗi 2: Knee Angle (Góc đầu gối quá gập hoặc quá duỗi) ---
                # Tính góc gối Trái
                L_angle = self.calculate_angle(landmarks[23], landmarks[25], landmarks[27])
                # Tính góc gối Phải
                R_angle = self.calculate_angle(landmarks[24], landmarks[26], landmarks[28])

                # Nếu cả 2 chân đều nằm ngoài khoảng 60-125 độ
                if not (self.KNEE_ANGLE_THRESHOLD[0] <= L_angle <= self.KNEE_ANGLE_THRESHOLD[1]) and \
                   not (self.KNEE_ANGLE_THRESHOLD[0] <= R_angle <= self.KNEE_ANGLE_THRESHOLD[1]):
                    feedback.append("Hạ gối vuông góc 90 độ nhé!")
                    is_correct = False

        # 5. Đóng gói kết quả gửi về Mobile
        correction_text = " - ".join(feedback) if not is_correct else "Form lunge tốt!"

        return {
            "counter": self.counter,
            "score": round(score * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text
        }