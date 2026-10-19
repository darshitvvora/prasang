import re
import secrets
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:100] or "artist"


async def unique_slug(session: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while (await session.execute(select(ArtistProfile.id).where(ArtistProfile.slug == slug))).first():
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug
