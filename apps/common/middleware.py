import logging
from typing import Any, Callable

request_logger = logging.getLogger("debug.request")


class DebugRequestsMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        request_logger.debug(
            "IN %s %s user=%s",
            request.method,
            request.get_full_path(),
            getattr(request.user, "id", None),
        )
        return self.get_response(request)
