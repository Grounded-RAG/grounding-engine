"""S3-compatible object storage helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings


class StorageError(RuntimeError):
    """Raised when the storage backend cannot satisfy a request."""


@dataclass(frozen=True)
class StoredObject:
    """Basic object metadata returned by storage writes."""

    bucket: str
    key: str
    etag: str | None
    size: int


@lru_cache
def get_storage_client() -> BaseClient:
    """Create and cache the S3-compatible client used by the backend."""

    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=str(settings.s3_endpoint_url),
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        use_ssl=settings.s3_secure,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def reset_storage_client() -> None:
    """Clear the cached storage client for test isolation."""

    get_storage_client.cache_clear()


def get_storage_bucket() -> str:
    """Return the configured object storage bucket name."""

    return get_settings().s3_bucket


def ensure_bucket_exists() -> None:
    """Verify that the configured bucket exists, creating it if needed."""

    client = get_storage_client()
    bucket = get_storage_bucket()

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if error_code in {"404", "NoSuchBucket", "NotFound"} or status_code == 404:
            client.create_bucket(Bucket=bucket)
            return
        raise StorageError("Object storage bucket check failed.") from exc
    except BotoCoreError as exc:
        raise StorageError("Object storage client check failed.") from exc


async def ensure_storage_ready() -> bool:
    """Confirm the storage backend is reachable and the bucket is available."""

    try:
        await asyncio.to_thread(ensure_bucket_exists)
        return True
    except (StorageError, BotoCoreError, ClientError):
        return False


async def upload_bytes(
    key: str,
    payload: bytes,
    *,
    content_type: str | None = None,
    metadata: dict[str, str] | None = None,
) -> StoredObject:
    """Upload an in-memory payload to object storage."""

    def _upload() -> StoredObject:
        client = get_storage_client()
        bucket = get_storage_bucket()
        ensure_bucket_exists()
        request: dict[str, object] = {
            "Bucket": bucket,
            "Key": key,
            "Body": payload,
        }
        if content_type is not None:
            request["ContentType"] = content_type
        if metadata is not None:
            request["Metadata"] = metadata

        response = client.put_object(**request)
        etag = response.get("ETag")
        if isinstance(etag, str):
            etag = etag.strip('"')
        else:
            etag = None
        return StoredObject(
            bucket=bucket,
            key=key,
            etag=etag,
            size=len(payload),
        )

    try:
        return await asyncio.to_thread(_upload)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to upload object to storage.") from exc


async def download_bytes(key: str) -> bytes:
    """Download an object payload from storage."""

    def _download() -> bytes:
        client = get_storage_client()
        response = client.get_object(Bucket=get_storage_bucket(), Key=key)
        body = response["Body"].read()
        if not isinstance(body, bytes):
            raise StorageError("Storage returned a non-bytes response body.")
        return body

    try:
        return await asyncio.to_thread(_download)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to download object from storage.") from exc


async def delete_object(key: str) -> None:
    """Delete an object from storage."""

    def _delete() -> None:
        client = get_storage_client()
        client.delete_object(Bucket=get_storage_bucket(), Key=key)

    try:
        await asyncio.to_thread(_delete)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Failed to delete object from storage.") from exc
