from django.urls import path
from .import views
from django.urls import include, re_path, path
from django.conf import settings
from django.conf.urls.static import static
from site_accounts import views as account_views

urlpatterns = [
    # /noise urls
    path('', views.index, name='index'),
    path('login/<slug:provider>/', account_views.noise_login, name='noise-login'),
    path('auth/callback/', account_views.noise_auth_callback, name='noise-auth-callback'),
    path('logout/', account_views.noise_logout, name='noise-logout'),
    path('tetris/scores/', views.tetris_scores, name='noise-tetris-scores'),
    path('add', views.add, name='noise-add'),
    path('<int:noise_id>/edit/', views.edit, name='noise-edit'),
    path('<int:noise_id>/delete/', views.delete, name='noise-delete'),
    path('<int:noise_id>/admin-thumbnail/', views.admin_thumbnail, name='noise-admin-thumbnail'),
    path('<int:noise_id>/archive-preview/', views.archive_preview, name='noise-archive-preview'),
    path('<slug:noise_key>-<int:noise_id>/', views.detail, name='noise-detail'),
    # re_path(r'^humans\.txt$', TemplateView.as_view(template_name="humans.txt", content_type='text/plain')),
] 
