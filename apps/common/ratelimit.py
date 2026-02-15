from functools import wraps

from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response


def _too_many():
    return Response(
        {"detail": "Too many requests, please try again later."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )

def ratelimit_or_429(*, key, rate, method=("POST",), group=None):
    def decorator(view_func):
        limited = ratelimit(key=key, rate=rate, method=method, group=group, block=False)

        @wraps(view_func)
        @limited
        def wrapper(request, *args, **kwargs):
            if getattr(request, "limited", False):
                return _too_many()
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def user_or_ip(group, request):
    u = getattr(request, "user", None)
    if u and u.is_authenticated:
        return f"user:{u.id}"
    ip = request.META.get("REMOTE_ADDR", "")
    return f"ip:{ip}"
