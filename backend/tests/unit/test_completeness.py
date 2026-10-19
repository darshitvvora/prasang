from types import SimpleNamespace

from app.artists.completeness import completeness


def _p(**kw):
    base = dict(stage_name="A", artist_type="dj", location_city="Mumbai", location_area="Juhu", per_event_rate_min=1, per_event_rate_max=2,
                profile_image_url=None, bio="", instagram_handle=None)
    return SimpleNamespace(**(base | kw))


def test_empty_profile_has_only_basic_info():
    c = completeness(_p(), media_count=0, review_count=0)
    assert c.percent == 17
    assert [i.key for i in c.items if i.done] == ["basic_info"]


def test_full_profile():
    c = completeness(_p(profile_image_url="/x.png", bio="x" * 60, instagram_handle="a"), media_count=2, review_count=1)
    assert c.percent == 100


def test_short_bio_does_not_count():
    c = completeness(_p(bio="Short bio"), media_count=0, review_count=0)
    assert not next(i for i in c.items if i.key == "bio").done
