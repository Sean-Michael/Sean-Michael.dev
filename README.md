# sean-michael.dev

My site: blog, projects, and digests. FastAPI renders plain HTML from markdown
stored in S3. There's no frontend build; it's one stylesheet and Jinja templates.

## Writing

Go to **<https://sean-michael.dev/admin>** and sign in with GitHub.

- **New post / project / digest**: type markdown on the left; a live preview renders on the right.
- **Save draft** (or ⌘S): saved to S3 under `…/drafts/`. Not public.
- **Publish**: moves the draft to the live prefix. It shows on the site immediately.
- **Edit a published post**: your edits save as a draft. The live version doesn't change until you
  hit **Publish changes**.
- **Unpublish**: takes it down and turns it back into a draft.
- **Images**: upload on the edit page, then paste the `![…](/images/…)` line it gives you.
  For projects, paste image URLs into the Screenshots box to get a gallery.

The S3 bucket has versioning on, so anything overwritten or deleted can be recovered.

### S3 layout

```
blog/posts/<slug>.md          blog/drafts/<slug>.md
projects/published/<slug>.md  projects/drafts/<slug>.md
digests/<slug>.md             digests/drafts/<slug>.md
images/<kind>/<slug>/<file>
```

Each file is markdown with YAML frontmatter (`title`, `date`, `tags`, `description`;
projects add `github_url`, `demo_url`, `tech_stack`, `screenshots`). Any other
frontmatter keys are kept when you edit through /admin. The digest automation can
keep writing straight to `digests/`.

## Running locally

```sh
make dev
```

Opens on <http://127.0.0.1:8000>. Content comes from `./content/` (same layout as S3,
gitignored), and `/admin` works without signing in. `make test` runs the tests.

## How it's deployed

Push to `main` → tests + security scan → Docker image → GitHub Actions copies
`docker-compose.yaml` to the EC2 box over SSM and runs `docker compose up`.

On the box, Traefik handles TLS and routing:

- `/admin/*` goes through **oauth2-proxy** (GitHub login, only users in
  `ADMIN_GITHUB_USERS`), then to the app. The app double-checks the username
  oauth2-proxy forwards.
- `/tides` and `/api/tides` go to the separate [tides](https://github.com/sean-michael/tides) container.
- Everything else goes to the app.

### One-time setup for /admin

1. Create a GitHub OAuth app (GitHub → Settings → Developer settings → OAuth Apps):
   homepage `https://sean-michael.dev`, callback `https://sean-michael.dev/oauth2/callback`.
2. Add these to `/opt/app/.env` on the EC2 box:
   ```sh
   OAUTH2_PROXY_CLIENT_ID=...
   OAUTH2_PROXY_CLIENT_SECRET=...
   OAUTH2_PROXY_COOKIE_SECRET=...   # openssl rand -base64 32 | tr -- '+/' '-_'
   ADMIN_GITHUB_USERS=sean-michael
   ```
3. Apply Terraform (`infrastructure/`) so the EC2 role can write to the bucket, not just read.
