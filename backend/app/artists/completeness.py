"""Profile strength shown on the artist dashboard and onboarding."""
from app.contract import CompletenessItem, ProfileCompleteness

MIN_BIO = 50


def completeness(profile, media_count: int, review_count: int) -> ProfileCompleteness:
    basic = all([profile.stage_name, profile.artist_type, profile.location_city, profile.location_area,
                 profile.per_event_rate_max])
    items = [
        CompletenessItem(key="basic_info", label="Basic info added", done=basic),
        CompletenessItem(key="photo", label="Profile photo uploaded", done=bool(profile.profile_image_url)),
        CompletenessItem(key="bio", label="Bio written", done=len((profile.bio or "").strip()) >= MIN_BIO),
        CompletenessItem(key="media", label="Add portfolio media", done=media_count > 0),
        CompletenessItem(key="instagram", label="Connect Instagram", done=bool(profile.instagram_handle)),
        CompletenessItem(key="review", label="Get your first review", done=review_count > 0),
    ]
    return ProfileCompleteness(percent=round(100 * sum(i.done for i in items) / len(items)), items=items)
