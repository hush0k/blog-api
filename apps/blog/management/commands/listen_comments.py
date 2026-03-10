import asyncio
import json
from typing import Any

import httpx
import redis.asyncio as aioredis
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.blog.redis_events import CHANNEL_NAME

WEBHOOK_URL = "https://httpbin.org/post"


async def notify(client: httpx.AsyncClient, payload: dict) -> None:
    try:
        response = await client.post(WEBHOOK_URL, json=payload, timeout=5)
        print(f"Webhook sent: {response.status_code}")
    except Exception as e:
        print(f"Webhook failed: {e}")


async def listen(stdout) -> None:
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL_NAME)
    stdout.write(f"Listening on Redis channel: {CHANNEL_NAME}")

    async with httpx.AsyncClient() as client:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                obj = json.loads(message["data"])
                stdout.write(json.dumps(obj, ensure_ascii=False))
                await notify(client, obj)
            except Exception:
                stdout.write(str(message["data"]))


class Command(BaseCommand):
    help = "Subscribe to Redis comments channel (async)."

    def handle(self, *args: Any, **options: Any) -> None:
        asyncio.run(listen(self.stdout))
