"""Minimal in-process pub/sub so the SSE endpoint can stream live phase/agent
events for a run. One asyncio.Queue per run_id. Swap for Redis pub/sub if
you run multiple backend replicas (see README scaling section).
"""
import asyncio
from collections import defaultdict

_queues: dict[int, list[asyncio.Queue]] = defaultdict(list)


def subscribe(run_id: int) -> asyncio.Queue:
    q = asyncio.Queue()
    _queues[run_id].append(q)
    return q


def unsubscribe(run_id: int, q: asyncio.Queue):
    if q in _queues[run_id]:
        _queues[run_id].remove(q)


async def publish(run_id: int, event: dict):
    for q in list(_queues.get(run_id, [])):
        await q.put(event)
