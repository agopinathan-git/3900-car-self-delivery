# carselfdelivery/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.contrib.auth import views as auth_views # For Django's auth views

# Only need to import carhub_views if home() is explicitly defined here
# and not within carhub.urls
from carhub import views as carhub_views


urlpatterns = [
    # Core Project URLs
    path('', carhub_views.home, name='home'),  # 🔹 Public landing page (or authenticated redirect)
    path('admin/', admin.site.urls),

    # App-Specific URL Inclusion
    # All URLs defined in carhub/urls.py will now be prefixed with '/carhub/'
    path('carhub/', include('carhub.urls')),

    # User Registration App (Assuming 'register' is a separate app)
    path('register/', include('register.urls')),

    # Django's Built-in Authentication URLs (login, logout, password change, etc.)
    # This single line includes many common auth URLs.
    path('accounts/', include('django.contrib.auth.urls')),

    # Explicit Password Reset Paths (often included by `accounts/` but explicit is fine)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Serving static/media files in development (REMEMBER TO REMOVE FOR PRODUCTION!)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
