import json
from typing import Any

from django.core.management.base import BaseCommand
from django_redis import get_redis_connection

from apps.blog.redis_events import CHANNEL_NAME


class Command(BaseCommand):
    help = "Subscribe to Redis comments channel and print incoming messages."

    def handle(self, *args: Any, **options: Any) -> None:
        redis_connection = get_redis_connection("default")
        pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(CHANNEL_NAME)
        self.stdout.write(f"Listening on Redis channel: {CHANNEL_NAME}")

        for message in pubsub.listen():
            data = message.get("data")
            if isinstance(data, (bytes, bytearray)):
                data = data.decode("utf-8", errors="replace")
            try:
                obj = json.loads(data)
                self.stdout.write(json.dumps(obj, ensure_ascii=False))
            except Exception:
                self.stdout.write(str(data))
