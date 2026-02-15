import json
from django_redis import get_redis_connection

def publish_comment_created(comment):
    payload = {
        "type": "comment.created",
        "comment_id": comment.id,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "text": comment.text,
        "created_at": comment.created_at.isoformat(),
    }
    r = get_redis_connection("default")
    r.publish("comments", json.dumps(payload, ensure_ascii=False))