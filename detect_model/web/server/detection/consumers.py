import json
import base64
import cv2
import numpy as np
import mediapipe as mp
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .bicep_engine import BicepCoachEngine

# Khởi tạo Mediapipe & Engine 1 lần duy nhất cho mỗi kết nối để tối ưu tốc độ
mp_pose = mp.solutions.pose

class PoseConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.engine = BicepCoachEngine()
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        base64_frame = data.get('frame')

        if not base64_frame:
            return

        # 1. Giải mã Base64 thành ảnh OpenCV siêu tốc
        img_bytes = base64.b64decode(base64_frame)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 2. Chạy Mediapipe (Chạy trong thread pool để không block Websocket)
        results = await sync_to_async(self.pose.process)(image)

        # 3. Phân tích logic
        if not results.pose_landmarks:
            await self.send(text_data=json.dumps({
                "type": "no_detection",
                "correction": "Vui lòng đứng trọn vẹn vào khung hình!"
            }))
            return

        landmarks = results.pose_landmarks.landmark
        
        # Gọi Engine (Chạy trong thread pool)
        analysis = await sync_to_async(self.engine.process_frame)(landmarks)

        # Trích xuất tọa độ gửi về vẽ khung xương
        landmarks_data = [{"x": lm.x, "y": lm.y, "visibility": lm.visibility} for lm in landmarks]

        # 4. Bắn kết quả về ngay lập tức
        await self.send(text_data=json.dumps({
            "type": "success",
            "landmarks": landmarks_data,
            "counter": analysis["counter"],
            "score": analysis["score"],
            "is_correct": analysis["is_correct"],
            "correction": analysis["correction"]
        }))