import logging
from typing import Any

from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.ratelimit import ratelimit_or_429
from apps.users.serializers import UserCreateSerializer, UserSerializer

logger = logging.getLogger("users")


class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @ratelimit_or_429(key="ip", rate="5/m", method=("POST",), group="auth_register")
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        email = request.data.get("email")
        logger.info(
            "Registration attempt email=%s ip=%s",
            email,
            request.META.get("REMOTE_ADDR"),
        )

        serializer = UserCreateSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except Exception:
            logger.exception("Registration failed email=%s", email)
            raise

        refresh = RefreshToken.for_user(user)
        logger.info("Registration success user_id=%s email=%s", user.id, user.email)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )
