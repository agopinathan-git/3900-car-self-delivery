
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.contrib.auth import views as auth_views
from carhub import views as carhub_views

urlpatterns = [
    # Home page
    path('', carhub_views.home, name='home'),

    # Admin panel
    path('admin/', admin.site.urls),

    # Carhub app
    path('carhub/', include('carhub.urls')),

    # User registration
    path('register/', include('register.urls')),

    # Auth (login, logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),

    # Password reset routes
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Static/Media files for dev
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
