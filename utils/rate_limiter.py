from time import time_ns
from typing import Callable

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_limiter.callback import default_callback
from fastapi_limiter.identifier import default_identifier
from pyrate_limiter import AbstractBucket, BucketFactory, Duration, Limiter, Rate, RateItem, RedisBucket
from redis.exceptions import RedisError

from utils.redis_client import redis_client


class RedisBucketFactory(BucketFactory):
    """Routes each rate-limit key (user id / IP) to its own RedisBucket,
    so limits are enforced per key instead of globally per endpoint."""

    def __init__(self, rates: list[Rate], prefix: str):
        self.rates = rates
        self.prefix = prefix
        self.buckets: dict[str, AbstractBucket] = {}

    def wrap_item(self, name: str, weight: int = 1) -> RateItem:
        return RateItem(name, time_ns() // 1_000_000, weight=weight)

    async def get(self, item: RateItem) -> AbstractBucket:
        bucket = self.buckets.get(item.name)
        if bucket is None:
            bucket = await RedisBucket.init(self.rates, redis_client, f"rl:{self.prefix}:{item.name}")
            self.buckets[item.name] = bucket
        return bucket


class RateLimiter:
    def __init__(
        self,
        limiter: Limiter,
        identifier: Callable = default_identifier,
        callback: Callable = default_callback,
        blocking: bool = False,
    ):
        self.limiter = limiter
        self.identifier = identifier
        self.callback = callback
        self.blocking = blocking

    async def __call__(self, request: Request, response: Response):
        key = await self.identifier(request)
        try:
            success = await self.limiter.try_acquire_async(key, blocking=self.blocking)
        except RedisError:
            print("RedisError: Rate limiting service unavailable")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable",
            )
        if not success:
            return await self.callback(request, response)


def rate_limited(prefix: str, rate: int, seconds: int, identifier: Callable = default_identifier) -> list[Depends]:
    """Builds a `dependencies=[...]` entry for a per-key rate limit, e.g.
    `dependencies=rate_limited("idea:create", 1, 10, auth.get_identifyer_for_limiter)`."""
    limiter = Limiter(RedisBucketFactory([Rate(rate, Duration.SECOND * seconds)], prefix=prefix))
    return [Depends(RateLimiter(limiter=limiter, identifier=identifier))]
