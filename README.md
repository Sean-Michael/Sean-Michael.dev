# sean-michael.dev

My site: blog, projects, and digests. Pages are HTML files in `site/`, wrapped in a
shared layout. The only dynamic part is the digest, which comes from S3.

## Writing

Everything under `site/` maps 1:1 to a URL:

```
site/index.html                  /
site/about.html                  /about
site/blog/index.html             /blog
site/blog/mt-hood-summit.html    /blog/mt-hood-summit
site/static/style.css            /static/style.css
site/404.html                    shown for anything that doesn't exist
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
up on `/blog` and the home page on its own (htmx loads the list from `/blog/latest`).
Quote the title if it has a colon in it. Images go in `site/static/images/`.
Push to `main` and it deploys.

A file that starts with `<!doctype html>` skips the layout and is sent exactly as
written (see `site/arete/`).

`make test` checks that every internal link in `site/` resolves, so a typo'd URL
fails CI instead of going live.

## Digests

The digest automation writes markdown (YAML frontmatter with `title` and `date`)
to `s3://smr-webdev-content/digests/<slug>.md`. The app loads all of them into
memory at startup, already rendered, and checks S3 for new or changed files every
5 minutes in the background. Page views never wait on S3.

## Running locally

```sh
make dev
```

Opens on <http://127.0.0.1:8000>. Digests come from `./content/digests/`
(gitignored). `make test` runs the tests.

## How it's deployed

Push to `main` → tests + security scan → Docker image → GitHub Actions copies
`docker-compose.yaml` to the EC2 box over SSM and runs `docker compose up`.

On the box, Traefik handles TLS and routing:

- `/tides` and `/api/tides` go to the separate [BTO](https://github.com/Sean-Michael/BTO) container (Bellingham Tidal Observatory).
- Everything else goes to the app.
