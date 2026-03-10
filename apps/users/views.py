import logging
from typing import Any

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.ratelimit import ratelimit_or_429
from apps.users.serializers import UserCreateSerializer, UserSerializer, UserLanguageSerializer, UserTimezoneSerializer

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


class UserMeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, url_path="language", methods=["patch"])
    def language(self, request):
        serializer = UserLanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.language = serializer.validated_data["language"]
        request.user.save(update_fields=["language"])
        return Response({"language": request.user.language})


    @action(detail=False, methods=["patch"], url_path="timezone")
    def timezone(self, request):
        serializer = UserTimezoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.timezone = serializer.validated_data["timezone"]
        request.user.save(update_fields=["timezone"])
        return Response({"timezone": request.user.timezone})
