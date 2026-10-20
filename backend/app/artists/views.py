"""ArtistProfile ORM → contract models."""
from app.contract import ArtistCard, ArtistDetail, ArtistProfile, Media, ProfileCompleteness, SocialWidget
from app.embeds import social_widgets
from app.subscriptions.entitlements import EMBED_KINDS, for_tier


def to_media(m) -> Media:
    return Media(id=str(m.id), kind=m.kind, url=m.url, embed_url=m.embed_url, thumbnail_url=m.thumbnail_url,
                 caption=m.caption, display_order=m.display_order, is_hd=bool(m.is_hd), delete_after=m.delete_after)


def public_media(p) -> list:
    """What planners see: nothing hidden by a downgrade, and no embedded posts on plans without embeds."""
    embeds = for_tier(p.subscription_tier).social_embeds
    return [m for m in p.media if m.hidden_at is None and (embeds or m.kind not in EMBED_KINDS)]


def card_fields(p) -> dict:
    return dict(
        artist_id=str(p.id), slug=p.slug, name=p.stage_name, artist_type=p.artist_type, profile_image_url=p.profile_image_url,
        bio=p.bio, location_city=p.location_city, location_area=p.location_area, per_event_rate_min=p.per_event_rate_min,
        per_event_rate_max=p.per_event_rate_max, average_rating=float(p.average_rating or 0), total_reviews=p.total_reviews,
        is_verified=bool(p.is_verified) and for_tier(p.subscription_tier).verified_badge,  # badge only on Pro/Premium
        is_featured=p.is_featured, subscription_tier=p.subscription_tier,
        instagram_handle=p.instagram_handle, youtube_channel=p.youtube_channel, facebook_url=p.facebook_url,
        experience_years=p.experience_years, event_types_supported=list(p.event_types_supported),
        languages_spoken=list(p.languages_spoken), ready_to_travel=p.ready_to_travel,
    )


def to_card(p) -> ArtistCard:
    return ArtistCard(**card_fields(p))


def detail_fields(p) -> dict:
    widgets = social_widgets(p.instagram_handle, p.youtube_channel, p.youtube_channel_id, p.facebook_url) \
        if for_tier(p.subscription_tier).social_embeds else []  # Free: plain text links only
    return card_fields(p) | dict(
        media=[to_media(m) for m in public_media(p)],
        social_widgets=[SocialWidget(platform=w.platform, profile_url=w.profile_url, embed_url=w.embed_url) for w in widgets],
    )


def to_detail(p) -> ArtistDetail:
    return ArtistDetail(**detail_fields(p))


def to_profile(p, completeness: ProfileCompleteness) -> ArtistProfile:
    return ArtistProfile(**detail_fields(p), contact_phone=p.contact_phone, whatsapp_number=p.whatsapp_number,
                         is_published=p.is_published, completeness=completeness,
                         suspended=p.suspended_at is not None, suspension_reason=p.suspension_reason,
                         google_place_url=p.google_place_url)
