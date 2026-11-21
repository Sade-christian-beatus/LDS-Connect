"""Scores en direct par Server-Sent Events (SSE)."""

import contextlib
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from lds_api.core.config import get_settings
from lds_api.realtime.bus import CHANNEL

router = APIRouter(tags=["direct"])
log = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 15


async def _stream(request: Request) -> AsyncIterator[str]:
    client = aioredis.Redis.from_url(get_settings().redis_url)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(CHANNEL)
        yield "retry: 5000\n\n"
        while not await request.is_disconnected():
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=HEARTBEAT_SECONDS
            )
            if msg and msg.get("type") == "message":
                data = msg["data"].decode() if isinstance(msg["data"], bytes) else msg["data"]
                yield f"event: match\ndata: {data}\n\n"
            else:
                yield ": ping\n\n"  # maintien de la connexion (proxys, réseaux mobiles)
    except (aioredis.RedisError, OSError):
        log.warning("Flux direct interrompu : Redis indisponible")
        yield "event: error\ndata: indisponible\n\n"
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()
            await client.aclose()


@router.get("/live", response_class=StreamingResponse)
async def live(request: Request) -> StreamingResponse:
    """Flux des mises à jour de matchs (événement « match » = MatchOut en JSON)."""
    return StreamingResponse(
        _stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
