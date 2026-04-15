from pathlib import Path
import math
import joblib
import numpy as np

# Khai báo đường dẫn chuẩn
MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

class BicepCoachEngine:
    # Thứ tự index CHUẨN XÁC theo file train của ông
    IMPORTANT_LMS = [0, 11, 12, 14, 13, 16, 15, 23, 24] 
    
    POSTURE_ERROR_THRESHOLD = 0.95
    STAGE_UP_THRESHOLD = 100
    STAGE_DOWN_THRESHOLD = 120
    PEAK_CONTRACTION_THRESHOLD = 60
    LOOSE_UPPER_ARM_ANGLE_THRESHOLD = 40
    VIS_THRESH = 0.65

    def __init__(self):
        model_path = MODEL_DIR / "bicep_curl_model.pkl" 
        scaler_path = MODEL_DIR / "bicep_curl_input_scaler.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Thiếu file model Bicep tại {model_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Thiếu file scaler Bicep tại {scaler_path}")

        # Tách lấy model KNN từ cục dictionary của ông
        all_models = joblib.load(model_path)
        self.model = all_models["KNN"] if isinstance(all_models, dict) else all_models
        self.scaler = joblib.load(scaler_path)
        
        # Quản lý trạng thái 2 tay riêng biệt
        self.arms = {
            "Trái": {"stage": "down", "counter": 0, "peak": 1000},
            "Phải": {"stage": "down", "counter": 0, "peak": 1000}
        }
        self.stand_posture = "C"

    def _calc_angle(self, p1, p2, p3):
        ang = math.degrees(math.atan2(p3.y - p2.y, p3.x - p2.x) - math.atan2(p1.y - p2.y, p1.x - p2.x))
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def process_frame(self, landmarks):
        # 1. TRÍCH XUẤT ĐIỂM VÀ DỰ ĐOÁN LỖI NGẢ LƯNG BẰNG ML MODEL
        row = []
        for idx in self.IMPORTANT_LMS:
            lm = landmarks[idx]
            row.extend([lm.x, lm.y, lm.z, lm.visibility])

        X_scaled = self.scaler.transform(np.array(row, dtype=float).reshape(1, -1))
        pred_class = self.model.predict(X_scaled)[0]
        prob = float(np.max(self.model.predict_proba(X_scaled)))

        if prob >= self.POSTURE_ERROR_THRESHOLD:
            self.stand_posture = pred_class

        feedback = []
        is_correct = True

        if self.stand_posture == "L":
            feedback.append("Đừng ngả người ra sau!")
            is_correct = False

        # 2. PHÂN TÍCH CHUYỂN ĐỘNG 2 CÁNH TAY BẰNG TOÁN HỌC
        L_sh, L_el, L_wr = landmarks[11], landmarks[13], landmarks[15]
        R_sh, R_el, R_wr = landmarks[12], landmarks[14], landmarks[16]

        class Point: # Tạo class phụ để tính góc với mặt đất (trục Y)
            def __init__(self, x, y):
                self.x = x
                self.y = y

        def analyze_arm(sh, el, wr, side_name):
            # Lọc nhiễu: Nếu không thấy rõ tay thì bỏ qua
            if sh.visibility < self.VIS_THRESH or el.visibility < self.VIS_THRESH or wr.visibility < self.VIS_THRESH:
                return False

            arm_err = False
            state = self.arms[side_name]
            curl_angle = self._calc_angle(sh, el, wr)

            # Logic đếm Rep và kiểm tra Peak Contraction (Siết cơ)
            if curl_angle > self.STAGE_DOWN_THRESHOLD:
                if state["stage"] == "up":
                    # Kiểm tra xem lúc nãy kéo lên có đủ cao không
                    if state["peak"] != 1000 and state["peak"] > self.PEAK_CONTRACTION_THRESHOLD:
                        feedback.append(f"Gập tay {side_name} cao hơn chút nữa!")
                        arm_err = True
                    state["peak"] = 1000 # Reset peak cho rep mới
                state["stage"] = "down"
                
            elif curl_angle < self.STAGE_UP_THRESHOLD and state["stage"] == "down":
                state["stage"] = "up"
                state["counter"] += 1

            if state["stage"] == "up" and curl_angle < state["peak"]:
                state["peak"] = curl_angle

            # Logic kiểm tra Loose Upper Arm (Mở cùi chỏ)
            if self.stand_posture != "L": # Chỉ bắt lỗi cùi chỏ nếu lưng đang thẳng
                proj = Point(sh.x, 1.0) # Hình chiếu thẳng đứng
                upper_arm_angle = self._calc_angle(el, sh, proj)
                
                if upper_arm_angle > self.LOOSE_UPPER_ARM_ANGLE_THRESHOLD:
                    feedback.append(f"Khép cùi chỏ {side_name} sát thân người!")
                    arm_err = True

            return arm_err

        # Phân tích tay trái và tay phải
        l_err = analyze_arm(L_sh, L_el, L_wr, "Trái")
        r_err = analyze_arm(R_sh, R_el, R_wr, "Phải")

        if l_err or r_err:
            is_correct = False

        # 3. TỔNG HỢP KẾT QUẢ GỬI VỀ MOBILE
        total_reps = self.arms["Trái"]["counter"] + self.arms["Phải"]["counter"]
        correction_text = " - ".join(feedback) if feedback else "Form tay rất nét!"

        return {
            "counter": total_reps,
            "score": round(prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text
        }