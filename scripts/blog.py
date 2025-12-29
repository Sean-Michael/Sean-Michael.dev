#!/usr/bin/env python3
"""Blog CLI for manipulating blog posts and images stored in S3"""

import logging
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

def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")



if __name__ == "__main__":
    main()
