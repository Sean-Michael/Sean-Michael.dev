"""Read-only object storage: a local directory in dev, an S3 bucket in prod.

Keys are slash-separated paths like ``digests/my-digest.md``. Both backends
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
    def list(self, prefix: str) -> dict[str, str]:
        """Names directly under ``prefix`` (not recursive), each mapped to a version
        string that changes whenever the object does."""
        ...

    def get(self, key: str) -> bytes | None: ...


class LocalStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"key escapes store root: {key}")
        return path

    def list(self, prefix: str) -> dict[str, str]:
        d = self._path(prefix)
        if not d.is_dir():
            return {}
        return {p.name: str(p.stat().st_mtime_ns) for p in d.iterdir() if p.is_file()}

    def get(self, key: str) -> bytes | None:
        p = self._path(key)
        return p.read_bytes() if p.is_file() else None


class S3Store:
    def __init__(self, bucket: str, region: str) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        # Room for the parallel fetches the digest cache does on refresh.
        self.s3 = boto3.client("s3", region_name=region, config=Config(max_pool_connections=16))

    def list(self, prefix: str) -> dict[str, str]:
        names: dict[str, str] = {}
        paginator = self.s3.get_paginator("list_objects_v2")
        # Delimiter keeps this one level deep: "digests/" won't return "digests/drafts/x.md".
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter="/"):
            for obj in page.get("Contents", []):
                name = obj["Key"][len(prefix) :]
                if name:
                    names[name] = obj["ETag"]
        return names

    def get(self, key: str) -> bytes | None:
        try:
            return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.s3.exceptions.NoSuchKey:
            return None


def make_store() -> Store:
    if os.getenv("CONTENT_SOURCE", "local") == "s3":
        bucket = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
        logger.info("Using S3 content store: %s", bucket)
        return S3Store(bucket, os.getenv("AWS_REGION", "us-west-2"))
    root = Path(os.getenv("CONTENT_DIR", BASE_DIR / "content"))
    logger.info("Using local content store: %s", root)
    return LocalStore(root)
