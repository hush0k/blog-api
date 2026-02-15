import logging

from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.core.cache import cache

from apps.blog.models import Post
from apps.blog.permissions import ReadPublisherOrOwner, IsOwnerOrReadOnly
from apps.blog.serializers import PostReadSerializer, PostWriteSerializer, CommentReadSerializer, CommentWriteSerializer
from apps.common.ratelimit import ratelimit_or_429, user_or_ip
from apps.blog.redis_events import publish_comment_created

logger = logging.getLogger("blog")
LIST_CACHE_KEY = "post:list:published:v1"
LIST_CACHE_TTL = 60

class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    queryset = Post.objects.all().select_related("author", "category").prefetch_related("tags")

    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadPublisherOrOwner,
        IsOwnerOrReadOnly,
    ]

    def list(self, request, *args, **kwargs):
        # I choose manually cache the list of published posts because it is the most common and expensive operation. The cache is invalidated when a post is created, updated or deleted.
        cached = cache.get(LIST_CACHE_KEY)
        if cached is not None:
            logger.debug("Post list cache hit")
            return Response(cached)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PostReadSerializer(page, many=True)
            data = serializer.data
            cache.set(LIST_CACHE_KEY, data, LIST_CACHE_TTL)
            return self.get_paginated_response(data)

        serializer = PostReadSerializer(queryset, many=True)
        data = serializer.data
        cache.set(LIST_CACHE_KEY, data, LIST_CACHE_TTL)
        return Response(data)


    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return PostReadSerializer
        return PostWriteSerializer

    def perform_create(self, serializer):
        logger.info("Post create attempt user_id=%s", getattr(self.request.user, "id", None))
        post = serializer.save(author=self.request.user)
        cache.set(LIST_CACHE_KEY, post, LIST_CACHE_TTL)
        logger.info("Post created id=%s user_id=%s slug=%s", post.id, getattr(self.request.user, "id", None), post.slug)
        return post

    def partial_update(self, request, *args, **kwargs):
        slug = kwargs.get("slug")
        logger.info("Post update attempt user_id=%s slug=%s", getattr(request.user, "id", None), slug)
        try:
            response = super().partial_update(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
                cache.delete(LIST_CACHE_KEY)
                logger.info("Post updated user_id=%s slug=%s", getattr(request.user, "id", None), slug)
            else:
                logger.warning("Post update failed user_id=%s slug=%s status=%s data=%s",
                               getattr(request.user, "id", None), slug, response.status_code, response.data)
            return response
        except Exception:
            logger.exception("Post update exception user_id=%s slug=%s", getattr(request.user, "id", None), slug)
            raise

    def destroy(self, request, *args, **kwargs):
        slug = kwargs.get("slug")
        logger.info("Post delete attempt user_id=%s slug=%s", getattr(request.user, "id", None), slug)
        try:
            response = super().destroy(request, *args, **kwargs)
            logger.warning("Post deleted user_id=%s slug=%s status=%s",
                           getattr(request.user, "id", None), slug, response.status_code)
            return response
        except Exception:
            logger.exception("Post delete exception user_id=%s slug=%s", getattr(request.user, "id", None), slug)
            raise


    @ratelimit_or_429(key=user_or_ip, rate="20/m", method=["POST"], group="post_create")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticatedOrReadOnly, ReadPublisherOrOwner], url_path="comments")
    def comments(self, request, slug=None):
        post = self.get_object()
        if request.method == "GET":
            logger.debug("Comments list post_slug=%s", post.slug)
            comments = post.comments.select_related("author").order_by("-created_at")
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = CommentReadSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = CommentReadSerializer(comments, many=True)
            return Response(serializer.data)


        logger.info(
            "Comment create attempt user_id=%s post_slug=%s",
            getattr(request.user, "id", None),
            post.slug,
        )
        serializer = CommentWriteSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            logger.warning(
                "Comment validation failed user_id=%s post_slug=%s errors=%s",
                getattr(request.user, "id", None),
                post.slug,
                serializer.errors,
            )
            logger.exception("Comment validation exception user_id=%s post_slug=%s",
                             getattr(request.user, "id", None), post.slug)
            raise
        try:
            comment = serializer.save(author=self.request.user)
            publish_comment_created(comment)
        except Exception:
            logger.exception("Comment create exception user_id=%s post_slug=%s",
                             getattr(request.user, "id", None), post.slug)
            raise

        logger.info(
            "Comment created id=%s user_id=%s post_slug=%s",
            comment.id,
            getattr(request.user, "id", None),
            post.slug,
        )
        return Response(CommentReadSerializer(comment).data, status=status.HTTP_201_CREATED)