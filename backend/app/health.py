"""Liveness and readiness endpoints."""
import asyncio

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine

router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


async def _postgres() -> bool:
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def _elasticsearch() -> bool:
    async with httpx.AsyncClient(timeout=3) as c:
        res = await c.get(f"{get_settings().elasticsearch_url}/_cluster/health")
        return res.status_code == 200 and res.json().get("status") in ("green", "yellow")


async def _temporal() -> bool:
    host, _, port = get_settings().temporal_address.partition(":")
    _, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port or 7233)), timeout=3)
    writer.close()
    return True


@router.get("/readyz")
async def readyz():
    checks = {"postgres": _postgres, "elasticsearch": _elasticsearch, "temporal": _temporal}
    result: dict[str, str] = {}
    for name, check in checks.items():
        try:
            result[name] = "ok" if await check() else "down"
        except Exception:
            result[name] = "down"
    status = 200 if all(v == "ok" for v in result.values()) else 503
    return JSONResponse(result, status_code=status)
