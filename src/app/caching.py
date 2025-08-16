import asyncio
import hashlib
import inspect
import time
from collections.abc import Callable
from functools import partial
from functools import wraps
from typing import Any

from fastapi.concurrency import run_in_threadpool
from otel import instrument
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError

from app.tools import ORJSONSerializer


@instrument
class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self):
        self.store = {}
        # to safely handle concurrent access
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self.lock:
            if key in self.store:
                value, expires_at = self.store[key]
                if expires_at is None or expires_at > time.time():
                    return value
                else:
                    # key expired, remove it
                    del self.store[key]
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None):
        async with self.lock:
            expires_at = time.time() + ttl if ttl else None
            self.store[key] = (value, expires_at)

    async def delete(self, key: str):
        async with self.lock:
            del self.store[key]


@instrument
class RedisCache:
    """Redis cache with ORJSON serialization."""

    _serializer = ORJSONSerializer

    def __init__(self, redis: aioredis.Redis, prefix: str | None = None):
        self._client = redis
        self._prefix = prefix

    @property
    def client(self):
        return self._client

    async def get(self, key: str):
        if not key:
            return
        if self._prefix:
            key = f"{self._prefix}:{key}"
        try:
            value = await self._client.get(key)
            if value:
                return self._serializer.decode(value)
        except ConnectionError:
            return

    async def set(self, key: str, value: Any, ttl: int | None = None):
        if not key or not value:
            return
        if self._prefix:
            key = f"{self._prefix}:{key}"
        try:
            await self._client.set(key, self._serializer.encode(value), ttl)
        except ConnectionError:
            pass

    async def delete(self, key: str):
        if not key:
            return
        if self._prefix:
            key = f"{self._prefix}:{key}"
        try:
            await self._client.delete(key)
        except ConnectionError:
            return


cache = InMemoryCache()


def set_redis_cache(redis: aioredis.Redis, prefix: str | None = None):
    global cache
    cache = RedisCache(redis, prefix)


def default_key_builder(func, *args, **kwargs) -> str:
    """Generate a key using function name, args and kwargs."""
    return hashlib.md5(f"{func.__name__}:{args}:{kwargs}".encode()).hexdigest()  # type: ignore


def cached(
    _func_or_coro=None,
    *,
    cache_key: str | None = None,
    ttl: int | None = None,
    namespace: str | None = None,
    key_builder: Callable[..., str] = None,
):
    """Simple caching decorator, using redis backend"""

    if not _func_or_coro:
        return partial(
            cached,
            cache_key=cache_key,
            ttl=ttl,
            namespace=namespace,
            key_builder=key_builder,
        )

    @wraps(_func_or_coro)
    async def wrapper(*args, **kwargs):
        async def ensure_async_func(*args, **kwargs):
            """Run cached sync functions in thread pool just like FastAPI."""
            if inspect.iscoroutinefunction(_func_or_coro):
                # async, return as is.
                # unintuitively, we have to await once here,
                # so that caller does not have to await twice.
                # https://stackoverflow.com/a/59268198/532513
                return await _func_or_coro(*args, **kwargs)
            else:
                # sync, wrap in thread and return async
                return await run_in_threadpool(_func_or_coro, *args, **kwargs)

        if cache_key:
            key = cache_key
        elif key_builder:
            key = key_builder(_func_or_coro, args, kwargs)
        else:
            key = default_key_builder(_func_or_coro, args, kwargs)

        if namespace:
            key = f"{namespace}:{key}"

        # caching logic
        value = await cache.get(key)
        if value is None:
            value = await ensure_async_func(*args, **kwargs)
            await cache.set(key, value, ttl)
        return value

    return wrapper
