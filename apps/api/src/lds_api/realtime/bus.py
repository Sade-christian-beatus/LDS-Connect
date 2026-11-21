"""Diffusion temps réel des scores (Redis pub/sub → Server-Sent Events)."""

import logging

import redis

from lds_api.core.ratelimit import get_redis

log = logging.getLogger(__name__)
CHANNEL = "lds:live"


def publish(payload_json: str) -> None:
    """Publie une mise à jour de match. Sans Redis, le direct est simplement indisponible."""
    try:
        get_redis().publish(CHANNEL, payload_json)
    except redis.RedisError:
        log.warning("Redis indisponible : mise à jour en direct non diffusée")
