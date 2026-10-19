"""Instagram / YouTube / Facebook links → official iframe embed URLs. No API keys needed.

Two uses:
- post embeds (portfolio media): parse_embed(kind, url)
- profile widgets (whole profile/channel/page): social_widgets(...) from the artist's handles
Only https/http links on the exact platform hosts are accepted; everything else is a 422 on `url`.
"""
import logging
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, quote, urlparse

import httpx

from app.errors import validation

log = logging.getLogger(__name__)
SocialKind = Literal["youtube", "instagram", "facebook"]

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com", "fb.watch"}

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
IG_CODE = re.compile(r"^[A-Za-z0-9_-]{5,40}$")
IG_HANDLE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
YT_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
YT_HANDLE = re.compile(r"^[A-Za-z0-9._-]{3,100}$")
FB_PATH = re.compile(r"^/[A-Za-z0-9.\-_/%?=&]+$")


@dataclass(frozen=True)
class Embed:
    kind: SocialKind
    url: str
    embed_url: str


@dataclass(frozen=True)
class Widget:
    platform: SocialKind
    profile_url: str
    embed_url: str | None


def _reject(message: str, field: str = "url"):
    raise validation({field: message})


def _parse(url: str, hosts: set[str], field: str = "url"):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in hosts:
        _reject("Paste a link from the platform's website or app", field)
    return parsed


def _youtube(url: str) -> Embed:
    p = _parse(url, YOUTUBE_HOSTS)
    host, parts = (p.hostname or "").lower(), [s for s in p.path.split("/") if s]
    if host == "youtu.be":
        video_id = parts[0] if parts else ""
    elif parts[:1] == ["watch"]:
        video_id = parse_qs(p.query).get("v", [""])[0]
    elif parts[:1] in (["shorts"], ["embed"], ["live"]) and len(parts) > 1:
        video_id = parts[1]
    else:
        video_id = ""
    if not VIDEO_ID.match(video_id):
        _reject("That doesn't look like a YouTube video link")
    return Embed("youtube", url.strip(), f"https://www.youtube-nocookie.com/embed/{video_id}")


def _instagram(url: str) -> Embed:
    p = _parse(url, INSTAGRAM_HOSTS)
    parts = [s for s in p.path.split("/") if s]
    if len(parts) < 2 or parts[0] not in ("p", "reel", "tv") or not IG_CODE.match(parts[1]):
        _reject("Paste a link to an Instagram post or reel")
    return Embed("instagram", url.strip(), f"https://www.instagram.com/{parts[0]}/{parts[1]}/embed")


def _facebook(url: str) -> Embed:
    p = _parse(url, FACEBOOK_HOSTS)
    if not FB_PATH.match(p.path or "/x") or len(p.path) < 3:
        _reject("Paste a link to a Facebook post or video")
    canonical = f"https://{'fb.watch' if p.hostname == 'fb.watch' else 'www.facebook.com'}{p.path}"
    is_video = p.hostname == "fb.watch" or "/videos/" in p.path or p.path.startswith("/watch") or "/reel/" in p.path
    plugin = "video.php" if is_video else "post.php"
    return Embed("facebook", url.strip(),
                 f"https://www.facebook.com/plugins/{plugin}?href={quote(canonical, safe='')}&show_text=true&width=500")


def parse_embed(kind: str, url: str) -> Embed:
    if kind == "youtube":
        return _youtube(url)
    if kind == "instagram":
        return _instagram(url)
    if kind == "facebook":
        return _facebook(url)
    _reject("Unsupported platform")
    raise AssertionError  # unreachable


# ---------- profile handles ----------

def normalize_instagram_handle(raw: str) -> str:
    raw = raw.strip()
    if "/" in raw or raw.lower().startswith(("http", "www.", "instagram.com")):
        p = _parse(raw, INSTAGRAM_HOSTS, "instagramHandle")
        raw = next((s for s in p.path.split("/") if s), "")
    handle = raw.lstrip("@")
    if not IG_HANDLE.match(handle):
        _reject("Enter your Instagram username, e.g. arjunmagic", "instagramHandle")
    return handle


def normalize_facebook_url(raw: str) -> str:
    p = _parse(raw, FACEBOOK_HOSTS - {"fb.watch"}, "facebookUrl")
    path = p.path.rstrip("/")
    if not path or not FB_PATH.match(path):
        _reject("Enter your Facebook page link, e.g. facebook.com/yourpage", "facebookUrl")
    return f"https://www.facebook.com{path}"


def parse_youtube_channel(raw: str) -> tuple[str | None, str | None]:
    """Returns (channel_id, handle). One of them is set; validation error if neither can be read."""
    raw = raw.strip()
    if YT_CHANNEL_ID.match(raw):
        return raw, None
    if "/" in raw:
        p = _parse(raw, YOUTUBE_HOSTS - {"youtu.be"}, "youtubeChannel")
        parts = [s for s in p.path.split("/") if s]
        if len(parts) >= 2 and parts[0] == "channel" and YT_CHANNEL_ID.match(parts[1]):
            return parts[1], None
        if parts and parts[0].startswith("@"):
            raw = parts[0]
        elif len(parts) >= 2 and parts[0] in ("c", "user"):
            raw = parts[1]
        else:
            _reject("Enter your channel link or @handle", "youtubeChannel")
    handle = raw.lstrip("@")
    if not YT_HANDLE.match(handle):
        _reject("Enter your channel link or @handle", "youtubeChannel")
    return None, handle


async def resolve_youtube_channel_id(handle: str, api_key: str | None, http: httpx.AsyncClient | None = None) -> str | None:
    """@handle → UC… channel id via the YouTube Data API (free quota). None if no key or lookup fails."""
    if not api_key:
        return None
    own = http is None
    http = http or httpx.AsyncClient(timeout=3)
    try:
        res = await http.get("https://www.googleapis.com/youtube/v3/channels",
                             params={"part": "id", "forHandle": "@" + handle.lstrip("@"), "key": api_key})
        items = res.json().get("items", []) if res.status_code == 200 else []
        channel_id = items[0]["id"] if items else None
        return channel_id if channel_id and YT_CHANNEL_ID.match(channel_id) else None
    except Exception:  # network/quota problems must never block saving a profile
        log.warning("youtube handle lookup failed for %s", handle, exc_info=True)
        return None
    finally:
        if own:
            await http.aclose()


def social_widgets(instagram_handle: str | None, youtube_channel: str | None, youtube_channel_id: str | None,
                   facebook_url: str | None) -> list[Widget]:
    widgets: list[Widget] = []
    if instagram_handle:
        widgets.append(Widget("instagram", f"https://www.instagram.com/{instagram_handle}/",
                              f"https://www.instagram.com/{instagram_handle}/embed"))
    if youtube_channel:
        if youtube_channel_id:
            widgets.append(Widget("youtube", f"https://www.youtube.com/channel/{youtube_channel_id}",
                                  f"https://www.youtube-nocookie.com/embed/videoseries?list=UU{youtube_channel_id[2:]}"))
        else:
            _, handle = parse_youtube_channel(youtube_channel)
            widgets.append(Widget("youtube", f"https://www.youtube.com/@{handle}", None))
    if facebook_url:
        widgets.append(Widget("facebook", facebook_url,
                              "https://www.facebook.com/plugins/page.php?href=" + quote(facebook_url, safe="")
                              + "&tabs=timeline&width=500&height=600&small_header=true&adapt_container_width=true"))
    return widgets
