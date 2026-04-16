import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import detection.routing # Khai báo đường dẫn routing cho WebSocket

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exercise_correction.settings")

# Bọc ứng dụng lại để xử lý song song cả HTTP và WebSocket
application = ProtocolTypeRouter({
    # Giao thức HTTP truyền thống (Dành cho các API cũ nếu có)
    "http": get_asgi_application(),
    
    # Giao thức WebSocket mới (Dành cho camera real-time)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            detection.routing.websocket_urlpatterns
        )
    ),
})