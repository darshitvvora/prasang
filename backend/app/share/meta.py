"""Link previews: Open Graph / Twitter tags for a shared artist profile (crawlers don't run JavaScript)."""
from dataclasses import dataclass
from html import escape

from app.config import Settings
from app.labels import ARTIST_TYPE_LABELS

START, END = "<!--og:start-->", "<!--og:end-->"
DESCRIPTION_MAX = 160


@dataclass(frozen=True)
class ShareMeta:
    title: str
    description: str
    image: str
    url: str
    type: str = "profile"


def _absolute(url: str | None, base: str) -> str:
    if not url:
        return f"{base}/og-default.png"
    return url if url.startswith(("http://", "https://")) else f"{base}/{url.lstrip('/')}"


def share_meta(profile, settings: Settings) -> ShareMeta:
    base = settings.public_web_url.rstrip("/")
    bio = " ".join((profile.bio or "").split())
    description = bio if len(bio) <= DESCRIPTION_MAX else bio[: DESCRIPTION_MAX - 1].rstrip() + "…"
    title = f"{profile.stage_name} · {ARTIST_TYPE_LABELS[profile.artist_type]} · {profile.location_city}"
    return ShareMeta(title=title, description=description or title, image=_absolute(profile.profile_image_url, base),
                     url=f"{base}/profile/{profile.slug}")


def render_head(meta: ShareMeta) -> str:
    e = lambda v: escape(v, quote=True)  # noqa: E731 - every value is user input
    tags = [
        f"<title>{e(meta.title)}</title>",
        f'<meta name="description" content="{e(meta.description)}" />',
        '<meta property="og:site_name" content="Prasang" />',
        f'<meta property="og:title" content="{e(meta.title)}" />',
        f'<meta property="og:description" content="{e(meta.description)}" />',
        f'<meta property="og:image" content="{e(meta.image)}" />',
        f'<meta property="og:url" content="{e(meta.url)}" />',
        f'<meta property="og:type" content="{e(meta.type)}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<link rel="canonical" href="{e(meta.url)}" />',
    ]
    return "\n    ".join(tags)


def inject(index_html: str, head: str) -> str:
    """Replace what sits between the og markers; pages without markers are returned unchanged."""
    start, end = index_html.find(START), index_html.find(END)
    if start < 0 or end < start:
        return index_html
    return index_html[: start + len(START)] + head + index_html[end:]
