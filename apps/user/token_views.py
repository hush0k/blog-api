from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from apps.common.ratelimit import ratelimit_or_429

class TokenObtainPairRateLimitedView(TokenObtainPairView):
    @ratelimit_or_429(key="ip", rate="10/m", method=("POST",), group="auth_token")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

def too_many_requests_response():
    return Response(
        {"detail": "Too many requests. Try again later."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
