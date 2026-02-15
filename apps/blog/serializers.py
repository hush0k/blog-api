import logging
from typing import Any

from rest_framework import serializers

from apps.blog.models import Category, Comment, Post, Tag

logger = logging.getLogger("blog")


class PostReadSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.email")
    category = serializers.StringRelatedField(read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ["id", "author", "title", "slug", "body", "category", "tags", "status", "created_at", "updated_at"]
        read_only_fields = fields


class PostWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=Category.objects.all(), required=False, allow_null=True)
    tag_ids = serializers.PrimaryKeyRelatedField(source="tags", queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Post
        fields = ["title", "slug", "body", "category_id", "tag_ids", "status"]

    def validate_title(self, value: str) -> str:
        if not value.strip():
            logger.warning("Post serializer rejected empty title")
            raise serializers.ValidationError("Title cannot be empty.")
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
            logger.warning("Comment serializer rejected empty body")
            raise serializers.ValidationError("Comment body cannot be empty.")
        return value

    def create(self, validated_data: dict[str, Any]) -> Comment:
        comment = super().create(validated_data)
        logger.info("Comment serializer created comment_id=%s", comment.id)
        return comment
