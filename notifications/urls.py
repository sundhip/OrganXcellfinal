"""notifications/urls.py"""
from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


class SOSView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        from .tasks import send_sos_alert
        organ_type = request.data.get('organ_type', 'unknown')
        user_id = request.data.get('user_id')
        send_sos_alert.delay(organ_type, user_id)
        return Response({'status': 'SOS alert sent', 'organ_type': organ_type})


class NotificationsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({'notifications': [], 'unread_count': 0})


urlpatterns = [
    path('sos/', SOSView.as_view(), name='sos'),
    path('', NotificationsListView.as_view(), name='notifications'),
]
