from types import SimpleNamespace

from app.config import Settings
from app.share.meta import ShareMeta, inject, render_head, share_meta

SETTINGS = Settings(env="test", public_web_url="https://prasang.in")


def _profile(**kw):
    base = dict(slug="arjun-mehta-dj", stage_name="Arjun Mehta", artist_type="dj", location_city="Mumbai",
                bio="Bollywood and house DJ for weddings.", profile_image_url="https://cdn.example.com/a.jpg")
    return SimpleNamespace(**{**base, **kw})


def test_title_format():
    assert share_meta(_profile(), SETTINGS).title == "Arjun Mehta · DJ · Mumbai"


def test_description_truncates_bio_to_160_with_ellipsis():
    meta = share_meta(_profile(bio="x" * 300), SETTINGS)
    assert len(meta.description) == 160
    assert meta.description.endswith("…")
    assert share_meta(_profile(bio="Short bio."), SETTINGS).description == "Short bio."


def test_image_falls_back_to_default():
    assert share_meta(_profile(profile_image_url=None), SETTINGS).image == "https://prasang.in/og-default.png"
    assert share_meta(_profile(profile_image_url="/artists/dj.png"), SETTINGS).image == "https://prasang.in/artists/dj.png"
    assert share_meta(_profile(), SETTINGS).image == "https://cdn.example.com/a.jpg"


def test_url_points_at_profile():
    assert share_meta(_profile(), SETTINGS).url == "https://prasang.in/profile/arjun-mehta-dj"


def test_render_escapes_hostile_name():
    head = render_head(share_meta(_profile(stage_name='"><script>alert(1)</script>'), SETTINGS))
    assert "<script>" not in head
    assert "&quot;&gt;&lt;script&gt;" in head
    assert 'property="og:type" content="profile"' in head
    assert 'name="twitter:card" content="summary_large_image"' in head


def test_inject_replaces_only_marked_block():
    page = "<html><head><meta charset=utf-8><!--og:start--><title>Generic</title><!--og:end--></head><body>x</body></html>"
    out = inject(page, render_head(ShareMeta(title="T", description="D", image="I", url="U")))
    assert "Generic" not in out
    assert out.startswith("<html><head><meta charset=utf-8><!--og:start-->")
    assert out.endswith("<!--og:end--></head><body>x</body></html>")
    assert "<title>T</title>" in out
    assert inject("<html>no markers</html>", "<title>T</title>") == "<html>no markers</html>"
