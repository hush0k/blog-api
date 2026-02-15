import logging
from typing import Any

from django.contrib.auth.password_validation import validate_password as django_validate_password
from rest_framework import serializers

from apps.users.models import User

logger = logging.getLogger("users")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "password", "password2", "avatar")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password2"]:
            logger.warning("Registration serializer rejected request: passwords mismatch")
            raise serializers.ValidationError("Passwords do not match.")
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
