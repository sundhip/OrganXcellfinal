"""organs/urls.py"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganViewSet, RecipientRequestViewSet, OrganMatchViewSet

router = DefaultRouter()
router.register(r'organs',   OrganViewSet,           basename='organ')
router.register(r'requests', RecipientRequestViewSet, basename='recipient-request')
router.register(r'matches',  OrganMatchViewSet,       basename='organ-match')

urlpatterns = [path('', include(router.urls))]
