#!/usr/bin/env python3
"""Blog CLI for managing markdown posts in S3."""

import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import click
import frontmatter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
REGION = os.getenv("AWS_REGION", "us-west-2")
MOUNT_POINT = Path(os.getenv("BLOG_MOUNT", Path.home() / "blog"))
EDITOR = os.getenv("EDITOR", "code --wait")

POSTS_DIR = MOUNT_POINT / "blog" / "posts"
DRAFTS_DIR = MOUNT_POINT / "blog" / "drafts"


def slugify(title: str) -> str:
    """Convert title to URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def is_mounted() -> bool:
    """Check if S3 bucket is mounted."""
    try:
        result = subprocess.run(
            ["mountpoint", "-q", str(MOUNT_POINT)],
            capture_output=True,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug(f"mountpoint check failed: {e}")
        return False


def require_mount(f):
    """Decorator to ensure bucket is mounted before running command."""
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        if not is_mounted():
            logger.error("Not mounted. Run: blog mount")
            sys.exit(1)
        return ctx.invoke(f, *args, **kwargs)
    return wrapper


def find_post(slug: str, directory: Path) -> Path:
    """Find a post by exact slug or fuzzy match."""
    filepath = directory / f"{slug}.md"
    if filepath.exists():
        return filepath

    matches = [f for f in directory.glob("*.md") if slug in f.stem]
    if len(matches) == 1:
        logger.info(f"Matched: {matches[0].stem}")
        return matches[0]
    elif len(matches) > 1:
        logger.error(f"Multiple matches: {[m.stem for m in matches]}")
        sys.exit(1)
    else:
        logger.error(f"Not found: {slug}")
        sys.exit(1)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose):
    """Manage blog posts in S3."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
def mount():
    """Mount S3 bucket via s3fs."""
    try:
        if is_mounted():
            logger.info(f"Already mounted at {MOUNT_POINT}")
            return

        if not shutil.which("s3fs"):
            logger.error("s3fs not found. Run: sudo apt install s3fs")
            sys.exit(1)

        passwd_file = Path.home() / ".passwd-s3fs"
        if not passwd_file.exists():
            logger.error(f"{passwd_file} not found")
            sys.exit(1)

        MOUNT_POINT.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                "s3fs", BUCKET, str(MOUNT_POINT),
                "-o", f"passwd_file={passwd_file}",
                "-o", f"url=https://s3.{REGION}.amazonaws.com",
                "-o", "use_path_request_style",
                "-o", "allow_other",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Mount failed: {result.stderr.strip()}")
            sys.exit(1)

        logger.info(f"Mounted at {MOUNT_POINT}")

    except Exception as e:
        logger.error(f"Mount failed: {e}")
        sys.exit(1)


@cli.command()
def unmount():
    """Unmount S3 bucket."""
    try:
        if not is_mounted():
            logger.info("Not mounted")
            return

        result = subprocess.run(
            ["fusermount", "-u", str(MOUNT_POINT)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Unmount failed: {result.stderr.strip()}")
            sys.exit(1)

        logger.info(f"Unmounted {MOUNT_POINT}")

    except Exception as e:
        logger.error(f"Unmount failed: {e}")
        sys.exit(1)


@cli.command()
def status():
    """Show mount status."""
    try:
        if is_mounted():
            logger.info(f"Mounted at {MOUNT_POINT}")
            posts = list(POSTS_DIR.glob("*.md")) if POSTS_DIR.exists() else []
            drafts = list(DRAFTS_DIR.glob("*.md")) if DRAFTS_DIR.exists() else []
            click.echo(f"  Posts: {len(posts)}")
            click.echo(f"  Drafts: {len(drafts)}")
        else:
            logger.info("Not mounted")
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        sys.exit(1)


@cli.command("list")
@click.option("--drafts", is_flag=True, help="List drafts instead of posts")
@require_mount
def list_posts(drafts):
    """List posts or drafts."""
    try:
        directory = DRAFTS_DIR if drafts else POSTS_DIR
        label = "Drafts" if drafts else "Posts"

        if not directory.exists():
            logger.info(f"No {label.lower()} found")
            return

        files = sorted(directory.glob("*.md"))
        if not files:
            logger.info(f"No {label.lower()} found")
            return

        click.echo(f"{label}:")
        for f in files:
            post = frontmatter.load(str(f))
            title = post.get("title", f.stem)
            post_date = post.get("date", "")
            raw_tags = post.metadata.get("tags", [])
            tags = raw_tags if isinstance(raw_tags, list) else []
            tag_str = f" [{', '.join(str(t) for t in tags)}]" if tags else ""
            click.echo(f"  {title} ({post_date}){tag_str}")

    except Exception as e:
        logger.error(f"List failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("title")
@require_mount
def new(title):
    """Create a new draft post."""
    try:
        slug = slugify(title)
        filepath = DRAFTS_DIR / f"{slug}.md"

        if filepath.exists():
            logger.error(f"Draft already exists: {filepath}")
            sys.exit(1)

        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

        post = frontmatter.Post(
            content="\n",
            title=title,
            date=date.today().isoformat(),
            author="Sean-Michael",
            tags=[],
        )
        filepath.write_text(frontmatter.dumps(post))
        logger.info(f"Created: {filepath}")

        subprocess.run(EDITOR.split() + [str(filepath)])

    except Exception as e:
        logger.error(f"Create failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("slug")
@click.option("--draft", is_flag=True, help="Edit a draft")
@require_mount
def edit(slug, draft):
    """Edit a post or draft."""
    try:
        directory = DRAFTS_DIR if draft else POSTS_DIR
        filepath = find_post(slug, directory)
        subprocess.run(EDITOR.split() + [str(filepath)])
    except Exception as e:
        logger.error(f"Edit failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("slug")
@require_mount
def publish(slug):
    """Move draft to posts (publish)."""
    try:
        src = find_post(slug, DRAFTS_DIR)
        POSTS_DIR.mkdir(parents=True, exist_ok=True)
        dst = POSTS_DIR / src.name
        src.rename(dst)
        logger.info(f"Published: {dst.name}")
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("slug")
@require_mount
def unpublish(slug):
    """Move post to drafts (unpublish)."""
    try:
        src = find_post(slug, POSTS_DIR)
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        dst = DRAFTS_DIR / src.name
        src.rename(dst)
        logger.info(f"Unpublished: {dst.name}")
    except Exception as e:
        logger.error(f"Unpublish failed: {e}")
        sys.exit(1)


@cli.command()
@require_mount
def tags():
    """List all unique tags."""
    try:
        all_tags: set[str] = set()

        for directory in [POSTS_DIR, DRAFTS_DIR]:
            if not directory.exists():
                continue
            for f in directory.glob("*.md"):
                post = frontmatter.load(str(f))
                raw_tags = post.metadata.get("tags", [])
                if isinstance(raw_tags, list):
                    all_tags.update(str(t) for t in raw_tags)

        if all_tags:
            click.echo("Tags:")
            for tag in sorted(all_tags):
                click.echo(f"  {tag}")
        else:
            logger.info("No tags found")

    except Exception as e:
        logger.error(f"Tags failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
