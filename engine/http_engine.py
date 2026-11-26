from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx

from config import MAX_CONCURRENCY, MAX_REQUESTS, MIN_INTERVAL_MS


async def run_http_test(
    url: str, count: int, interval_ms: int, concurrency: int
) -> list[dict]:
    if not 1 <= count <= MAX_REQUESTS:
        raise ValueError("Nombre de requêtes hors limites.")
    if interval_ms < MIN_INTERVAL_MS:
        raise ValueError("Intervalle trop court.")
    if not 1 <= concurrency <= MAX_CONCURRENCY:
        raise ValueError("Concurrence hors limites.")

    semaphore = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(10.0, connect=5.0)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    results: list[dict] = []

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "TRHACKNON-Web-Stress-Lab/1.0"},
    ) as client:

        async def request_once(index: int) -> dict:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(url)
                    elapsed = (time.perf_counter() - started) * 1000
                    return {
                        "index": index,
                        "status": response.status_code,
                        "latency_ms": round(elapsed, 2),
                        "size": len(response.content),
                        "error": None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                except httpx.HTTPError as exc:
                    elapsed = (time.perf_counter() - started) * 1000
                    return {
                        "index": index,
                        "status": 0,
                        "latency_ms": round(elapsed, 2),
                        "size": 0,
                        "error": str(exc)[:250],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

        tasks = []
        for index in range(count):
            tasks.append(asyncio.create_task(request_once(index + 1)))
            if index < count - 1:
                await asyncio.sleep(interval_ms / 1000)

        results = await asyncio.gather(*tasks)

    return results
