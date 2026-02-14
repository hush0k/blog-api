from rest_framework import serializers

from apps.blog.models import Post, Category, Tag, Comment


class PostReadSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    category = serializers.StringRelatedField(read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "id", "author", "title", "slug", "body", "category", "tags", "status", "created_at", "updated_at"
        ]
        read_only_fields = fields


class PostWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )
    class Meta:
        model = Post
        fields = [
            "title", "slug", "body", "category_id", "tag_ids", "status"
        ]
    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value

class CommentReadSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    post = serializers.ReadOnlyField(source="post.title")

    class Meta:
        model = Comment
        fields = ["id", "author", "post", "body", "created_at"]
        read_only_fields = fields

class CommentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["body"]

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment body cannot be empty.")
        return value

