from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.blog.models import Post


class IsPostPublishedOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return obj.status == Post.Status.PUBLISHED or obj.author_id == getattr(
                request.user, "id", None
            )
        return obj.author_id == getattr(request.user, "id", None)
