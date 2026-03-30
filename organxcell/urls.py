"""organxcell/urls.py — Master routing + serves frontend"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('admin/', admin.site.urls),
    path('api/accounts/',      include('accounts.urls')),
    path('api/organs/',        include('organs.urls')),
    path('api/consent/',       include('consent.urls')),
    path('api/transport/',     include('transport.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/ai/',            include('ai_engine.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
