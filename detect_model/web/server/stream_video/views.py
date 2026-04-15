import os
import mimetypes
import json
import traceback
import base64
import cv2
import numpy as np
import mediapipe as mp
from datetime import datetime
from wsgiref.util import FileWrapper

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from django.http import StreamingHttpResponse, JsonResponse

# Import utils cũ
from detection.main import exercise_detection
from detection.utils import get_static_file_url

# Import 4 AI Coach Engines siêu tốc
from detection.squat_engine import SquatCoachEngine
from detection.lunge_engine import LungeCoachEngine
from detection.plank_engine import PlankCoachEngine
from detection.bicep_engine import BicepCoachEngine

# Khởi tạo Engine ở mức Global để Load file .pkl 1 lần duy nhất khi bật server
try:
    squat_engine = SquatCoachEngine()
    lunge_engine = LungeCoachEngine()
    plank_engine = PlankCoachEngine()
    bicep_engine = BicepCoachEngine()
    print("✅ Đã load thành công toàn bộ 4 AI Coach Models!")
except Exception as e:
    print(f"❌ Lỗi khi load Models: {e}")

# Khởi tạo MediaPipe 1 lần duy nhất trên Server để tối ưu tốc độ xử lý ảnh
mp_pose = mp.solutions.pose
pose_analyzer = mp_pose.Pose(
    static_image_mode=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    model_complexity=1
)


@api_view(["GET"])
def stream_video(request):
    video_name = request.GET.get("video_name")
    if not video_name:
        return JsonResponse(
            status=status.HTTP_400_BAD_REQUEST,
            data={"message": "File name not given"},
        )

    static_url = get_static_file_url(f"media/{video_name}")
    if not static_url:
        return JsonResponse(
            status=status.HTTP_404_NOT_FOUND,
            data={"message": "File not found"},
        )

    video_size = os.path.getsize(static_url)
    content_type, _ = mimetypes.guess_type(static_url)
    content_type = content_type or "application/octet-stream"

    chunk_size = video_size // 10

    response = StreamingHttpResponse(
        FileWrapper(open(static_url, "rb"), chunk_size), content_type=content_type
    )
    response["Content-Length"] = video_size
    response["Accept-Ranges"] = "bytes"
    return response


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_video(request):
    exercise_type = request.GET.get("type")
    if not exercise_type:
        return JsonResponse(
            status=status.HTTP_400_BAD_REQUEST,
            data={"message": "Exercise type has not given"},
        )

    try:
        if request.method == "POST":
            video = request.FILES["file"]
            now = int(datetime.now().strftime("%Y%m%d%H%M%S"))
            name_to_save = f"video_{now}.mp4"

            results, *other_data = exercise_detection(
                video_file_path=video.temporary_file_path(),
                video_name_to_save=name_to_save,
                exercise_type=exercise_type,
                rescale_percent=40,
            )

            host = request.build_absolute_uri("/")
            for index, error in enumerate(results):
                if error["frame"]:
                    results[index]["frame"] = host + f"static/images/{error['frame']}"

            response_data = {
                "type": exercise_type,
                "processed": True,
                "file_name": name_to_save,
                "details": results,
            }

            if exercise_type in ["squat", "lunge", "bicep_curl"]:
                response_data["counter"] = other_data[0]

            return JsonResponse(status=status.HTTP_200_OK, data=response_data)

    except Exception as e:
        print(f"Error Video Processing: {e}")
        return JsonResponse(
            status=status.HTTP_400_BAD_REQUEST,
            data={"error": f"Error: {e}"},
        )


@api_view(["POST"])
def analyze_pose(request):
    """
    Endpoint Real-time cho App React Native.
    Nhận Base64 từ Camera -> MediaPipe -> Phân tích lỗi -> Trả về JSON feedback.
    """
    exercise_type = request.GET.get("type", "squat")

    try:
        body = json.loads(request.body)
        b64_frame = body.get("frame")

        if not b64_frame:
            return JsonResponse({
                "type": "no_detection",
                "correction": "Không nhận được dữ liệu camera."
            })

        # 1. Giải mã Base64 thành hình ảnh OpenCV
        img_data = base64.b64decode(b64_frame)
        np_arr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # 2. Xử lý hình ảnh bằng MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_results = pose_analyzer.process(image_rgb)

        # Nếu không có dáng người trong khung hình
        if not mp_results.pose_landmarks:
            return JsonResponse({
                "type": "no_detection",
                "correction": "Vui lòng đứng rõ vào khung hình!"
            })

        # Trích xuất landmarks để đưa vào AI Engines
        landmarks = mp_results.pose_landmarks.landmark

        # 3. Phân luồng cho các AI Coach
        if exercise_type == 'squat':
            result = squat_engine.process_frame(landmarks)
        elif exercise_type == 'lunge':
            result = lunge_engine.process_frame(landmarks)
        elif exercise_type == 'plank':
            result = plank_engine.process_frame(landmarks)
        elif exercise_type == 'bicep_curl':
            result = bicep_engine.process_frame(landmarks)
        else:
            result = {
                "counter": 0,
                "score": 0,
                "is_correct": True,
                "correction": f"Chưa hỗ trợ bài {exercise_type}"
            }

        # 4. Trích xuất format điểm chuẩn để Mobile (pose-tracker.tsx) hiển thị Animated Dots
        formatted_landmarks = [
            {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} 
            for lm in landmarks
        ]

        # Trả về cho App
        return JsonResponse({
            "type": "prediction",
            "rep_count": result.get("counter", 0),
            "score": result.get("score", 0),
            "is_correct": result.get("is_correct", True),
            "correction": result.get("correction", "Form chuẩn!"),
            "landmarks": formatted_landmarks
        }, status=status.HTTP_200_OK)

    except FileNotFoundError as fnf_error:
        print(f"Lỗi thiếu Model: {fnf_error}")
        return JsonResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data={"error": f"Error loading model: {str(fnf_error)}"}
        )
    except Exception as e:
        print(f"Lỗi Server (Real-time): {e}")
        traceback.print_exc()
        return JsonResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data={"error": f"Server error: {str(e)}"}
        )