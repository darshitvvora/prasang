import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Locality(Base):
    """A city (area NULL) or a city area. Feeds GET /locations."""

    __tablename__ = "localities"
    __table_args__ = (UniqueConstraint("city", "area", name="uq_localities_city_area"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city: Mapped[str] = mapped_column(String(80), index=True)
    area: Mapped[str | None] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(default=0)
