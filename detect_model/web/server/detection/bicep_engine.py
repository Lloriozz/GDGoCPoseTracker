from pathlib import Path
import math
import joblib
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / "static" / "model"

# Tối ưu 1: Mang class Point ra ngoài cùng để tránh Memory Leak
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class BicepCoachEngine:
    IMPORTANT_LMS = [0, 11, 12, 14, 13, 16, 15, 23, 24] 
    
    POSTURE_ERROR_THRESHOLD = 0.80
    STAGE_UP_THRESHOLD = 100
    STAGE_DOWN_THRESHOLD = 120
    PEAK_CONTRACTION_THRESHOLD = 60
    LOOSE_UPPER_ARM_ANGLE_THRESHOLD = 40
    VIS_THRESH = 0.55

    def __init__(self):
        model_path = MODEL_DIR / "bicep_curl_model.pkl" 
        scaler_path = MODEL_DIR / "bicep_curl_input_scaler.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Thiếu file model Bicep tại {model_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Thiếu file scaler Bicep tại {scaler_path}")

        all_models = joblib.load(model_path)
        self.model = all_models["KNN"] if isinstance(all_models, dict) else all_models
        self.scaler = joblib.load(scaler_path)
        
        self.arms = {
            "Trái": {"stage": "down", "counter": 0, "peak": 1000},
            "Phải": {"stage": "down", "counter": 0, "peak": 1000}
        }
        self.stand_posture = "C"

    def _calc_angle(self, p1, p2, p3):
        ang = math.degrees(math.atan2(p3.y - p2.y, p3.x - p2.x) - math.atan2(p1.y - p2.y, p1.x - p2.x))
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def process_frame(self, landmarks):
        L_sh, L_el, L_wr = landmarks[11], landmarks[13], landmarks[15]
        R_sh, R_el, R_wr = landmarks[12], landmarks[14], landmarks[16]
        total_reps = self.arms["Trái"]["counter"] + self.arms["Phải"]["counter"]

        # GATEKEEPER 1: VISIBILITY
        avg_vis = sum([L_sh.visibility, L_el.visibility, L_wr.visibility, R_sh.visibility, R_el.visibility, R_wr.visibility]) / 6.0
        if avg_vis < self.VIS_THRESH:
            return {
                "counter": total_reps,
                "score": 0,
                "is_correct": False,
                "correction": "Vui lòng đứng trọn vẹn vào khung hình!"
            }

        # GATEKEEPER 2: IDLE STATE
        l_angle = self._calc_angle(L_sh, L_el, L_wr)
        r_angle = self._calc_angle(R_sh, R_el, R_wr)

        if l_angle > 150 and r_angle > 150:
            return {
                "counter": total_reps,
                "score": 100,
                "is_correct": True,
                "correction": "Sẵn sàng? Hãy gập tạ lên nào!"
            }

        # Tối ưu 2: List Comprehension siêu tốc 
        row = [val for idx in self.IMPORTANT_LMS for val in (
            landmarks[idx].x, landmarks[idx].y, landmarks[idx].z, landmarks[idx].visibility
        )]

        # Tối ưu 3: Bỏ .reshape(1, -1), dùng np.array 2 chiều luôn
        X_scaled = self.scaler.transform(np.array([row], dtype=float))
        
        try:
            pred_class = self.model.predict(X_scaled)[0]
            prob = float(np.max(self.model.predict_proba(X_scaled)))
        except Exception:
            return {"counter": total_reps, "score": 0, "is_correct": False, "correction": "Đang định vị tư thế...", "left_angle": round(l_angle), "right_angle": round(r_angle)}

        if prob >= self.POSTURE_ERROR_THRESHOLD:
            self.stand_posture = pred_class

        feedback = []
        is_correct = True

        if self.stand_posture == "L":
            feedback.append("Đừng ngả người ra sau!")
            is_correct = False

        # Tối ưu 4: Hàm analyze_arm gọn gàng, Point đã được mang ra ngoài
        def analyze_arm(sh, el, wr, curl_angle, side_name):
            arm_err = False
            state = self.arms[side_name]

            if curl_angle > self.STAGE_DOWN_THRESHOLD:
                if state["stage"] == "up":
                    if state["peak"] != 1000 and state["peak"] > self.PEAK_CONTRACTION_THRESHOLD:
                        feedback.append(f"Gập tay {side_name} cao hơn chút nữa!")
                        arm_err = True
                    state["peak"] = 1000 
                state["stage"] = "down"
                
            elif curl_angle < self.STAGE_UP_THRESHOLD and state["stage"] == "down":
                state["stage"] = "up"
                state["counter"] += 1

            if state["stage"] == "up" and curl_angle < state["peak"]:
                state["peak"] = curl_angle

            if self.stand_posture != "L": 
                proj = Point(sh.x, 1.0) 
                upper_arm_angle = self._calc_angle(el, sh, proj)
                
                if upper_arm_angle > self.LOOSE_UPPER_ARM_ANGLE_THRESHOLD:
                    feedback.append(f"Khép cùi chỏ {side_name} sát thân người!")
                    arm_err = True

            return arm_err

        l_err = analyze_arm(L_sh, L_el, L_wr, l_angle, "Trái")
        r_err = analyze_arm(R_sh, R_el, R_wr, r_angle, "Phải")

        if l_err or r_err:
            is_correct = False

        total_reps = self.arms["Trái"]["counter"] + self.arms["Phải"]["counter"]
        correction_text = " - ".join(feedback) if feedback else "Form rất nét, tiếp tục!"

        return {
            "counter": total_reps,
            "score": round(prob * 100, 1),
            "is_correct": is_correct,
            "correction": correction_text,
            "left_angle": round(l_angle), 
            "right_angle": round(r_angle)
        }