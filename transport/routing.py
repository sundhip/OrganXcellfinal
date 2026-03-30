"""transport/routing.py — WebSocket URL patterns"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/transport/(?P<transport_id>\d+)/$', consumers.TransportTrackingConsumer.as_asgi()),
    re_path(r'ws/transport/all/$', consumers.AllTransportsFeedConsumer.as_asgi()),
]
