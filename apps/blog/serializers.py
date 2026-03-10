import logging
import zoneinfo
from babel.dates import format_datetime
from typing import Any

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.blog.models import Category, Comment, Post, Tag

logger = logging.getLogger("blog")


class PostReadSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.email")
    category = serializers.SerializerMethodField()
    tags = serializers.StringRelatedField(many=True, read_only=True)
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()


    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "tags",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_category(self, obj):
        if obj.category is None:
            return None
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if lang == "ru":
            return obj.category.name_ru or obj.category.name
        if lang == "kk":
            return obj.category.name_kk or obj.category.name
        return obj.category.name

    def _format_dt(self, dt):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            lang = request.LANGUAGE_CODE
            tz_name = request.user.timezone or "UTC"
        else:
            lang = "en"
            tz_name = "UTC"

        tz = zoneinfo.ZoneInfo(tz_name)
        dt_local = dt.astimezone(tz)

        return format_datetime(dt_local, format="long", locale=lang)

    def get_created_at(self, obj):
        return self._format_dt(obj.created_at)

    def get_updated_at(self, obj):
        return self._format_dt(obj.updated_at)


class PostWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags", queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Post
        fields = ["title", "slug", "body", "category_id", "tag_ids", "status"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            logger.warning("Post serializer rejected empty title")
            raise serializers.ValidationError(_("Title cannot be empty."))
        return value

    def create(self, validated_data: dict[str, Any]) -> Post:
        post = super().create(validated_data)
        logger.info("Post serializer created post_id=%s", post.id)
        return post

    def update(self, instance: Post, validated_data: dict[str, Any]) -> Post:
        post = super().update(instance, validated_data)
        logger.info("Post serializer updated post_id=%s", post.id)
        return post


class CommentReadSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.email")
    post = serializers.ReadOnlyField(source="post.slug")

    class Meta:
        model = Comment
        fields = ["id", "author", "post", "body", "created_at"]
        read_only_fields = fields


class CommentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["body"]

    def validate_body(self, value: str) -> str:
        if not value.strip():
            logger.warning(_("Comment serializer rejected empty body"))
            raise serializers.ValidationError(_("Comment body cannot be empty."))
        return value

    def create(self, validated_data: dict[str, Any]) -> Comment:
        comment = super().create(validated_data)
        logger.info("Comment serializer created comment_id=%s", comment.id)
        return comment


