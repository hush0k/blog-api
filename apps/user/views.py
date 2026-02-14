import logging

from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import User
from apps.user.serializers import UserCreateSerializer, UserSerializer


logger = logging.getLogger("users")

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        ip = request.META.get("REMOTE_ADDR")

        logger.info(
            "Registration attempt email=%s ip=%s",
            email, ip
        )

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            logger.warning(
                "Registration validation failed email=%s ip=%s",
                email, ip
            )
            logger.exception("Registration validation exception email=%s", email)
            raise


        try:
            user = serializer.save()
        except Exception:
            logger.exception(
                "Registration failed while saving data in DB email=%s",
                email
            )
            raise

        logger.info(
            "User successfully create an account id=%s, email=%s",
            user.id,
            user.email
        )

        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.action in ["list", "retrieve", "update", "partial_update", "destroy"]:
            raise MethodNotAllowed(self.action)
        return super().get_permissions()