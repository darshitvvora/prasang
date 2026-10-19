"""Object storage (Amazon S3). Browsers/apps upload directly with presigned PUT URLs."""
from datetime import UTC, datetime, timedelta
from typing import Protocol

import aioboto3
from botocore.exceptions import ClientError

from app.config import Settings, get_settings
from app.errors import AppError


class Storage(Protocol):
    async def presign_put(self, key: str, content_type: str, expires_s: int = 300) -> tuple[str, datetime]: ...
    async def exists(self, key: str) -> bool: ...
    async def delete(self, key: str) -> None: ...
    def public_url(self, key: str) -> str: ...


class S3Storage:
    def __init__(self, settings: Settings):
        self.bucket = settings.s3_bucket
        self.base_url = settings.media_base_url
        self._session = aioboto3.Session()
        self._client_kwargs = {"region_name": settings.aws_region, "endpoint_url": settings.s3_endpoint_url}

    def _client(self):
        return self._session.client("s3", **self._client_kwargs)

    async def presign_put(self, key: str, content_type: str, expires_s: int = 300) -> tuple[str, datetime]:
        async with self._client() as s3:
            url = await s3.generate_presigned_url(
                "put_object", Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type}, ExpiresIn=expires_s)
        return url, datetime.now(UTC) + timedelta(seconds=expires_s)

    async def exists(self, key: str) -> bool:
        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

    async def delete(self, key: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self.bucket, Key=key)

    def public_url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


def get_storage() -> Storage:
    settings = get_settings()
    if not settings.s3_bucket:
        raise AppError(503, "storage_not_configured",
                       "Photo and video uploads aren't set up yet. You can still add YouTube, Instagram or Facebook links.")
    return S3Storage(settings)
