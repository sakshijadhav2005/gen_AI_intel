import redis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = "vericheck_raw_posts"

def push_to_queue(item: dict):
    redis_client.lpush(QUEUE_NAME, json.dumps(item))

def pop_from_queue() -> dict:
    # block for 2 seconds
    result = redis_client.brpop(QUEUE_NAME, timeout=2)
    if result:
        # result is a tuple (queue_name, data)
        return json.loads(result[1])
    return None
