import redis.asyncio as redis

import secret

redis_client = redis.from_url(f"redis://{secret.REDIS_IP}", encoding="utf8", decode_responses=True)
