"""transport/urls.py"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransportRequestViewSet, AllActiveTransportsView

router = DefaultRouter()
router.register(r'requests', TransportRequestViewSet, basename='transport')
router.register(r'active', AllActiveTransportsView, basename='active-transports')

urlpatterns = [path('', include(router.urls))]
