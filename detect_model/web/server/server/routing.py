from django.urls import path
from detection.consumers import PoseConsumer

websocket_urlpatterns = [
    path('ws/pose/', PoseConsumer.as_asgi()),
]