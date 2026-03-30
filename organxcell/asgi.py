"""organxcell/asgi.py — ASGI with WebSocket support for live tracking"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import transport.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'organxcell.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(transport.routing.websocket_urlpatterns)
    ),
})
