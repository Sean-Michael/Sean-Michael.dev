# UI/UX Review — Sean-Michael.dev

**Date:** 2026-05-20  
**Reviewer:** Claude (via full template + CSS audit)  
**Method:** Read all templates and `style.css` end-to-end; cross-referenced CSS class names against HTML usage to find mismatches and missing implementations.

---

## Process

1. Read every template (`index.html`, `base.html`, `blog_detail.html`, `project_detail.html`, `digest_index.html`, `digest_detail.html`, `about.html`, `projects_index.html`) and `app/static/style.css` in full.
2. Built a map of every CSS class *defined* vs every CSS class *used in templates*.
3. Identified classes used in templates that have no CSS definition (dead references) and CSS rules that had no corresponding HTML (unused but intended).
4. Checked DOM ordering against CSS conventions (e.g. `border-bottom` on `.hcr-tabs` implies it should sit *above* content, not below).
5. Checked the server-side data pipeline (`app/main.py`) for fields the design expected but weren't being computed (read-time, TOC).

---

## Gaps Found and Fixed

### 1. Homepage slab layout broken (CRITICAL)
**File:** `app/templates/index.html`  
**Problem:** The three-column slab section (Selected Work / Writing / Currently) used `.gs-cols` and `.gs-col` as container classes. Neither exists in `style.css`. The CSS has `.gs-slab-grid` (`grid-template-columns: 1.5fr 1fr; gap: 56px`) but the template never used it. All three sections stacked vertically.  
**Fix:** Replaced `.gs-cols` with `.gs-slab-grid`. Wrapped the Writing and Currently sections in a single right-column `div` (with `display:flex; flex-direction:column; gap:32px`) so the two-column grid correctly hosts Selected Work on the left (1.5fr) and Writing + Currently stacked on the right (1fr).

---

### 2. Carousel tabs rendered below widgets (CRITICAL)
**File:** `app/templates/index.html`  
**Problem:** In the DOM, `<div class="hcr-content">` (the widget panels) appeared *before* `<div class="hcr-tabs">`. The CSS defines `border-bottom` on `.hcr-tabs` — a clear signal it was designed to sit above the content. Visually, the tab strip appeared below all five widgets.  
**Fix:** Moved the `hcr-tabs` block above `hcr-content` in the DOM. The JavaScript carousel uses `data-idx` attributes to link tabs to widgets by index, so DOM reordering does not affect interactivity.

---

### 3. Blog article missing read-time estimate (MEDIUM)
**Files:** `app/main.py`, `app/templates/blog_detail.html`  
**Problem:** The CSS defined `.pg-article-read` for a read-time span in the article meta row, but no read-time was computed or rendered anywhere.  
**Fix:**  
- Added `read_time: int = 0` field to the `Blog` Pydantic model.  
- In `load_blog`, count raw markdown words (`len(post.content.split())`), divide by 200 wpm, round to nearest minute (minimum 1). Result cached with the blog via `lru_cache`.  
- Added `· {{ blog.read_time }} min read` to the `pg-article-meta` row in `blog_detail.html`.

---

### 4. Blog article missing Table of Contents (MEDIUM)
**Files:** `app/main.py`, `app/templates/blog_detail.html`  
**Problem:** The CSS had full `.pg-toc` styling (sticky rail widget, active-state highlighting, left-border indicator) but no TOC was ever rendered. The article rail only showed Share and Related.  
**Fix:**  
- Added `toc: list[dict] = []` field to `Blog`.  
- Switched from `markdown.markdown(...)` to `markdown.Markdown(extensions=["toc"])` in `load_blog`. The `toc` extension automatically adds `id` attributes to headings in the rendered HTML and exposes `md.toc_tokens` (a nested list of `{level, id, name, children}`).  
- Added `_flatten_toc()` helper to recursively flatten the token tree into a flat list of `{id, title, level}` dicts (capped at H3).  
- Rendered a CONTENTS widget at the top of the article rail in `blog_detail.html`, shown only when `blog.toc` is non-empty. H3 entries get `padding-left: 20px` for visual nesting.

---

### 5. Digest index: wrong arrow class (MEDIUM)
**File:** `app/templates/digest_index.html`  
**Problem:** Each digest row (`dg-row`) had an arrow `div` using class `pg-post-card-arrow`. The hover reveal (`opacity: 0 → 1`) is defined on `.dg-row:hover .dg-row-arrow`, so the wrong class meant the arrow never appeared on hover.  
**Fix:** Changed `pg-post-card-arrow` → `dg-row-arrow`.

---

### 6. Project detail: action buttons unstyled (MEDIUM)
**File:** `app/templates/project_detail.html`  
**Problem:** The GitHub and Live demo links in `pg-proj-actions` used class `pg-proj-action`, which has no CSS definition. The design system has a full button system: `pg-btn` (base), `pg-btn-primary` (filled, high-contrast), `pg-btn-ghost` (outlined).  
**Fix:** Changed GitHub link to `class="pg-btn pg-btn-primary"` and Live demo link to `class="pg-btn pg-btn-ghost"`. Added `<span class="pg-btn-arrow">↗</span>` inside each for the hover-translate arrow animation.

---

## Files Changed

| File | Change |
|------|--------|
| `app/main.py` | Added `read_time`/`toc` to `Blog`; updated `load_blog` to use `toc` extension; added `_flatten_toc` helper |
| `app/templates/index.html` | Fixed slab grid class; moved carousel tabs above content |
| `app/templates/blog_detail.html` | Added read-time to meta; added TOC rail widget |
| `app/templates/digest_index.html` | Fixed digest row arrow class |
| `app/templates/project_detail.html` | Fixed action button classes |

All 65 tests pass after changes.
