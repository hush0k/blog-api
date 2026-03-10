import asyncio

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.blog.models import Post
from apps.users.models import User


@extend_schema(
    tags=["Stats"],
    summary="Get API stats",
    description="Returns total number of published posts and registered users.",
    responses={
        200: OpenApiResponse(description="Stats returned"),
    },
)
async def stats_view(request):
    post_count, user_count = await asyncio.gather(
        Post.objects.acount(),
        User.objects.acount(),
    )
    return JsonResponse({"posts": post_count, "users": user_count})
