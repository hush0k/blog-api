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
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, extend_schema_view

from apps.blog.models import Comment, Post
from apps.blog.permissions import IsPostPublishedOrOwner
from apps.blog.redis_events import publish_comment_created
from apps.blog.serializers import (
    CommentReadSerializer,
    CommentWriteSerializer,
    PostReadSerializer,
    PostWriteSerializer,
)
from apps.core.ratelimit import ratelimit_or_429, user_or_ip

logger = logging.getLogger("blog")
LIST_CACHE_KEY_PREFIX = "post:list:published"
LIST_CACHE_TTL_SECONDS = 60

@extend_schema_view(
    retrieve=extend_schema(
        tags=["Posts"],
        summary="Get post details",
        description="Returns a single post by slug. Authenticated users can also see their own draft posts. Dates formatted by user locale and timezone.",
        responses={
            200: PostReadSerializer,
            404: OpenApiResponse(description="Post not found"),
        },
    ),
    create=extend_schema(
        tags=["Posts"],
        summary="Create a post",
        description="Creates a new post. Authentication required. Invalidates the posts list cache for all languages. Rate limited to 20 requests per minute.",
        request=PostWriteSerializer,
        responses={
            201: PostWriteSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            429: OpenApiResponse(description="Rate limit exceeded"),
        },
        examples=[
            OpenApiExample("Request", value={"title": "My post", "slug": "my-post", "body": "Content", "status": "published"}, request_only=True),
            OpenApiExample("Response", value={"title": "My post", "slug": "my-post", "body": "Content", "status": "published"}, response_only=True, status_codes=["201"]),
        ],
    ),
    update=extend_schema(exclude=True),
)
class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    queryset = Post.objects.select_related("author", "category").prefetch_related(
        "tags"
    )
    permission_classes = [IsAuthenticatedOrReadOnly, IsPostPublishedOrOwner]

    def get_queryset(self) -> QuerySet[Post]:
        base_queryset = super().get_queryset()
        user = self.request.user
        if self.action == "list":
            return base_queryset.filter(status=Post.Status.PUBLISHED)
        if self.action == "retrieve":
            if user.is_authenticated:
                return base_queryset.filter(
                    Q(status=Post.Status.PUBLISHED) | Q(author=user)
                )
            return base_queryset.filter(status=Post.Status.PUBLISHED)
        return base_queryset

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return PostReadSerializer
        return PostWriteSerializer

    @extend_schema(
        tags=["Posts"],
        summary="List published posts",
        description="Returns paginated list of published posts. Dates are formatted by user locale and timezone. Response is cached in Redis per language. Anonymous users see UTC dates. Cache is invalidated when any post is created, updated or deleted.",
        responses={
            200: PostReadSerializer,
        },
        examples=[
            OpenApiExample(
                "Response",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "author": "user@example.com",
                            "title": "My first post",
                            "slug": "my-first-post",
                            "body": "Post content here",
                            "category": "Technology",
                            "tags": ["python", "django"],
                            "status": "published",
                            "created_at": "March 10, 2026, 2:30:00 PM UTC",
                            "updated_at": "March 10, 2026, 2:30:00 PM UTC",
                        }
                    ],
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        page_number = request.query_params.get("page", "1")
        lang = getattr(request, "LANGUAGE_CODE", "en")
        cache_key = f"{LIST_CACHE_KEY_PREFIX}:lang:{lang}:page:{page_number}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Post list cache hit page=%s", page_number)
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PostReadSerializer(page, many=True, context={"request": request})
            data = serializer.data
            cache.set(cache_key, data, LIST_CACHE_TTL_SECONDS)
            return self.get_paginated_response(data)

        serializer = PostReadSerializer(queryset, many=True, context={"request": request})
        data = serializer.data
        cache.set(cache_key, data, LIST_CACHE_TTL_SECONDS)
        return Response(data)

    def _invalidate_posts_cache(self) -> None:
        try:
            cache.delete_pattern(f"{LIST_CACHE_KEY_PREFIX}:*")
        except Exception:
            logger.exception("Post list cache invalidation failed")

    @ratelimit_or_429(
        key=user_or_ip, rate="20/m", method=("POST",), group="post_create"
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info("Post create attempt user_id=%s", getattr(request.user, "id", None))
        try:
            response = super().create(request, *args, **kwargs)
        except Exception:
            logger.exception(
                "Post create exception user_id=%s", getattr(request.user, "id", None)
            )
            raise
        if response.status_code == status.HTTP_201_CREATED:
            self._invalidate_posts_cache()
            logger.info(
                "Post create success user_id=%s", getattr(request.user, "id", None)
            )
        else:
            logger.warning(
                "Post create failed user_id=%s status=%s",
                getattr(request.user, "id", None),
                response.status_code,
            )
        return response


    def perform_create(self, serializer: PostWriteSerializer) -> None:
        serializer.save(author=self.request.user)

    @extend_schema(
        tags=["Posts"],
        summary="Update a post",
        description="Partially updates a post. Authentication required. Only the post author can update. Invalidates the posts list cache for all languages.",
        request=PostWriteSerializer,
        responses={
            200: PostWriteSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the post author"),
            404: OpenApiResponse(description="Post not found"),
        },
        examples=[
            OpenApiExample("Request", value={"title": "Updated title"}, request_only=True),
            OpenApiExample("Response", value={"title": "Updated title", "slug": "my-post"}, response_only=True, status_codes=["200"]),
        ],
    )
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info(
            "Post update attempt user_id=%s slug=%s",
            getattr(request.user, "id", None),
            kwargs.get("slug"),
        )
        try:
            response = super().partial_update(request, *args, **kwargs)
        except Exception:
            logger.exception(
                "Post update exception user_id=%s slug=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
            )
            raise
        if response.status_code == status.HTTP_200_OK:
            self._invalidate_posts_cache()
            logger.info(
                "Post update success user_id=%s slug=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
            )
        else:
            logger.warning(
                "Post update failed user_id=%s slug=%s status=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
                response.status_code,
            )
        return response

    @extend_schema(
        tags=["Posts"],
        summary="Delete a post",
        description="Deletes a post. Authentication required. Only the post author can delete. Invalidates the posts list cache for all languages.",
        responses={
            204: OpenApiResponse(description="Post deleted"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the post author"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info(
            "Post delete attempt user_id=%s slug=%s",
            getattr(request.user, "id", None),
            kwargs.get("slug"),
        )
        try:
            response = super().destroy(request, *args, **kwargs)
        except Exception:
            logger.exception(
                "Post delete exception user_id=%s slug=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
            )
            raise
        if response.status_code == status.HTTP_204_NO_CONTENT:
            self._invalidate_posts_cache()
            logger.info(
                "Post delete success user_id=%s slug=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
            )
        else:
            logger.warning(
                "Post delete failed user_id=%s slug=%s status=%s",
                getattr(request.user, "id", None),
                kwargs.get("slug"),
                response.status_code,
            )
        return response

    @extend_schema(
        tags=["Comments"],
        summary="List or create comments",
        description="GET: Returns paginated comments for a post. POST: Creates a new comment. Authentication required for POST.",
        request=CommentWriteSerializer,
        responses={
            200: CommentReadSerializer,
            201: CommentReadSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Post not accessible"),
            404: OpenApiResponse(description="Post not found"),
        },
        examples=[
            OpenApiExample("Request", value={"body": "Great post!"}, request_only=True),
            OpenApiExample(
                "Response",
                value={"id": 1, "author": "user@example.com", "body": "Great post!", "created_at": "2026-03-10"},
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[IsAuthenticatedOrReadOnly],
        url_path="comments",
    )
    def comments(self, request: Request, slug: str | None = None) -> Response:
        post = self.get_object()
        post_visible = (
            post.status == Post.Status.PUBLISHED
            or post.author_id == getattr(request.user, "id", None)
        )

        if request.method == "GET":
            if not post_visible:
                return Response(status=status.HTTP_404_NOT_FOUND)
            comments_queryset: QuerySet[Comment] = post.comments.select_related(
                "author"
            ).order_by("-created_at")
            page = self.paginate_queryset(comments_queryset)
            if page is not None:
                serializer = CommentReadSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = CommentReadSerializer(comments_queryset, many=True)
            return Response(serializer.data)

        if not post_visible:
            return Response(status=status.HTTP_403_FORBIDDEN)

        logger.info(
            "Comment create attempt user_id=%s post_slug=%s",
            getattr(request.user, "id", None),
            post.slug,
        )
        serializer = CommentWriteSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(author=request.user, post=post)
            publish_comment_created(comment)
        except Exception:
            logger.exception(
                "Comment create exception user_id=%s post_slug=%s",
                getattr(request.user, "id", None),
                post.slug,
            )
            raise
        logger.info(
            "Comment create success comment_id=%s user_id=%s",
            comment.id,
            getattr(request.user, "id", None),
        )
        return Response(
            CommentReadSerializer(comment).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=["Comments"],
        summary="Update or delete a comment",
        description="PATCH: Updates a comment. DELETE: Deletes a comment. Authentication required. Only the comment author can modify or delete.",
        request=CommentWriteSerializer,
        responses={
            200: CommentReadSerializer,
            204: OpenApiResponse(description="Comment deleted"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the comment author"),
            404: OpenApiResponse(description="Comment not found"),
        },
        examples=[
            OpenApiExample("Request", value={"body": "Updated comment"}, request_only=True),
            OpenApiExample("Response", value={"id": 1, "body": "Updated comment"}, response_only=True, status_codes=["200"]),
        ],
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path=r"comments/(?P<comment_id>[^/.]+)",
    )
    def comment_detail(
        self, request: Request, slug: str | None = None, comment_id: str | None = None
    ) -> Response:
        post = self.get_object()
        comment = get_object_or_404(
            post.comments.select_related("author"), pk=comment_id
        )
        if comment.author_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if request.method == "PATCH":
            logger.info(
                "Comment update attempt comment_id=%s user_id=%s",
                comment.id,
                request.user.id,
            )
            serializer = CommentWriteSerializer(
                comment, data=request.data, partial=True
            )
            try:
                serializer.is_valid(raise_exception=True)
                updated_comment = serializer.save()
            except Exception:
                logger.exception(
                    "Comment update exception comment_id=%s user_id=%s",
                    comment.id,
                    request.user.id,
                )
                raise
            logger.info(
                "Comment update success comment_id=%s user_id=%s",
                updated_comment.id,
                request.user.id,
            )
            return Response(
                CommentReadSerializer(updated_comment).data, status=status.HTTP_200_OK
            )

        logger.info(
            "Comment delete attempt comment_id=%s user_id=%s",
            comment.id,
            request.user.id,
        )
        comment.delete()
        logger.info(
            "Comment delete success comment_id=%s user_id=%s",
            comment.id,
            request.user.id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
