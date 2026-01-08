"""Content loader for blog posts and projects from local filesystem or S3."""

import glob
import logging
import os
from enum import Enum
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

CONTENT_SOURCE = os.getenv("CONTENT_SOURCE", "local")
S3_CONTENT_BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

BASE_DIR = Path(__file__).parent.parent


class ContentType(Enum):
    BLOG = "blog"
    PROJECT = "project"


CONTENT_CONFIG = {
    ContentType.BLOG: {
        "s3_prefix": "blog/posts/",
        "local_dir": BASE_DIR / "content" / "blog" / "posts",
    },
    ContentType.PROJECT: {
        "s3_prefix": "projects/published/",
        "local_dir": BASE_DIR / "content" / "projects" / "published",
    },
}


def get_s3_client():
    try:
        return boto3.client("s3", region_name=AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise


def list_content_files(content_type: ContentType) -> list[str]:
    config = CONTENT_CONFIG[content_type]
    if CONTENT_SOURCE == "local":
        local_dir = config["local_dir"]
        logger.debug(f"Listing local {content_type.value} files in {local_dir}")
        files = [Path(f).stem for f in glob.glob(f"{local_dir}/*.md")]
        logger.info(f"Found {len(files)} local {content_type.value} files")
        return files
    else:
        s3_prefix = config["s3_prefix"]
        logger.debug(f"Listing S3 objects in {S3_CONTENT_BUCKET}/{s3_prefix}")
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=S3_CONTENT_BUCKET, Prefix=s3_prefix)
        files = [
            Path(item["Key"]).stem
            for item in response.get("Contents", [])
            if item["Key"].endswith(".md")
        ]
        logger.info(f"Found {len(files)} {content_type.value} files in S3")
        return files


def read_content_file(content_type: ContentType, slug: str) -> str:
    config = CONTENT_CONFIG[content_type]
    if CONTENT_SOURCE == "local":
        file_path = config["local_dir"] / f"{slug}.md"
        logger.debug(f"Reading local file: {file_path}")
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    else:
        key = f"{config['s3_prefix']}{slug}.md"
        logger.debug(f"Reading S3 object: s3://{S3_CONTENT_BUCKET}/{key}")
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=S3_CONTENT_BUCKET, Key=key)
        return response["Body"].read().decode("utf-8")


def list_blog_files() -> list[str]:
    return list_content_files(ContentType.BLOG)


def read_blog_file(slug: str) -> str:
    return read_content_file(ContentType.BLOG, slug)


def list_project_files() -> list[str]:
    return list_content_files(ContentType.PROJECT)


def read_project_file(slug: str) -> str:
    return read_content_file(ContentType.PROJECT, slug)
