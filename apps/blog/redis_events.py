import json
from typing import Any

from django_redis import get_redis_connection

CHANNEL_NAME = "comments"
EVENT_TYPE_COMMENT_CREATED = "comment.created"


def publish_comment_created(comment: Any) -> None:
    payload = {
        "type": EVENT_TYPE_COMMENT_CREATED,
        "comment_id": comment.id,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }
    redis_connection = get_redis_connection("default")
    redis_connection.publish(CHANNEL_NAME, json.dumps(payload, ensure_ascii=False))
