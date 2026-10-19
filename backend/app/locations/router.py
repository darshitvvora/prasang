from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contract import City, LocationsResponse
from app.db import get_session
from app.locations.models import Locality

router = APIRouter(tags=["locations"])


@router.get("/locations", response_model=LocationsResponse, response_model_by_alias=True)
async def locations(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(Locality).order_by(Locality.sort_order))).scalars().all()
    cities = [City(name=r.city, areas=[]) for r in rows if r.area is None]
    by_name = {c.name: c for c in cities}
    for r in rows:
        if r.area is not None and r.city in by_name:
            by_name[r.city].areas.append(r.area)
    return LocationsResponse(cities=cities)
