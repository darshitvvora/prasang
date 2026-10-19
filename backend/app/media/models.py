import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import MediaKindEnum
from app.timestamps import Timestamps


class ArtistMedia(Timestamps, Base):
    __tablename__ = "artist_media"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artist_profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(MediaKindEnum)
    url: Mapped[str] = mapped_column(String(1000))
    embed_url: Mapped[str | None] = mapped_column(String(1500))
    storage_key: Mapped[str | None] = mapped_column(String(300))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))
    caption: Mapped[str | None] = mapped_column(String(300))
    display_order: Mapped[int] = mapped_column(default=0)

    artist: Mapped["ArtistProfile"] = relationship(back_populates="media")  # noqa: F821
