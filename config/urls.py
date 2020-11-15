from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import (
    include,
    path,
)
from django.views import defaults as default_views
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView

from sprints.users.api import GoogleLogin

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", lambda request: redirect('/swagger')),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # Dashboard
    path("dashboard/", include("sprints.dashboard.urls", namespace="dashboard")),
    # Sustainability Dashboard
    path("sustainability/", include("sprints.sustainability.urls", namespace="sustainability")),
]

# Provide an option to disable standard (not social auth) login/registration page.
if not getattr(settings, "ACCOUNT_ALLOW_LOGIN", True):
    urlpatterns += [
        path(
            "accounts/login/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path(
            "accounts/signup/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
    ]

urlpatterns += [
    path("accounts/", include("allauth.urls")),
    url(r'^rest-auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^rest-auth/google/$', GoogleLogin.as_view(), name='google_login'),
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # Your stuff: custom urls includes go here
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
