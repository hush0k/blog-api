import logging
from typing import Any

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample, OpenApiResponse


from apps.core.ratelimit import ratelimit_or_429
from apps.users.serializers import UserCreateSerializer, UserSerializer, UserLanguageSerializer, UserTimezoneSerializer

logger = logging.getLogger("users")

def send_welcome_email(user):
    with translation.override(user.language or "en"):
        body = render_to_string(
            "emails/welcome.html",
            {"user": user}
        )
        send_mail(
            subject=str(translation.gettext("Welcome!")),
            message=body,
            from_email="noreply@blog.com",
            recipient_list=[user.email],
        )


class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Create a new user",
        description="Create a new user",
    )
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

        send_welcome_email(user)

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

    @extend_schema(
        tags=["Auth"],
        summary="Update info about language",
        description="Sets the authenticated user's preferred language. Must be one of: en, ru, kk.",
        request=UserLanguageSerializer,
        responses={
            200: OpenApiResponse(description="Language update"),
            400: OpenApiResponse(description="Unsupported update"),
            401: OpenApiResponse(description="Authentication needed"),
        },
        examples=[
            OpenApiExample("Request", value={"language": "ru"}, request_only=True),
            OpenApiExample("Response", value={"language": "ru"}, response_only=True, status_codes=["200"]),
        ],
    )
    @action(detail=False, url_path="language", methods=["patch"])
    def language(self, request):
        serializer = UserLanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.language = serializer.validated_data["language"]
        request.user.save(update_fields=["language"])
        return Response({"language": request.user.language})


    @extend_schema(
        tags=["Auth"],
        summary="Update info about timezone",
        description="Update info about timezone",
        request=UserTimezoneSerializer,
        responses={
            200: OpenApiResponse(description="Timezone update"),
            400: OpenApiResponse(description="Unsupported update"),
            401: OpenApiResponse(description="Authentication needed"),
        },
        examples=[
            OpenApiExample("Request", value={"timezone": "Asia/Almaty"}, request_only=True),
            OpenApiExample("Response", value={"timezone": "Asia/Almaty"}, response_only=True, status_codes=["200"]),

        ]
    )
    @action(detail=False, methods=["patch"], url_path="timezone")
    def timezone(self, request):
        serializer = UserTimezoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.timezone = serializer.validated_data["timezone"]
        request.user.save(update_fields=["timezone"])
        return Response({"timezone": request.user.timezone})
