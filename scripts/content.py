#!/usr/bin/env python3
"""Content CLI for managing blog posts and projects in S3."""

import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from functools import wraps
from pathlib import Path

import click
import frontmatter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BUCKET = os.getenv("S3_CONTENT_BUCKET", "smr-webdev-content")
REGION = os.getenv("AWS_REGION", "us-west-2")
MOUNT_POINT = Path(os.getenv("CONTENT_MOUNT", Path.home() / "content"))
EDITOR = os.getenv("EDITOR", "code --wait")

BLOG_POSTS_DIR = MOUNT_POINT / "blog" / "posts"
BLOG_DRAFTS_DIR = MOUNT_POINT / "blog" / "drafts"
PROJECT_PUBLISHED_DIR = MOUNT_POINT / "projects" / "published"
PROJECT_DRAFTS_DIR = MOUNT_POINT / "projects" / "drafts"
IMAGES_DIR = MOUNT_POINT / "images"


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def is_mounted() -> bool:
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
    @wraps(f)
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        if not is_mounted():
            logger.error("Not mounted. Run: content mount")
            sys.exit(1)
        return ctx.invoke(f, *args, **kwargs)
    return wrapper


def find_content(slug: str, directory: Path) -> Path:
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


def list_content(published_dir: Path, drafts_dir: Path, show_drafts: bool, label: str):
    directory = drafts_dir if show_drafts else published_dir
    state = "Drafts" if show_drafts else label

    if not directory.exists():
        logger.info(f"No {state.lower()} found")
        return

    files = sorted(directory.glob("*.md"))
    if not files:
        logger.info(f"No {state.lower()} found")
        return

    click.echo(f"{state}:")
    for f in files:
        post = frontmatter.load(str(f))
        title = post.get("title", f.stem)
        post_date = post.get("date", "")
        raw_tags = post.metadata.get("tags", [])
        tags = raw_tags if isinstance(raw_tags, list) else []
        tag_str = f" [{', '.join(str(t) for t in tags)}]" if tags else ""
        click.echo(f"  {title} ({post_date}){tag_str}")


def publish_content(slug: str, drafts_dir: Path, published_dir: Path):
    src = find_content(slug, drafts_dir)
    published_dir.mkdir(parents=True, exist_ok=True)
    dst = published_dir / src.name
    src.rename(dst)
    logger.info(f"Published: {dst.name}")


def unpublish_content(slug: str, published_dir: Path, drafts_dir: Path):
    src = find_content(slug, published_dir)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    dst = drafts_dir / src.name
    src.rename(dst)
    logger.info(f"Unpublished: {dst.name}")


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose):
    """Manage blog posts and projects in S3."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
def mount():
    """Mount S3 bucket via s3fs."""
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
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"Mount failed: {result.stderr.strip()}")
        sys.exit(1)

    logger.info(f"Mounted at {MOUNT_POINT}")


@cli.command()
def unmount():
    """Unmount S3 bucket."""
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


@cli.command()
def status():
    """Show mount status and content counts."""
    if is_mounted():
        logger.info(f"Mounted at {MOUNT_POINT}")

        blog_posts = list(BLOG_POSTS_DIR.glob("*.md")) if BLOG_POSTS_DIR.exists() else []
        blog_drafts = list(BLOG_DRAFTS_DIR.glob("*.md")) if BLOG_DRAFTS_DIR.exists() else []
        click.echo(f"  Blog posts: {len(blog_posts)}")
        click.echo(f"  Blog drafts: {len(blog_drafts)}")

        proj_published = list(PROJECT_PUBLISHED_DIR.glob("*.md")) if PROJECT_PUBLISHED_DIR.exists() else []
        proj_drafts = list(PROJECT_DRAFTS_DIR.glob("*.md")) if PROJECT_DRAFTS_DIR.exists() else []
        click.echo(f"  Projects: {len(proj_published)}")
        click.echo(f"  Project drafts: {len(proj_drafts)}")
    else:
        logger.info("Not mounted")


@cli.command()
@require_mount
def tags():
    """List all unique tags across blogs and projects."""
    all_tags: set[str] = set()

    for directory in [BLOG_POSTS_DIR, BLOG_DRAFTS_DIR, PROJECT_PUBLISHED_DIR, PROJECT_DRAFTS_DIR]:
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


@cli.group()
def blog():
    """Manage blog posts."""
    pass


@blog.command("new")
@click.argument("title")
@require_mount
def blog_new(title):
    """Create a new blog draft."""
    slug = slugify(title)
    filepath = BLOG_DRAFTS_DIR / f"{slug}.md"

    if filepath.exists():
        logger.error(f"Draft already exists: {filepath}")
        sys.exit(1)

    BLOG_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

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


@blog.command("list")
@click.option("--drafts", is_flag=True, help="List drafts instead of posts")
@require_mount
def blog_list(drafts):
    """List blog posts or drafts."""
    list_content(BLOG_POSTS_DIR, BLOG_DRAFTS_DIR, drafts, "Posts")


@blog.command("edit")
@click.argument("slug")
@click.option("--draft", is_flag=True, help="Edit a draft")
@require_mount
def blog_edit(slug, draft):
    """Edit a blog post or draft."""
    directory = BLOG_DRAFTS_DIR if draft else BLOG_POSTS_DIR
    filepath = find_content(slug, directory)
    subprocess.run(EDITOR.split() + [str(filepath)])


@blog.command("publish")
@click.argument("slug")
@require_mount
def blog_publish(slug):
    """Move blog draft to posts."""
    publish_content(slug, BLOG_DRAFTS_DIR, BLOG_POSTS_DIR)


@blog.command("unpublish")
@click.argument("slug")
@require_mount
def blog_unpublish(slug):
    """Move blog post to drafts."""
    unpublish_content(slug, BLOG_POSTS_DIR, BLOG_DRAFTS_DIR)


@cli.group()
def project():
    """Manage projects."""
    pass


@project.command("new")
@click.argument("title")
@click.option("--github", required=True, help="GitHub repository URL")
@click.option("--demo", default=None, help="Live demo URL")
@click.option("--status", "proj_status", default="active", type=click.Choice(["active", "wip", "archived"]))
@require_mount
def project_new(title, github, demo, proj_status):
    """Create a new project draft."""
    slug = slugify(title)
    filepath = PROJECT_DRAFTS_DIR / f"{slug}.md"

    if filepath.exists():
        logger.error(f"Draft already exists: {filepath}")
        sys.exit(1)

    PROJECT_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    post = frontmatter.Post(
        content="\n",
        title=title,
        date=date.today().isoformat(),
        author="Sean-Michael",
        github_url=github,
        demo_url=demo,
        tech_stack=[],
        status=proj_status,
        tags=[],
    )
    filepath.write_text(frontmatter.dumps(post))
    logger.info(f"Created: {filepath}")

    subprocess.run(EDITOR.split() + [str(filepath)])


@project.command("list")
@click.option("--drafts", is_flag=True, help="List drafts instead of published")
@require_mount
def project_list(drafts):
    """List projects or drafts."""
    list_content(PROJECT_PUBLISHED_DIR, PROJECT_DRAFTS_DIR, drafts, "Projects")


@project.command("edit")
@click.argument("slug")
@click.option("--draft", is_flag=True, help="Edit a draft")
@require_mount
def project_edit(slug, draft):
    """Edit a project or draft."""
    directory = PROJECT_DRAFTS_DIR if draft else PROJECT_PUBLISHED_DIR
    filepath = find_content(slug, directory)
    subprocess.run(EDITOR.split() + [str(filepath)])


@project.command("publish")
@click.argument("slug")
@require_mount
def project_publish(slug):
    """Move project draft to published."""
    publish_content(slug, PROJECT_DRAFTS_DIR, PROJECT_PUBLISHED_DIR)


@project.command("unpublish")
@click.argument("slug")
@require_mount
def project_unpublish(slug):
    """Move project to drafts."""
    unpublish_content(slug, PROJECT_PUBLISHED_DIR, PROJECT_DRAFTS_DIR)


@cli.group()
def image():
    """Manage images."""
    pass


@image.command("add")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--for", "content_type", required=True, type=click.Choice(["blog", "projects"]))
@click.option("--as", "name", default=None, help="Custom filename (without extension)")
@require_mount
def image_add(filepath, content_type, name):
    """Upload an image to S3."""
    src = Path(filepath)
    dest_dir = IMAGES_DIR / content_type
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{name}{src.suffix}" if name else src.name
    dest = dest_dir / filename

    if dest.exists():
        logger.error(f"Image already exists: {dest}")
        sys.exit(1)

    shutil.copy2(src, dest)
    url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/images/{content_type}/{filename}"
    logger.info(f"Uploaded: {dest}")
    click.echo(f"URL: {url}")
    click.echo(f"Markdown: ![{src.stem}]({url})")


@image.command("list")
@click.option("--blog", "show_blog", is_flag=True, help="Show blog images only")
@click.option("--projects", "show_projects", is_flag=True, help="Show project images only")
@require_mount
def image_list(show_blog, show_projects):
    """List uploaded images."""
    if not IMAGES_DIR.exists():
        logger.info("No images found")
        return

    dirs_to_check = []
    if show_blog or (not show_blog and not show_projects):
        dirs_to_check.append(("blog", IMAGES_DIR / "blog"))
    if show_projects or (not show_blog and not show_projects):
        dirs_to_check.append(("projects", IMAGES_DIR / "projects"))

    for label, img_dir in dirs_to_check:
        if not img_dir.exists():
            continue
        images = list(img_dir.glob("*"))
        images = [i for i in images if i.is_file()]
        if images:
            click.echo(f"{label.capitalize()} images:")
            for img in sorted(images):
                url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/images/{label}/{img.name}"
                click.echo(f"  {img.name}")
                click.echo(f"    {url}")


if __name__ == "__main__":
    cli()
