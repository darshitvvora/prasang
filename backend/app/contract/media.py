from typing import Annotated, Literal

from pydantic import Field

from app.contract.common import ContractModel, MediaKind, SocialKind, UtcDatetime


class Media(ContractModel):
    id: str
    kind: MediaKind
    url: str
    embed_url: str | None
    thumbnail_url: str | None
    caption: str | None
    display_order: int
    is_hd: bool
    delete_after: UtcDatetime | None  # set when a downgrade put this item over the plan's limit


class MediaItems(ContractModel):
    items: list[Media]


class QuotaCount(ContractModel):
    used: int
    limit: int


class MediaQuota(ContractModel):
    images: QuotaCount
    videos: QuotaCount
    hd_videos: QuotaCount


class MediaListResponse(ContractModel):
    items: list[Media]
    quota: MediaQuota


class UploadUrlRequest(ContractModel):
    kind: Literal["image", "video", "avatar"]
    content_type: str
    size_bytes: int = Field(gt=0)
    hd: bool = False  # Premium: use an HD video slot (up to 200 MB)


class UploadUrlResponse(ContractModel):
    upload_url: str
    storage_key: str
    expires_at: str
    headers: dict[str, str]


class CreateMediaUploadRequest(ContractModel):
    kind: Literal["image", "video"]
    storage_key: str
    caption: str | None = None


class CreateMediaLinkRequest(ContractModel):
    kind: SocialKind
    url: str
    caption: str | None = None


CreateMediaRequest = Annotated[CreateMediaUploadRequest | CreateMediaLinkRequest, Field(discriminator="kind")]


class SetAvatarRequest(ContractModel):
    storage_key: str


class SetAvatarResponse(ContractModel):
    profile_image_url: str


class ReorderMediaRequest(ContractModel):
    ids: list[str]
