"""Social link parsing: post embeds (media) and profile widgets. Review Focus 4: hostile URLs never pass."""
import httpx
import pytest

from app.embeds import (
    normalize_facebook_url,
    normalize_instagram_handle,
    parse_embed,
    parse_youtube_channel,
    resolve_youtube_channel_id,
    social_widgets,
)
from app.errors import AppError

NOCOOKIE = "https://www.youtube-nocookie.com/embed/"


@pytest.mark.parametrize(("url", "embed"), [
    ("https://www.youtube.com/watch?v=aqz-KE-bpKQ", NOCOOKIE + "aqz-KE-bpKQ"),
    ("https://youtube.com/watch?feature=share&v=aqz-KE-bpKQ", NOCOOKIE + "aqz-KE-bpKQ"),
    ("https://m.youtube.com/watch?v=aqz-KE-bpKQ", NOCOOKIE + "aqz-KE-bpKQ"),
    ("https://youtu.be/aqz-KE-bpKQ?si=x", NOCOOKIE + "aqz-KE-bpKQ"),
    ("https://www.youtube.com/shorts/aqz-KE-bpKQ", NOCOOKIE + "aqz-KE-bpKQ"),
])
def test_youtube_links(url, embed):
    e = parse_embed("youtube", url)
    assert (e.kind, e.embed_url) == ("youtube", embed)


@pytest.mark.parametrize(("url", "embed"), [
    ("https://www.instagram.com/p/C9xYz12AbCd/", "https://www.instagram.com/p/C9xYz12AbCd/embed"),
    ("https://instagram.com/reel/C9xYz12AbCd/?igsh=abc", "https://www.instagram.com/reel/C9xYz12AbCd/embed"),
    ("https://www.instagram.com/tv/C9xYz12AbCd", "https://www.instagram.com/tv/C9xYz12AbCd/embed"),
])
def test_instagram_links(url, embed):
    assert parse_embed("instagram", url).embed_url == embed


def test_facebook_post_and_video_links():
    post = parse_embed("facebook", "https://www.facebook.com/arjunmagic/posts/pfbid0abc")
    assert post.embed_url.startswith("https://www.facebook.com/plugins/post.php?href=https%3A%2F%2Fwww.facebook.com%2Farjunmagic%2Fposts%2Fpfbid0abc")
    video = parse_embed("facebook", "https://www.facebook.com/arjunmagic/videos/1093847561029384/")
    assert video.embed_url.startswith("https://www.facebook.com/plugins/video.php?href=")
    watch = parse_embed("facebook", "https://fb.watch/abcDEF123/")
    assert "plugins/video.php" in watch.embed_url


@pytest.mark.parametrize(("kind", "url"), [
    ("youtube", "javascript:alert(1)"),
    ("instagram", "https://instagram.com.evil.com/p/C9xYz12AbCd/"),
    ("youtube", "https://example.com/watch?v=aqz-KE-bpKQ"),
    ("youtube", "ftp://youtube.com/watch?v=aqz-KE-bpKQ"),
    ("youtube", "https://www.youtube.com/watch?list=abc"),
    ("instagram", "https://www.instagram.com/arjunmagic/"),
    ("facebook", "https://www.facebook.com.evil.com/x/posts/1"),
    ("instagram", "https://www.youtube.com/watch?v=aqz-KE-bpKQ"),
    ("youtube", "https://www.youtube.com/watch?v=aqz\"><script>"),
])
def test_hostile_or_unsupported_links_are_rejected(kind, url):
    with pytest.raises(AppError) as err:
        parse_embed(kind, url)
    assert err.value.status == 422
    assert "url" in err.value.details["fields"]


@pytest.mark.parametrize(("raw", "handle"), [
    ("arjunmagic", "arjunmagic"), ("@arjun.magic_", "arjun.magic_"), ("https://www.instagram.com/arjunmagic/?hl=en", "arjunmagic"),
])
def test_instagram_handle_normalisation(raw, handle):
    assert normalize_instagram_handle(raw) == handle


@pytest.mark.parametrize("raw", ["arjun magic", "x" * 31, "https://evil.com/arjun", "@"])
def test_bad_instagram_handles(raw):
    with pytest.raises(AppError):
        normalize_instagram_handle(raw)


def test_facebook_page_url_normalisation():
    assert normalize_facebook_url("facebook.com/arjunmagic") == "https://www.facebook.com/arjunmagic"
    assert normalize_facebook_url("https://m.facebook.com/arjunmagic/?ref=x") == "https://www.facebook.com/arjunmagic"
    with pytest.raises(AppError):
        normalize_facebook_url("https://facebook.com.evil.com/arjun")


@pytest.mark.parametrize(("raw", "expected"), [
    ("UCabcdefghijklmnopqrstuv", ("UCabcdefghijklmnopqrstuv", None)),
    ("https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv", ("UCabcdefghijklmnopqrstuv", None)),
    ("@ArjunMagic", (None, "ArjunMagic")),
    ("https://www.youtube.com/@ArjunMagic/videos", (None, "ArjunMagic")),
    ("ArjunMalhotraMagic", (None, "ArjunMalhotraMagic")),
])
def test_youtube_channel_parsing(raw, expected):
    assert parse_youtube_channel(raw) == expected


async def test_youtube_handle_resolution_uses_data_api_when_key_set():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["forHandle"] == "@ArjunMagic"
        return httpx.Response(200, json={"items": [{"id": "UCabcdefghijklmnopqrstuv"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert await resolve_youtube_channel_id("@ArjunMagic", api_key="k", http=http) == "UCabcdefghijklmnopqrstuv"
        assert await resolve_youtube_channel_id("@ArjunMagic", api_key=None, http=http) is None


async def test_youtube_resolution_failure_is_not_fatal():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
        assert await resolve_youtube_channel_id("@ArjunMagic", api_key="k", http=http) is None


def test_social_widgets():
    widgets = social_widgets(instagram_handle="arjunmagic", youtube_channel="@ArjunMagic", youtube_channel_id=None,
                             facebook_url="https://www.facebook.com/arjunmagic")
    by = {w.platform: w for w in widgets}
    assert by["instagram"].embed_url == "https://www.instagram.com/arjunmagic/embed"
    assert by["instagram"].profile_url == "https://www.instagram.com/arjunmagic/"
    assert by["youtube"].embed_url is None and by["youtube"].profile_url == "https://www.youtube.com/@ArjunMagic"
    assert by["facebook"].embed_url.startswith("https://www.facebook.com/plugins/page.php?href=https%3A%2F%2Fwww.facebook.com%2Farjunmagic")
    with_id = social_widgets(None, "@ArjunMagic", "UCabcdefghijklmnopqrstuv", None)
    assert with_id[0].embed_url == "https://www.youtube-nocookie.com/embed/videoseries?list=UUabcdefghijklmnopqrstuv"
    assert social_widgets(None, None, None, None) == []
