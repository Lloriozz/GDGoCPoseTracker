import json
import base64
import cv2
import numpy as np
import mediapipe as mp
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .bicep_engine import BicepCoachEngine
from .squat_engine import SquatCoachEngine
from .lunge_engine import LungeCoachEngine
from .plank_engine import PlankCoachEngine

# Khởi tạo Mediapipe 1 lần
mp_pose = mp.solutions.pose

ENGINE_REGISTRY = {
    "bicep": BicepCoachEngine,
    "bicep_curl": BicepCoachEngine,
    "squat": SquatCoachEngine,
    "lunge": LungeCoachEngine,
    "plank": PlankCoachEngine,
}

class PoseConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        route_kwargs = self.scope.get("url_route", {}).get("kwargs", {})
        exercise = (route_kwargs.get("exercise") or "bicep").lower()

        if exercise not in ENGINE_REGISTRY:
            await self.accept()
            await self.send(text_data=json.dumps({
                "type": "error",
                "correction": f"Bài tập '{exercise}' không được hỗ trợ.",
            }))
            await self.close()
            return

        self.exercise = exercise
        await self.accept()
        try:
            self.engine = ENGINE_REGISTRY[exercise]()
        except Exception as e:
            await self.send(text_data=json.dumps({
                "type": "error",
                "correction": f"Không load được model '{exercise}': {e}",
            }))
            await self.close()
            return

        # Tối ưu 1: static_image_mode=False (Mặc định) giúp MediaPipe dùng tính năng Tracking siêu nhanh thay vì Detection lại từ đầu.
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    async def disconnect(self, close_code):
        pass

    # Tối ưu 2: Gộp việc chạy MediaPipe và Engine vào MỘT hàm đồng bộ duy nhất
    def _process_frame_sync(self, image):
        # Chạy MediaPipe
        results = self.pose.process(image)
        
        if not results.pose_landmarks:
            return None, None
            
        landmarks = results.pose_landmarks.landmark
        
        # Chạy phân tích AI / Toán học ngay trong cùng thread
        analysis = self.engine.process_frame(landmarks)
        
        # Trích xuất data
        landmarks_data = [{"x": lm.x, "y": lm.y, "visibility": lm.visibility} for lm in landmarks]
        
        return analysis, landmarks_data

    async def receive(self, text_data):
        data = json.loads(text_data)
        base64_frame = data.get('frame')

        if not base64_frame:
            return

        # Giải mã ảnh
        img_bytes = base64.b64decode(base64_frame)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Tối ưu 3: Resize ảnh nhỏ lại trước khi đưa vào MediaPipe (Giảm 50% thời gian xử lý)
        # MediaPipe đằng nào cũng tự thu nhỏ ảnh (xuống 256x256), nên thu nhỏ từ OpenCV sẽ nhanh hơn.
        image = cv2.resize(image, (320, 240), interpolation=cv2.INTER_AREA)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Gọi hàm gộp (Chỉ mất 1 lần context-switch thay vì 2 lần như code cũ)
        # thread_sensitive=False cho phép Django xài ThreadPool lớn hơn để không kẹt luồng chính
        result = await sync_to_async(self._process_frame_sync, thread_sensitive=False)(image)

        if result == (None, None):
            await self.send(text_data=json.dumps({
                "type": "no_detection",
                "correction": "Vui lòng đứng trọn vẹn vào khung hình!"
            }))
            return

        analysis, landmarks_data = result

        # Bắn kết quả về
        payload = {
            "type": "success",
            "exercise": self.exercise,
            "landmarks": landmarks_data,
            "counter": analysis["counter"],
            "score": analysis.get("score", 0), # Dùng .get() để tránh lỗi key error
            "is_correct": analysis["is_correct"],
            "correction": analysis["correction"],
        }
        
        for extra_key in ("stage", "feet", "knee", "left_angle", "right_angle"):
            if extra_key in analysis:
                payload[extra_key] = analysis[extra_key]

        await self.send(text_data=json.dumps(payload))