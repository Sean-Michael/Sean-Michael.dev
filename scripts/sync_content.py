#!/usr/bin/env python3
"""Sync local content/ directory to S3 bucket."""

import argparse
import logging
import mimetypes
import os
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# Configuration
S3_CONTENT_BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

BASE_DIR = Path(__file__).parent.parent
CONTENT_DIR = BASE_DIR / "content"


def get_s3_client():
    try:
        return boto3.client("s3", region_name=AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise


def sync_to_s3(dry_run: bool = False):
    s3 = get_s3_client()

    if not CONTENT_DIR.exists():
        logger.error(f"Content directory not found: {CONTENT_DIR}")
        return

    files_synced = 0

    for file_path in CONTENT_DIR.rglob("*"):
        if file_path.is_dir():
            continue

        if any(part.startswith(".") for part in file_path.parts):
            continue

        s3_key = str(file_path.relative_to(CONTENT_DIR))

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"

        if dry_run:
            logger.info(f"[DRY RUN] Would upload: {file_path} -> s3://{S3_CONTENT_BUCKET}/{s3_key}")
        else:
            logger.info(f"Uploading: {file_path} -> s3://{S3_CONTENT_BUCKET}/{s3_key}")
            s3.upload_file(
                str(file_path),
                S3_CONTENT_BUCKET,
                s3_key,
                ExtraArgs={"ContentType": content_type},
            )

        files_synced += 1

    action = "Would sync" if dry_run else "Synced"
    logger.info(f"{action} {files_synced} files to s3://{S3_CONTENT_BUCKET}/")


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Sync content to S3")
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be uploaded without actually uploading",
    )
    args = parser.parse_args()

    sync_to_s3(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
