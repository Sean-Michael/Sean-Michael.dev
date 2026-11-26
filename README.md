# sean-michael.dev

My site: blog, projects, and digests. Pages are HTML files in `site/`, wrapped in a
shared layout and built into plain files for GitHub Pages. Digests come from S3.

## Writing

Everything under `site/` maps 1:1 to a URL:

```
site/index.html                  /
site/about.html                  /about
site/blog/index.html             /blog
site/blog/mt-hood-summit.html    /blog/mt-hood-summit
site/static/style.css            /static/style.css
site/404.html                    shown for anything that doesn't exist
(generated)                      /digest, /digest/<slug>, /sitemap.xml, /robots.txt
```

Pages contain only their own content. The header, nav and footer live once in
`app/templates/base.html`.

To write a post, create `site/blog/<slug>.html`:

```html
---
title: "My new post"
date: 2026-10-22
description: "One line for search results and link previews."
tags: [climbing]
---
<p>Any HTML you want. Add a <style> block for per-post CSS.</p>
```

That's it: the title, date and read time are added at the top, and the post shows
up on `/blog` and the home page on its own (the build fills in any `<!-- posts -->`
or `<!-- posts:5 -->` marker with the list).
Quote the title if it has a colon in it.

Images live in S3, not git. `./image.sh ~/Pictures/IMG_1234.JPG baker-summit` uploads
to `s3://smr-webdev-content/images/baker-summit.jpg` and copies
`<img src="/images/baker-summit.jpg" alt="">` to the clipboard. The build points
`/images/` at the bucket, and the deploy fails if a page uses an image S3 won't serve.
Push to `main` and it deploys.

A file that starts with `<!doctype html>` skips the layout and is sent exactly as
written (see `site/arete/`).

`make test` checks that every internal link in `site/` resolves, so a typo'd URL
fails CI instead of going live.

## Digests

[ai-newstand](https://github.com/Sean-Michael/ai-newstand) writes markdown (YAML
frontmatter with `title` and `date`) to `s3://smr-webdev-content/digests/<slug>.md`,
then sends a `digest-published` repository_dispatch to this repo, which rebuilds the
site. A digest that won't parse is logged and skipped so it can't block deploys.

## Running locally

```sh
make dev
```

Builds into `dist/` and serves it on <http://127.0.0.1:8000>, mapping `/about` to
`about.html` the way GitHub Pages does. Run `make build` again after editing. Digests
come from `./content/digests/` (gitignored). `make test` runs the tests.

## How it's deployed

`.github/workflows/deploy.yaml` runs on a push to `main`, on a `digest-published`
dispatch from ai-newstand, and weekly as a backstop. It runs the tests, syncs
`digests/` down from S3, runs `python -m app.build`, and publishes `dist/` to GitHub
Pages. DNS (Squarespace) points `sean-michael.dev` at GitHub Pages.
