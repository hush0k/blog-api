import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, extend_schema_view

from apps.core.ratelimit import ratelimit_or_429

logger = logging.getLogger("users")

@extend_schema_view(
    post=extend_schema(
        tags=["Auth"],
        summary="Obtain JWT token pair",
        description="Authenticates user by email and password. Returns access and refresh tokens. Rate limited to 10 requests per minute per IP.",
        responses={
            200: OpenApiResponse(description="Token pair returned"),
            400: OpenApiResponse(description="Invalid credentials"),
            429: OpenApiResponse(description="Rate limit exceeded"),
        },
        examples=[
            OpenApiExample("Request", value={"email": "user@example.com", "password": "StrongPass123!"}, request_only=True),
            OpenApiExample("Response", value={"access": "eyJ...", "refresh": "eyJ..."}, response_only=True, status_codes=["200"]),
        ],
    )
)
class TokenObtainPairRateLimitedView(TokenObtainPairView):
    @ratelimit_or_429(key="ip", rate="10/m", method=("POST",), group="auth_token")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        email = request.data.get("email")
        logger.info(
            "Login attempt email=%s ip=%s", email, request.META.get("REMOTE_ADDR")
        )
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info("Login success email=%s", email)
        else:
            logger.warning(
                "Login failed email=%s status=%s", email, response.status_code
            )
        return response
