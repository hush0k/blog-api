from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.blog.stats_view import stats_view
from apps.blog.views import PostViewSet

router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")

urlpatterns = router.urls + [
    path("stats/", stats_view, name="stats"),
]
