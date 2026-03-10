import logging
from typing import Any
import zoneinfo

from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.users.models import User

logger = logging.getLogger("users")

SUPPORTED_LANGUAGES = ["en", "ru", "kk"]

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "avatar",
        )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password2"]:
            logger.warning(
                "Registration serializer rejected request: passwords mismatch"
            )
            raise serializers.ValidationError(_("Passwords do not match."))
        django_validate_password(attrs["password"])
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        logger.info("Registration serializer created user_id=%s", user.id)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "avatar")


class UserLanguageSerializer(serializers.Serializer):
    language = serializers.CharField()

    @staticmethod
    def validate_language(value):
        if value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                _(f"Language not supported.")
            )
        return value


class UserTimezoneSerializer(serializers.Serializer):
    timezone = serializers.CharField()

    @staticmethod
    def validate_timezone(value):
        if value not in zoneinfo.available_timezones():
            raise serializers.ValidationError(
                _(f"Invalid timezone. Use valid IANA timezone")
            )
        return value




