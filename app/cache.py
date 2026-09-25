from app.redis_client import redis_client

CACHE_KEY_PREFIX = "cache:link:"
CACHE_TTL_SECONDS = 3600  


def _cache_key(code: str) -> str:
    return f"{CACHE_KEY_PREFIX}{code}"


def get_cached_target(code: str) -> str | None:
    return redis_client.get(_cache_key(code))


def set_cached_target(code: str, target_url: str) -> None:
    redis_client.set(_cache_key(code), target_url, ex=CACHE_TTL_SECONDS)


def invalidate_cached_target(code: str) -> None:
    redis_client.delete(_cache_key(code))