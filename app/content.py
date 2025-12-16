"""Content loader for blog posts from local filesystem or S3."""

import glob
import logging
import os
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# Configuration
CONTENT_SOURCE = os.getenv("CONTENT_SOURCE", "local")
S3_CONTENT_BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

BASE_DIR = Path(__file__).parent.parent
LOCAL_CONTENT_DIR = BASE_DIR / "content" / "blog"


def get_s3_client():
    try:
        return boto3.client("s3", region_name=AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise


def list_blog_files() -> list[str]:
    if CONTENT_SOURCE == "local":
        logger.debug(f"Listing local files in {LOCAL_CONTENT_DIR}")
        all_blog_files = [Path(f).stem for f in glob.glob(f"{LOCAL_CONTENT_DIR}/*.md")]
        logger.info(f"Found {len(all_blog_files)} local blog files")
        return all_blog_files
    else:
        logger.debug(f"Listing S3 objects in {S3_CONTENT_BUCKET}")
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=S3_CONTENT_BUCKET, Prefix="blog/")
        blog_files = [
            Path(item["Key"]).stem
            for item in response.get("Contents", [])
            if item["Key"].endswith(".md")
        ]
        logger.info(f"Found {len(blog_files)} blog files in S3")
        return blog_files


def read_blog_file(slug: str) -> str:
    if CONTENT_SOURCE == "local":
        file_path = LOCAL_CONTENT_DIR / f"{slug}.md"
        logger.debug(f"Reading local file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        key = f"blog/{slug}.md"
        logger.debug(f"Reading S3 object: s3://{S3_CONTENT_BUCKET}/{key}")
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=S3_CONTENT_BUCKET, Key=key)
        return response["Body"].read().decode("utf-8")

