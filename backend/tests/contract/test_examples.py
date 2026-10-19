"""Every JSON example in contracts/examples must parse into its Pydantic contract model with no extra keys."""
import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app import contract as C

EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"

# example path (relative to contracts/examples) -> contract type
TABLE: dict[str, object] = {
    "auth/providers.response.json": C.AuthProvidersResponse,
    "site/info.response.json": C.SiteInfo,
    "site/contact.request.json": C.ContactRequest,
    "site/contact.response.json": C.ContactResponse,
    "me/get.response.json": C.Me,
    "me/post.request.json": C.CreateMeRequest,
    "me/post.response.json": C.Me,
    "me/patch.request.json": C.UpdateMeRequest,
    "locations/get.response.json": C.LocationsResponse,
    "search/artists.response.json": C.SearchResponse,
    "search/suggestions.response.json": C.SuggestionsResponse,
    "artists/featured.response.json": C.ArtistCardList,
    "artists/detail.response.json": C.ArtistDetail,
    "artists/reviews.response.json": C.ReviewPage,
    "artists/similar.response.json": C.ArtistCardList,
    "artists/post.request.json": C.ArtistProfileInput,
    "artists/me.response.json": C.ArtistProfile,
    "artists/patch.request.json": C.ArtistProfilePatch,
    "artists/dashboard.response.json": C.ArtistDashboard,
    "media/list.response.json": C.MediaListResponse,
    "media/upload-url.request.json": C.UploadUrlRequest,
    "media/upload-url.response.json": C.UploadUrlResponse,
    "media/create.request.json": C.CreateMediaRequest,
    "media/create-youtube.request.json": C.CreateMediaRequest,
    "media/create-facebook.request.json": C.CreateMediaRequest,
    "media/create.response.json": C.Media,
    "media/create-youtube.response.json": C.Media,
    "media/avatar.request.json": C.SetAvatarRequest,
    "media/avatar.response.json": C.SetAvatarResponse,
    "media/order.request.json": C.ReorderMediaRequest,
    "media/order.response.json": C.MediaItems,
    "leads/post.request.json": C.CreateLeadRequest,
    "leads/post.response.json": C.CreateLeadResponse,
    "leads/artist.response.json": C.ArtistLeadsResponse,
    "leads/patch.request.json": C.UpdateLeadRequest,
    "leads/patch.response.json": C.ArtistLead,
    "leads/planner.response.json": C.PlannerInquiriesResponse,
    "subscriptions/plans.response.json": C.PlanList,
    "subscriptions/me.response.json": C.MySubscriptionResponse,
    "subscriptions/trial.request.json": C.StartTrialRequest,
    "subscriptions/trial.response.json": C.PlanUsage,
    "subscriptions/post.request.json": C.CreateSubscriptionRequest,
    "subscriptions/post.response.json": C.CreateSubscriptionResponse,
    "subscriptions/verify.request.json": C.VerifyPaymentRequest,
    "subscriptions/verify.response.json": C.VerifyPaymentResponse,
    "subscriptions/cancel.response.json": C.MySubscriptionResponse,
    "subscriptions/webhook.request.json": C.RazorpayWebhookEvent,
    "errors/validation_error.json": C.ErrorBody,
    "errors/artist_not_found.json": C.ErrorBody,
    "errors/unauthenticated.json": C.ErrorBody,
    "errors/profile_required.json": C.ErrorBody,
    "errors/media_quota_exceeded.json": C.ErrorBody,
    "errors/lead_rate_limited.json": C.ErrorBody,
}


def test_every_example_is_covered():
    on_disk = {str(p.relative_to(EXAMPLES)) for p in EXAMPLES.rglob("*.json")}
    assert on_disk == set(TABLE), f"unmapped: {on_disk - set(TABLE)}; missing: {set(TABLE) - on_disk}"


@pytest.mark.parametrize("path", sorted(TABLE))
def test_example_matches_contract(path):
    data = json.loads((EXAMPLES / path).read_text())
    TypeAdapter(TABLE[path]).validate_python(data)


def test_serialisation_round_trips_to_camel_case():
    data = json.loads((EXAMPLES / "artists/detail.response.json").read_text())
    model = C.ArtistDetail.model_validate(data)
    assert model.model_dump(by_alias=True, mode="json") == data


def test_strict_mode_rejects_unknown_keys():
    data = json.loads((EXAMPLES / "me/get.response.json").read_text()) | {"hacker": True}
    with pytest.raises(ValidationError):
        TypeAdapter(C.Me).validate_python(data)


def test_enum_values_are_validated():
    data = json.loads((EXAMPLES / "artists/detail.response.json").read_text()) | {"artistType": "juggler"}
    with pytest.raises(ValidationError):
        C.ArtistDetail.model_validate(data)


def test_timestamps_serialise_as_utc_z():
    from datetime import datetime, timedelta, timezone

    me = C.Me(id="u", email=None, full_name="A", phone=None, role="planner", avatar_url=None, artist_slug=None,
              created_at=datetime(2026, 10, 19, 15, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))))
    assert me.model_dump(by_alias=True, mode="json")["createdAt"] == "2026-10-19T10:00:00Z"
