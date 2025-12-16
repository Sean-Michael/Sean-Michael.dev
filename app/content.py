"""
Content loader that abstracts reading blog posts from local filesystem or S3.

Environment variables:
    CONTENT_SOURCE: "local" or "s3" (default: "local")
    S3_CONTENT_BUCKET: bucket name when using S3
    AWS_REGION: AWS region for S3
"""

import os
from pathlib import Path
import boto3
import glob
import logging


# Configuration from environment
CONTENT_SOURCE = os.getenv("CONTENT_SOURCE", "local")
S3_CONTENT_BUCKET = os.getenv("S3_CONTENT_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# Local paths
BASE_DIR = Path(__file__).parent.parent
LOCAL_CONTENT_DIR = BASE_DIR / "content" / "blog"


def get_s3_client():
    try:
        s3 = boto3.client('s3')
        return s3
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


def list_blog_files() -> list[str]:
    if CONTENT_SOURCE == "local":
        try:
            print(f"Listing all .md files in {LOCAL_CONTENT_DIR}...")
            all_blog_files = [Path(f).stem for f in glob.glob(f"{LOCAL_CONTENT_DIR}/*.md")]
            print(f"Found {len(all_blog_files)} files in local dir.")
            return all_blog_files
        except Exception as e:
            print(f"Error: {e}")
            exit(1)
    else:
        s3_client = get_s3_client()
        print(f"Listing objects in bucket: {S3_CONTENT_BUCKET}...")
        try:
            response = s3_client.list_objects_v2(Bucket=S3_CONTENT_BUCKET)
            blog_files=[Path(item['Key']).stem for item in response.get('Contents',[]) 
                        if item['Key'].startswith('blog/') and item['Key'].endswith('.md')]
            print(f"Found {len(blog_files)} files in bucket.")
            return blog_files
        except Exception as e:
            print(f"Error: {e}")
            exit(1)


def read_blog_file(slug: str) -> str:

    if CONTENT_SOURCE == "local":
        try:
            with open(f"{LOCAL_CONTENT_DIR}/{slug}.md", 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error: {e}")
            return 'No Content'
    else:
        s3_client=get_s3_client()
        try:
            response = s3_client.get_object(Bucket=S3_CONTENT_BUCKET, Key=f"blog/{slug}.md")
            blog_content = response.get("Body").read().decode("utf-8")
            return blog_content
        except Exception as e:
            print(f"Error: {e}")
            return 'No Content'

