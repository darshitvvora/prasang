"""One rule for who the public can see: published and not suspended (deleted artists are unpublished)."""
from sqlalchemy import and_

from app.artists.models import ArtistProfile


def is_public(profile: ArtistProfile) -> bool:
    return bool(profile.is_published) and profile.suspended_at is None


def public_filter():
    return and_(ArtistProfile.is_published.is_(True), ArtistProfile.suspended_at.is_(None))
