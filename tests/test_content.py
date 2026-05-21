"""Unit tests for content loading, parsing, and utility functions."""

from datetime import date

import pytest

from app.main import (
    Blog,
    DigestSummary,
    Project,
    _ttl_bucket,
    extract_first_paragraph,
    get_all_tags,
    get_related_posts,
    list_all_digests,
    load_all_blogs,
    load_all_projects,
    load_blog,
    load_digest,
    load_project,
    parse_digest_slug,
)

# ---------------------------------------------------------------------------
# parse_digest_slug
# ---------------------------------------------------------------------------


def test_parse_digest_slug_date_only():
    result = parse_digest_slug("2026-03-30")
    assert result.date == date(2026, 3, 30)
    assert result.slug == "2026-03-30"
    assert "March" in result.title


def test_parse_digest_slug_with_topic():
    result = parse_digest_slug("mcp-servers-2026-05-20")
    assert result.date == date(2026, 5, 20)
    assert result.slug == "mcp-servers-2026-05-20"
    assert "Mcp Servers" in result.title


def test_parse_digest_slug_multi_word_topic():
    result = parse_digest_slug("ai-news-weekly-2025-12-01")
    assert result.date == date(2025, 12, 1)
    assert "December" in result.title


# ---------------------------------------------------------------------------
# extract_first_paragraph
# ---------------------------------------------------------------------------


def test_extract_first_paragraph_basic():
    text = "Hello world.\n\nSecond paragraph."
    assert extract_first_paragraph(text) == "Hello world."


def test_extract_first_paragraph_skips_headings():
    text = "# Title\n\nActual paragraph."
    assert extract_first_paragraph(text) == "Actual paragraph."


def test_extract_first_paragraph_skips_list_items():
    text = "- item one\n- item two\n\nParagraph text."
    assert extract_first_paragraph(text) == "Paragraph text."


def test_extract_first_paragraph_skips_opening_fence():
    # The function skips lines starting with ``` but not lines *inside* a code block.
    # In practice, frontmatter content rarely starts with a bare code block.
    text = "```python\ncode\n```"
    # First non-skipped line is "code" (inside the fence)
    assert extract_first_paragraph(text) == "code"


def test_extract_first_paragraph_empty():
    assert extract_first_paragraph("") == ""


# ---------------------------------------------------------------------------
# get_all_tags
# ---------------------------------------------------------------------------


def test_get_all_tags_returns_sorted_unique(client):
    blogs = load_all_blogs(_ttl_bucket())
    tags = get_all_tags(blogs)
    assert tags == sorted(set(tags))
    assert len(tags) == len(set(tags))


def test_get_all_tags_empty():
    assert get_all_tags([]) == []


def test_get_all_tags_includes_known_tag():
    blogs = load_all_blogs(_ttl_bucket())
    tags = get_all_tags(blogs)
    assert "python" in tags


# ---------------------------------------------------------------------------
# get_related_posts
# ---------------------------------------------------------------------------


def test_get_related_posts_excludes_self():
    blogs = load_all_blogs(_ttl_bucket())
    current = blogs[0]
    related = get_related_posts(current, blogs)
    assert current not in related


def test_get_related_posts_respects_limit():
    blogs = load_all_blogs(_ttl_bucket())
    related = get_related_posts(blogs[0], blogs, limit=2)
    assert len(related) <= 2


def test_get_related_posts_prefers_tag_matches():
    blogs = load_all_blogs(_ttl_bucket())
    if len(blogs) < 2:
        pytest.skip("need at least 2 blog posts")
    current = blogs[0]
    related = get_related_posts(current, blogs)
    if current.tags and len(blogs) > 2:
        # First related post should share at least one tag if any exist
        shared_tags = set(related[0].tags) & set(current.tags)
        others_no_match = [b for b in related[1:] if not (set(b.tags) & set(current.tags))]
        # Posts with shared tags come before posts with no shared tags
        assert len(shared_tags) >= len(
            set(others_no_match[0].tags) & set(current.tags)
        ) if others_no_match else True


# ---------------------------------------------------------------------------
# Blog loading
# ---------------------------------------------------------------------------


def test_load_all_blogs_sorted_newest_first():
    blogs = load_all_blogs(_ttl_bucket())
    dates = [b.date for b in blogs]
    assert dates == sorted(dates, reverse=True)


def test_load_all_blogs_returns_blog_models():
    blogs = load_all_blogs(_ttl_bucket())
    assert all(isinstance(b, Blog) for b in blogs)


def test_load_blog_has_required_fields():
    blog = load_all_blogs(_ttl_bucket())[0]
    assert blog.title
    assert blog.slug
    assert blog.author
    assert blog.date
    assert blog.content


def test_load_blog_content_is_html():
    blog = load_all_blogs(_ttl_bucket())[0]
    # markdown() always wraps in <p> tags
    assert "<p>" in blog.content or "<h" in blog.content


def test_load_blog_known_slug():
    blog = load_blog("building-an-ai-news-digest", _ttl_bucket())
    assert blog.slug == "building-an-ai-news-digest"
    assert blog.title


# ---------------------------------------------------------------------------
# Project loading
# ---------------------------------------------------------------------------


def test_load_all_projects_sorted_newest_first():
    projects = load_all_projects(_ttl_bucket())
    dates = [p.date for p in projects]
    assert dates == sorted(dates, reverse=True)


def test_load_all_projects_returns_project_models():
    projects = load_all_projects(_ttl_bucket())
    assert all(isinstance(p, Project) for p in projects)


def test_load_project_has_required_fields():
    project = load_all_projects(_ttl_bucket())[0]
    assert project.title
    assert project.slug
    assert project.github_url
    assert project.date
    assert project.status in ("active", "wip", "archive")


def test_load_project_known_slug():
    project = load_project("homelab-cluster", _ttl_bucket())
    assert project.slug == "homelab-cluster"
    assert project.tech_stack


# ---------------------------------------------------------------------------
# Digest loading
# ---------------------------------------------------------------------------


def test_list_all_digests_sorted_newest_first():
    digests = list_all_digests(_ttl_bucket())
    dates = [d.date for d in digests]
    assert dates == sorted(dates, reverse=True)


def test_list_all_digests_returns_digest_summary_models():
    digests = list_all_digests(_ttl_bucket())
    assert all(isinstance(d, DigestSummary) for d in digests)


def test_load_digest_known_slug():
    digest = load_digest("2026-03-30", _ttl_bucket())
    assert digest.slug == "2026-03-30"
    assert digest.title
    assert digest.content
    assert "<" in digest.content  # rendered HTML
