from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from noise.api import NoiseViewSet
from .views import media

admin.site.site_header = 'Noise administration'
admin.site.site_title = 'Noise'
router = DefaultRouter()
router.register('noise', NoiseViewSet, basename='api-noise')
urlpatterns = [
    path('', RedirectView.as_view(url='/noise/', permanent=False)),
    path('noise/', include('noise.urls')),
    path('admin/', admin.site.urls),
    path('accounts/login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('api/', include(router.urls)),
]
if not getattr(settings, 'AWS_STORAGE_BUCKET_NAME', ''):
    urlpatterns.append(path('media/<path:filename>', media, name='noise-media'))
