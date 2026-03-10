from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.token_views import TokenObtainPairRateLimitedView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.blog.urls")),
    path(
        "api/auth/token/",
        TokenObtainPairRateLimitedView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
