import logging
from typing import Any, Callable
from django.conf import settings

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


class LanguageDetectionMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        language = self._detect_language(request)
        request.LANGUAGE_CODE = language
        return self.get_response(request)

    @staticmethod
    def _detect_language(request):
        if request.user.is_authenticated and request.user.language:
            return request.user.language

        lang = request.GET.get("lang")
        if lang:
             return lang

        accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE")
        if accept_language:
            return accept_language.split(",")[0].split("-")[0].strip()

        return settings.LANGUAGE_CODE





