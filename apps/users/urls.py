from rest_framework.routers import DefaultRouter

from apps.users.views import RegisterViewSet

router = DefaultRouter()
router.register(r"auth/register", RegisterViewSet, basename="auth-register")

urlpatterns = router.urls
