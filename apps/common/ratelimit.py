from functools import wraps
from typing import Any, Callable

from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response

RATE_LIMIT_ERROR_MESSAGE = "Too many requests. Try again later."


def too_many_requests_response() -> Response:
    return Response(
        {"detail": RATE_LIMIT_ERROR_MESSAGE},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def ratelimit_or_429(
    *, key: Any, rate: str, method: tuple[str, ...] | list[str] = ("POST",), group: str | None = None
) -> Callable:
    def decorator(view_func: Callable) -> Callable:
        limited = ratelimit(key=key, rate=rate, method=method, group=group, block=False)

        @wraps(view_func)
        @limited
        def wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
            if getattr(request, "limited", False):
                return too_many_requests_response()
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def user_or_ip(group: str, request: Any) -> str:
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return f"user:{user.id}"
    ip = request.META.get("REMOTE_ADDR", "")
    return f"ip:{ip}"
