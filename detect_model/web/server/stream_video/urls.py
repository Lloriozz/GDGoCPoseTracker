from django.urls import path
from . import views

urlpatterns = [
    path("stream", views.stream_video, name="stream"),
    path("upload", views.upload_video, name="upload"),
    
    path("analyze/", views.analyze_pose, name="analyze_pose"),
]