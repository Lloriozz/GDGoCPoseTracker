from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/pose/(?P<exercise_type>\w+)/$', consumers.PoseConsumer.as_asgi()),
]