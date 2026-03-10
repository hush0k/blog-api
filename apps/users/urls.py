from rest_framework.routers import DefaultRouter

from apps.users.views import RegisterViewSet, UserMeViewSet

router = DefaultRouter()
router.register(r"auth/register", RegisterViewSet, basename="auth-register")
router.register(r"users/me", UserMeViewSet, basename="users-me")

urlpatterns = router.urls
