from rest_framework import routers

from apps.blog.views import PostViewSet

router = routers.DefaultRouter()
router.register(r"", PostViewSet, basename="post")

urlpatterns = router.urls