"""consent/urls.py"""
from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


class ConsentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({'consents': []})


urlpatterns = [
    path('', ConsentListView.as_view(), name='consent-list'),
]
