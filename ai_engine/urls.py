"""ai_engine/urls.py"""
from django.urls import path
from .views import (
    MatchExplainerView, SurvivalPredictorView,
    WaitingListReorderView, ChatbotView,
    RouteOptimizerView, AllocationAdvisorView,
)

urlpatterns = [
    path('explain-match/',    MatchExplainerView.as_view(),     name='ai-explain-match'),
    path('predict-survival/', SurvivalPredictorView.as_view(),  name='ai-predict-survival'),
    path('reorder-waitlist/', WaitingListReorderView.as_view(), name='ai-reorder-waitlist'),
    path('chat/',             ChatbotView.as_view(),            name='ai-chatbot'),
    path('optimize-route/',   RouteOptimizerView.as_view(),     name='ai-optimize-route'),
    path('allocate/',         AllocationAdvisorView.as_view(),  name='ai-allocate'),
]
