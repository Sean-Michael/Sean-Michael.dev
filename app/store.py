"""Key/value object storage: a local directory in dev, an S3 bucket in prod.

Keys are slash-separated paths like ``blog/posts/my-post.md``. Both backends
behave the same so the rest of the app never cares which one is active.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent


class Store(Protocol):
    def list(self, prefix: str) -> list[str]:
        """Names directly under ``prefix`` (not recursive), e.g. ``my-post.md``."""
        ...

    def get(self, key: str) -> bytes | None: ...

    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def delete(self, key: str) -> None: ...


class LocalStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"key escapes store root: {key}")
        return path

    def list(self, prefix: str) -> list[str]:
        d = self._path(prefix)
        if not d.is_dir():
            return []
        return sorted(p.name for p in d.iterdir() if p.is_file())

    def get(self, key: str) -> bytes | None:
        p = self._path(key)
        return p.read_bytes() if p.is_file() else None

    def put(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Store:
    def __init__(self, bucket: str, region: str) -> None:
        import boto3

        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)

    def list(self, prefix: str) -> list[str]:
        names: list[str] = []
        paginator = self.s3.get_paginator("list_objects_v2")
        # Delimiter keeps this one level deep: "digests/" won't return "digests/drafts/x.md".
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter="/"):
            names += [obj["Key"][len(prefix) :] for obj in page.get("Contents", [])]
        return sorted(n for n in names if n)

    def get(self, key: str) -> bytes | None:
        try:
            return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.s3.exceptions.NoSuchKey:
            return None

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)


def make_store() -> Store:
    if os.getenv("CONTENT_SOURCE", "local") == "s3":
        bucket = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
        logger.info("Using S3 content store: %s", bucket)
        return S3Store(bucket, os.getenv("AWS_REGION", "us-west-2"))
    root = Path(os.getenv("CONTENT_DIR", BASE_DIR / "content"))
    logger.info("Using local content store: %s", root)
    return LocalStore(root)
