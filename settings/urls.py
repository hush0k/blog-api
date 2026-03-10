from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.token_views import TokenObtainPairRateLimitedView

TokenRefreshDocumented = extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Refresh JWT access token",
        description="Takes a refresh token and returns a new access token.",
        responses={
            200: OpenApiResponse(description="New access token returned"),
            401: OpenApiResponse(description="Invalid or expired refresh token"),
        },
        examples=[
            OpenApiExample(
                "Request",
                value={"refresh": "eyJ..."},
                request_only=True,
            ),
            OpenApiExample(
                "Response",
                value={"access": "eyJ..."},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
)(TokenRefreshView)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.blog.urls")),
    path(
        "api/auth/token/",
        TokenObtainPairRateLimitedView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/auth/token/refresh/", TokenRefreshDocumented.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
