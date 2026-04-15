from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.api, name="api"),
    path("pose/analyze/", views.analyze_pose_frame, name="analyze-pose-frame"),
    path("pose/close/", views.close_pose_session, name="close-pose-session"),
    path("video/", include("stream_video.urls")),
]
