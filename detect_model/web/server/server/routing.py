from django.urls import path
from detection.consumers import PoseConsumer

websocket_urlpatterns = [
    # Backwards-compatible default (bicep curl)
    path('ws/pose/', PoseConsumer.as_asgi()),
    # Per-exercise endpoint: ws/pose/bicep/, ws/pose/squat/
    path('ws/pose/<str:exercise>/', PoseConsumer.as_asgi()),
]