"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from pages import views as pages_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("hunting/", include("hunting.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    # Override the built-in logout so it lands on the farewell page.
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="logged_out"),
        name="logout",
    ),
    path("logged-out/", pages_views.logged_out_view, name="logged_out"),
    path("accounts/signup/", pages_views.signup_view, name="signup"),
]

# Friendly page when django-ratelimit blocks a user (default would be 403).
handler429 = "pages.views.ratelimited_view"

# Serve user-uploaded media in development only.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
