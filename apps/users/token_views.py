import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.ratelimit import ratelimit_or_429

logger = logging.getLogger("users")


class TokenObtainPairRateLimitedView(TokenObtainPairView):
    @ratelimit_or_429(key="ip", rate="10/m", method=("POST",), group="auth_token")
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        email = request.data.get("email")
        logger.info("Login attempt email=%s ip=%s", email, request.META.get("REMOTE_ADDR"))
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info("Login success email=%s", email)
        else:
            logger.warning("Login failed email=%s status=%s", email, response.status_code)
        return response
