"""accounts/urls.py"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, MeView, HospitalViewSet

urlpatterns = [
    path('register/',  RegisterView.as_view(),   name='register'),
    path('login/',     LoginView.as_view(),       name='login'),
    path('me/',        MeView.as_view(),          name='me'),
    path('refresh/',   TokenRefreshView.as_view(),name='token-refresh'),
    path('hospitals/', HospitalViewSet.as_view(), name='hospitals'),
]
