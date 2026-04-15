import mediapipe as mp
import cv2
from django.conf import settings

# Import đúng các Engine mới (đã đổi tên file thành dấu _)
from .plank_engine import PlankCoachEngine
from .bicep_engine import BicepCoachEngine
from .squat_engine import SquatCoachEngine
from .lunge_engine import LungeCoachEngine
from .utils import rescale_frame

# Drawing helpers
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

EXERCISE_DETECTIONS = None

def load_machine_learning_models():
    """Load all machine learning models"""
    global EXERCISE_DETECTIONS

    if EXERCISE_DETECTIONS is not None:
        return

    print("Loading ML models for Video Processing...")
    EXERCISE_DETECTIONS = {
        "plank": PlankCoachEngine(),
        "bicep_curl": BicepCoachEngine(),
        "squat": SquatCoachEngine(),
        "lunge": LungeCoachEngine(),
    }

def exercise_detection(
    video_file_path: str,
    video_name_to_save: str,
    exercise_type: str,
    rescale_percent: float = 40,
) -> tuple:
    """Xử lý video upload offline dựa trên Engine mới"""
    
    # Đảm bảo model đã được load
    load_machine_learning_models()
    
    detector = EXERCISE_DETECTIONS.get(exercise_type)
    if not detector:
        raise Exception(f"Not supported exercise: {exercise_type}")

    cap = cv2.VideoCapture(video_file_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * rescale_percent / 100)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * rescale_percent / 100)
    size = (width, height)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    saved_path = f"{settings.MEDIA_ROOT}/{video_name_to_save}"
    out = cv2.VideoWriter(saved_path, fourcc, fps, size)

    print(f"PROCESSING VIDEO: {exercise_type}...")
    
    # Dùng list để chứa các feedback/error frames nếu cần (tương thích với logic cũ của views.py)
    results_metadata = []

    with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
        while cap.isOpened():
            ret, image = cap.read()
            if not ret:
                break

            image = rescale_frame(image, rescale_percent)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                # Gọi Engine mới xử lý từng frame
                analysis = detector.process_frame(results.pose_landmarks.landmark)
                
                # Vẽ landmarks lên video để user xem lại
                mp_drawing.draw_landmarks(
                    image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(244, 117, 66), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=1)
                )
                
                # Nếu có lỗi (is_correct = False), lưu lại text để hiển thị
                if not analysis["is_correct"]:
                    cv2.putText(image, analysis["correction"], (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            out.write(image)

    cap.release()
    out.release()
    print(f"PROCESSED. Save path: {saved_path}")

    # Trả về kết quả khớp với mong đợi của views.py
    # Trả về (results_list, counter)
    return results_metadata, detector.counter