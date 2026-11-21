"""Limitation de débit à fenêtre fixe, stockée dans Redis."""

import contextlib
import logging
from functools import lru_cache

import redis
from fastapi import HTTPException, status

from lds_api.core.config import get_settings

log = logging.getLogger(__name__)


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, socket_timeout=1)


def hit(key: str, *, limit: int, window_seconds: int) -> None:
    """Compte un appel ; lève 429 au-delà de `limit` appels par fenêtre.

    Si Redis est indisponible, la requête passe (journalisé) : mieux vaut un service
    dégradé qu'une plateforme bloquée un jour de match.
    """
    full_key = f"rl:{key}"
    try:
        pipe = get_redis().pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, window_seconds, nx=True)
        count, _ = pipe.execute()
    except redis.RedisError:
        log.warning("Redis indisponible : limitation de débit ignorée pour %s", key)
        return
    if count > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de tentatives, réessayez dans quelques minutes",
            headers={"Retry-After": str(window_seconds)},
        )


def reset(key: str) -> None:
    with contextlib.suppress(redis.RedisError):
        get_redis().delete(f"rl:{key}")
