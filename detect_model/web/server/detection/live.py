import base64
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

# 1. Import đúng tên file và tên Class Engine mới
from .bicep_engine import BicepCoachEngine
from .lunge_engine import LungeCoachEngine
from .plank_engine import PlankCoachEngine
from .squat_engine import SquatCoachEngine

mp_pose = mp.solutions.pose
logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 600

@dataclass
class LiveSession:
    detector: object
    pose: object
    frame_index: int
    updated_at: float

def _create_detector(exercise_type: str):
    """Khởi tạo Engine mới dựa trên loại bài tập"""
    if exercise_type == "bicep_curl":
        return BicepCoachEngine()
    if exercise_type == "squat":
        return SquatCoachEngine()
    if exercise_type == "lunge":
        return LungeCoachEngine()
    if exercise_type == "plank":
        return PlankCoachEngine()
    raise ValueError(f"Unsupported exercise type: {exercise_type}")

LIVE_SESSIONS = {}

def _cleanup_expired_sessions():
    now = time.time()
    expired_keys = [sid for sid, s in LIVE_SESSIONS.items() if now - s.updated_at > SESSION_TTL_SECONDS]
    for sid in expired_keys:
        session = LIVE_SESSIONS.pop(sid, None)
        if session: session.pose.close()

def get_or_create_live_session(exercise_type: str, session_id: Optional[str] = None):
    _cleanup_expired_sessions()
    session_id = session_id or str(uuid.uuid4())
    existing_session = LIVE_SESSIONS.get(session_id)

    if existing_session:
        existing_session.updated_at = time.time()
        return session_id, existing_session

    detector = _create_detector(exercise_type)
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=1)
    session = LiveSession(detector=detector, pose=pose, frame_index=0, updated_at=time.time())
    LIVE_SESSIONS[session_id] = session
    return session_id, session

def decode_base64_frame(frame_base64: str):
    if not frame_base64: raise ValueError("Frame payload is empty.")
    if "," in frame_base64: frame_base64 = frame_base64.split(",", 1)[1]
    image_bytes = base64.b64decode(frame_base64)
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return frame

def analyze_live_frame(exercise_type: str, frame_base64: str, session_id: Optional[str] = None):
    """
    Hàm xử lý chính: Chạy MediaPipe và ném landmarks vào Engine mới
    """
    session_id, session = get_or_create_live_session(exercise_type, session_id)
    session.frame_index += 1
    session.updated_at = time.time()

    # 1. Decode ảnh từ App gửi lên
    frame = decode_base64_frame(frame_base64)
    if frame is None: return {"type": "error", "message": "Decode failed"}

    # 2. Chạy MediaPipe lấy 33 điểm
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = session.pose.process(rgb_frame)

    if not results.pose_landmarks:
        return {
            "session_id": session_id,
            "type": "no_detection",
            "correction": "Vui lòng đứng rõ vào khung hình!",
            "score": 0, "rep_count": 0, "landmarks": []
        }

    raw_landmarks = results.pose_landmarks.landmark
    
    # 3. Gọi hàm process_frame của Engine (Tất cả Engine mới đều dùng chung hàm này)
    # Trả về kết quả là dict chứa counter, score, is_correct, correction
    analysis = session.detector.process_frame(raw_landmarks)

    # 4. Trả kết quả về cho API (Views.py)
    return {
        "session_id": session_id,
        "type": "prediction",
        "score": analysis.get("score", 0),
        "rep_count": analysis.get("counter", 0),
        "is_correct": analysis.get("is_correct", True),
        "correction": analysis.get("correction", "Form tốt!"),
        "landmarks": [
            {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} 
            for lm in raw_landmarks
        ]
    }

def close_live_session(session_id: str):
    session = LIVE_SESSIONS.pop(session_id, None)
    if session: session.pose.close()