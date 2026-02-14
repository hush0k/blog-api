import logging

from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.blog.models import Post
from apps.blog.permissions import ReadPublisherOrOwner, IsOwnerOrReadOnly
from apps.blog.serializers import PostReadSerializer, PostWriteSerializer, CommentReadSerializer, CommentWriteSerializer

logger = logging.getLogger("blog")

class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    queryset = Post.objects.all().select_related("author", "category").prefetch_related("tags")

    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadPublisherOrOwner,
        IsOwnerOrReadOnly,
    ]

    def get_queryset(self):
        if self.action == "list":
            return self.queryset.filter(status=Post.Status.PUBLISHED)
        return self.queryset

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return PostReadSerializer
        return PostWriteSerializer

    def perform_create(self, serializer):
        logger.info(
            "Post create attempt user_id=%s",
            getattr(self.request.user, "id", None),
        )
        try:
            post = serializer.save(author=self.request.user)
        except Exception:
            logger.warning(
                "Post can't be created user_id=%s",
                getattr(self.request.user, "id", None),
            )
        logger.info(
            "Post is created user_id=%s slug=%s",
            getattr(self.request.user, "id", None),
            post.slug
        )

    def partial_update(self, request, *args, **kwargs):
        slug = kwargs.get("slug")
        logger.info("Post update attempt user_id=%s slug=%s", getattr(request.user, "id", None), slug)
        try:
            response = super().partial_update(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
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