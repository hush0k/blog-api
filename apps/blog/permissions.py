from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return getattr(obj, "author_id", None) == getattr(request.user, "id", None)

class ReadPublisherOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if getattr(obj, "status", None) == "published":
            return True

        return getattr(obj, "author_id", None) == getattr(request.user, "id", None)
