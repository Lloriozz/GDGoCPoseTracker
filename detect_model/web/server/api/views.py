from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
import logging
import traceback

from detection.live import analyze_live_frame, close_live_session

logger = logging.getLogger(__name__)

@api_view(["GET"])
def root(request):
    return Response(
        {
            "service": "PoseTracker API",
            "status": "ok",
            "time": datetime.now(),
            "endpoints": {
                "health": "/api/",
                "analyze_pose": "/api/pose/analyze/?type=squat",
                "close_pose_session": "/api/pose/close/",
                "upload_video": "/api/video/upload?type=squat",
            },
        }
    )


@api_view(["GET"])
def api(request):
    return Response(
        {
            "service": "PoseTracker API",
            "status": "ok",
            "time": datetime.now(),
        }
    )


@api_view(["POST"])
def analyze_pose_frame(request):
    exercise_type = request.query_params.get("type")
    session_id = request.query_params.get("session_id")
    frame = request.data.get("frame")

    if not exercise_type:
        return Response(
            {"error": "Missing exercise type."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not frame:
        return Response(
            {"error": "Missing frame payload."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = analyze_live_frame(
            exercise_type=exercise_type,
            frame_base64=frame,
            session_id=session_id,
        )
        return Response(payload)
    except ValueError as error:
        logger.warning(
            "Invalid live pose request exercise_type=%s session_id=%s error=%s",
            exercise_type,
            session_id,
            error,
        )
        return Response(
            {"error": str(error)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as error:
        trace = traceback.format_exc()
        logger.exception(
            "Live pose analyze failed exercise_type=%s session_id=%s",
            exercise_type,
            session_id,
        )
        return Response(
            {
                "error": str(error),
                "exercise_type": exercise_type,
                "session_id": session_id,
                "traceback": trace,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def close_pose_session(request):
    session_id = request.query_params.get("session_id") or request.data.get("session_id")
    if not session_id:
        return Response(
            {"error": "Missing session id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    close_live_session(session_id)
    return Response({"closed": True, "session_id": session_id})
