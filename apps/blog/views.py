import logging
from typing import Any

from django.core.cache import cache
from django.db.models import Q, QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from apps.blog.models import Comment, Post
from apps.blog.permissions import IsPostPublishedOrOwner
from apps.blog.redis_events import publish_comment_created
from apps.blog.serializers import CommentReadSerializer, CommentWriteSerializer, PostReadSerializer, PostWriteSerializer
from apps.common.ratelimit import ratelimit_or_429, user_or_ip

logger = logging.getLogger("blog")
LIST_CACHE_KEY_PREFIX = "post:list:published"
LIST_CACHE_TTL_SECONDS = 60


class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    queryset = Post.objects.select_related("author", "category").prefetch_related("tags")
    permission_classes = [IsAuthenticatedOrReadOnly, IsPostPublishedOrOwner]

    def get_queryset(self) -> QuerySet[Post]:
        base_queryset = super().get_queryset()
        user = self.request.user
        if self.action == "list":
            return base_queryset.filter(status=Post.Status.PUBLISHED)
        if self.action == "retrieve":
            if user.is_authenticated:
                return base_queryset.filter(Q(status=Post.Status.PUBLISHED) | Q(author=user))
            return base_queryset.filter(status=Post.Status.PUBLISHED)
        return base_queryset

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return PostReadSerializer
        return PostWriteSerializer

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        page_number = request.query_params.get("page", "1")
        cache_key = f"{LIST_CACHE_KEY_PREFIX}:page:{page_number}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Post list cache hit page=%s", page_number)
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PostReadSerializer(page, many=True)
            data = serializer.data
            cache.set(cache_key, data, LIST_CACHE_TTL_SECONDS)
            return self.get_paginated_response(data)

        serializer = PostReadSerializer(queryset, many=True)
        data = serializer.data
        cache.set(cache_key, data, LIST_CACHE_TTL_SECONDS)
        return Response(data)

    def _invalidate_posts_cache(self) -> None:
        try:
            cache.delete_pattern(f"{LIST_CACHE_KEY_PREFIX}:*")
        except Exception:
            logger.exception("Post list cache invalidation failed")

    @ratelimit_or_429(key=user_or_ip, rate="20/m", method=("POST",), group="post_create")
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info("Post create attempt user_id=%s", getattr(request.user, "id", None))
        try:
            response = super().create(request, *args, **kwargs)
        except Exception:
            logger.exception("Post create exception user_id=%s", getattr(request.user, "id", None))
            raise
        if response.status_code == status.HTTP_201_CREATED:
            self._invalidate_posts_cache()
            logger.info("Post create success user_id=%s", getattr(request.user, "id", None))
        else:
            logger.warning("Post create failed user_id=%s status=%s", getattr(request.user, "id", None), response.status_code)
        return response

    def perform_create(self, serializer: PostWriteSerializer) -> None:
        serializer.save(author=self.request.user)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info("Post update attempt user_id=%s slug=%s", getattr(request.user, "id", None), kwargs.get("slug"))
        try:
            response = super().partial_update(request, *args, **kwargs)
        except Exception:
            logger.exception("Post update exception user_id=%s slug=%s", getattr(request.user, "id", None), kwargs.get("slug"))
            raise
        if response.status_code == status.HTTP_200_OK:
            self._invalidate_posts_cache()
            logger.info("Post update success user_id=%s slug=%s", getattr(request.user, "id", None), kwargs.get("slug"))
        else:
            logger.warning(
                "Post update failed user_id=%s slug=%s status=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
                response.status_code,
            )
        return response

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info("Post delete attempt user_id=%s slug=%s", getattr(request.user, "id", None), kwargs.get("slug"))
        try:
            response = super().destroy(request, *args, **kwargs)
        except Exception:
            logger.exception("Post delete exception user_id=%s slug=%s", getattr(request.user, "id", None), kwargs.get("slug"))
            raise
        if response.status_code == status.HTTP_204_NO_CONTENT:
            self._invalidate_posts_cache()
            logger.info("Post delete success user_id=%s slug=%s", getattr(request.user, "id", None), kwargs.get("slug"))
        else:
            logger.warning(
                "Post delete failed user_id=%s slug=%s status=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
                response.status_code,
            )
        return response

    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticatedOrReadOnly], url_path="comments")
    def comments(self, request: Request, slug: str | None = None) -> Response:
        post = self.get_object()
        post_visible = post.status == Post.Status.PUBLISHED or post.author_id == getattr(request.user, "id", None)

        if request.method == "GET":
            if not post_visible:
                return Response(status=status.HTTP_404_NOT_FOUND)
            comments_queryset: QuerySet[Comment] = post.comments.select_related("author").order_by("-created_at")
            page = self.paginate_queryset(comments_queryset)
            if page is not None:
                serializer = CommentReadSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = CommentReadSerializer(comments_queryset, many=True)
            return Response(serializer.data)

        if not post_visible:
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info("Comment create attempt user_id=%s post_slug=%s", getattr(request.user, "id", None), post.slug)
        serializer = CommentWriteSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(author=request.user, post=post)
            publish_comment_created(comment)
        except Exception:
            logger.exception("Comment create exception user_id=%s post_slug=%s", getattr(request.user, "id", None), post.slug)
            raise
        logger.info("Comment create success comment_id=%s user_id=%s", comment.id, getattr(request.user, "id", None))
        return Response(CommentReadSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path=r"comments/(?P<comment_id>[^/.]+)",
    )
    def comment_detail(self, request: Request, slug: str | None = None, comment_id: str | None = None) -> Response:
        post = self.get_object()
        comment = get_object_or_404(post.comments.select_related("author"), pk=comment_id)
        if comment.author_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.method == "PATCH":
            logger.info("Comment update attempt comment_id=%s user_id=%s", comment.id, request.user.id)
            serializer = CommentWriteSerializer(comment, data=request.data, partial=True)
            try:
                serializer.is_valid(raise_exception=True)
                updated_comment = serializer.save()
            except Exception:
                logger.exception("Comment update exception comment_id=%s user_id=%s", comment.id, request.user.id)
                raise
            logger.info("Comment update success comment_id=%s user_id=%s", updated_comment.id, request.user.id)
            return Response(CommentReadSerializer(updated_comment).data, status=status.HTTP_200_OK)

        logger.info("Comment delete attempt comment_id=%s user_id=%s", comment.id, request.user.id)
        comment.delete()
        logger.info("Comment delete success comment_id=%s user_id=%s", comment.id, request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
