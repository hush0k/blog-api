import json
import redis
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Subscribe to Redis channel 'comments' and print incoming messages."

    def handle(self, *args, **options):
        r = redis.Redis(host="127.0.0.1", port=6379, db=1, socket_timeout=None)

        pubsub = r.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe("comments")

        self.stdout.write("Listening on Redis channel: comments")

        for message in pubsub.listen():
            data = message.get("data")
            if isinstance(data, (bytes, bytearray)):
                data = data.decode("utf-8", errors="replace")

            try:
                obj = json.loads(data)
                self.stdout.write(json.dumps(obj, ensure_ascii=False))
            except Exception:
                self.stdout.write(str(data))
