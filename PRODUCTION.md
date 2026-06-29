# SmartApply — Production Launch Guide

## Table of Contents

1. [Architecture Snapshot](#1-architecture-snapshot)
2. [Decision Matrix: Where Everything Lives](#2-decision-matrix-where-everything-lives)
3. [Database: Neon Serverless PostgreSQL](#3-database-neon-serverless-postgresql)
4. [Resume Storage: Cloudflare R2](#4-resume-storage-cloudflare-r2)
5. [Backend Hosting: Render Free Tier](#5-backend-hosting-render-free-tier)
6. [Secret Management](#6-secret-management)
7. [LLM Scaling Strategy](#7-llm-scaling-strategy)
8. [Building and Packaging the Extension](#8-building-and-packaging-the-extension)
9. [Google Cloud Console: Production Setup](#9-google-cloud-console-production-setup)
10. [Chrome Web Store Submission](#10-chrome-web-store-submission)
11. [Monitoring and Error Tracking](#11-monitoring-and-error-tracking)
12. [Security Hardening Checklist](#12-security-hardening-checklist)
13. [Post-Launch Runbook](#13-post-launch-runbook)

---

## 1. Architecture Snapshot

```
LinkedIn page (user's browser)
  └─ Content Script (TypeScript)   →  extracts visible DOM text only
        ↓ chrome.runtime.sendMessage
  Service Worker (MV3)
        ↓ HTTPS
  FastAPI backend  (Render — free tier)
        ├─ Auth:    Google OAuth 2.0 + JWT RS256
        ├─ AI:      Gemini 2.0 Flash (primary) → Groq LLaMA (fallback)
        ├─ Gmail:   gmail.send on behalf of the user
        ├─ DB:      PostgreSQL on Neon (serverless, free)
        └─ Files:   PDF resumes on Cloudflare R2 (free)
```

Zero LinkedIn server requests. Zero scraping. The content script reads only what
the user is already looking at.

---

## 2. Decision Matrix: Where Everything Lives

| Concern | Choice | Monthly cost | Free tier limit |
|---|---|---|---|
| Backend hosting | Render (Web Service) | $0 | 750 hours/month; sleeps after 15 min idle |
| PostgreSQL | Neon (Serverless) | $0 | 0.5 GB storage, 190 compute hours |
| Resume files | Cloudflare R2 | $0 | 10 GB storage, 10 M Class-B reads |
| AI — primary | Gemini 2.0 Flash | $0 | 15 RPM, 1 M tokens/day |
| AI — fallback | Groq (LLaMA 3.3 70B) | $0 | 30 RPM, 14 400 req/day |
| Error tracking | Sentry | $0 | 5 000 errors/month |
| Uptime pings | UptimeRobot | $0 | 50 monitors, 5-min interval |
| Logs | Render → Papertrail | $0 | 50 MB/day, 7-day retention |
| Chrome Web Store | One-time dev fee | **$5 once** | — |

**Total recurring cost at launch: $0/month.** You hit a real cost event only
when Neon storage or R2 egress exceeds limits — that requires thousands of
active users.

---

## 3. Database: Neon Serverless PostgreSQL

Neon is serverless PostgreSQL that scales compute to zero between requests
(no idle cost), is wire-compatible with `asyncpg`, and the free tier covers
thousands of users given this schema's size.

### Step 1 — Create a project

Go to https://console.neon.tech, sign in with GitHub, and create a project
named `smartapply`. Pick the region closest to your Render deployment.
Neon creates a default database `neondb` with owner `neondb_owner`.

### Step 2 — Get the connection string

In the Neon dashboard → Connection Details → select the **Pooled** connection
(PgBouncer). Copy and adapt it for SQLAlchemy's asyncpg dialect:

```
# What Neon shows:
postgresql://neondb_owner:<password>@<host>-pooler.neon.tech/neondb?sslmode=require

# What you set as DATABASE_URL (note +asyncpg and ssl= not sslmode=):
postgresql+asyncpg://neondb_owner:<password>@<host>-pooler.neon.tech/neondb?ssl=require
```

### Step 3 — Verify locally

```bash
DATABASE_URL="postgresql+asyncpg://..." \
  python -c "
import asyncio, sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
async def test():
    e = create_async_engine('$(echo $DATABASE_URL)')
    async with e.connect() as c:
        r = await c.execute(sqlalchemy.text('SELECT 1'))
        print('OK', r.one())
asyncio.run(test())
"
```

Alembic runs automatically at startup via `start.sh` → `alembic upgrade head`.
No manual migration step needed after the first deploy.

---

## 4. Resume Storage: Cloudflare R2

The current `LocalResumeStorage` writes to the container filesystem. On
Render's free tier the filesystem is **ephemeral** — a redeploy wipes every
uploaded file. R2 fixes this: S3-compatible, zero egress fees, 10 GB free.

### Step 1 — Create a bucket

Cloudflare dashboard → R2 Object Storage → Create bucket → name it
`smartapply-resumes`.

### Step 2 — Create API credentials

R2 settings → Manage R2 API Tokens → Create token with
**Object Read & Write** scoped to `smartapply-resumes`. Save the
Access Key ID and Secret Access Key.

### Step 3 — Add dependencies

```toml
# pyproject.toml
aioboto3 = ">=13.0"
```

### Step 4 — Implement `R2ResumeStorage`

Create `backend/app/infrastructure/storage/r2_storage.py` implementing the
existing `IResumeStorage` interface (`save`, `get`, `delete`). Use `aioboto3`
with `endpoint_url = https://<account_id>.r2.cloudflarestorage.com`.

### Step 5 — Config + DI wiring

Add to `Settings` in `config.py`:

```python
RESUME_STORAGE_BACKEND: Literal["local", "r2"] = "local"
R2_ACCOUNT_ID: str | None = None
R2_ACCESS_KEY_ID: str | None = None
R2_SECRET_ACCESS_KEY: str | None = None
R2_BUCKET_NAME: str = "smartapply-resumes"
```

In `dependencies.py`, branch `get_resume_storage()` on
`settings.RESUME_STORAGE_BACKEND`.

### Step 6 — Set Render environment variables

```
RESUME_STORAGE_BACKEND=r2
R2_ACCOUNT_ID=<cloudflare account id>
R2_ACCESS_KEY_ID=<key>
R2_SECRET_ACCESS_KEY=<secret>
R2_BUCKET_NAME=smartapply-resumes
```

---

## 5. Backend Hosting: Render Free Tier

The `render.yaml` at repo root already has the correct structure
(Docker build from `backend/Dockerfile`, `start.sh` runs migrations then
Uvicorn). No structural changes needed.

### Step 1 — Connect repository

Render dashboard → New → Blueprint → connect GitHub repo. Render detects
`render.yaml` and pre-fills the service config.

### Step 2 — Set `sync: false` environment variables

Every variable marked `sync: false` in `render.yaml` must be entered manually
in the Render dashboard. Fill in:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon `postgresql+asyncpg://...` from section 3 |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | `https://<your-service>.onrender.com/api/v1/auth/google/callback` |
| `JWT_PRIVATE_KEY` | Base64-encoded PEM (see section 6) |
| `JWT_PUBLIC_KEY` | Base64-encoded PEM (see section 6) |
| `GMAIL_TOKEN_ENCRYPTION_KEY` | Fernet key (see section 6) |
| `GEMINI_API_KEY` | From https://aistudio.google.com/app/apikey |
| `GROQ_API_KEY` | From https://console.groq.com |
| `CORS_ALLOWED_ORIGINS` | `chrome-extension://<extension-id>` (get ID after publishing) |

### Step 3 — Cold start mitigation

The free tier sleeps after 15 minutes of inactivity. First request after a
sleep takes ~20–30 s. To keep it warm:

1. Create a free UptimeRobot monitor pinging
   `https://<service>.onrender.com/api/v1/health` every 5 minutes.
2. This consumes ~720 of the 750 free hours/month — right at the limit.
   Watch your usage in the Render dashboard.
3. If cold starts become a user complaint, upgrade to the Render Starter plan
   ($7/month — always-on instance).

---

## 6. Secret Management

### JWT RS256 keys

Generate locally — never commit these files:

```bash
cd backend
openssl genrsa -out secrets/private.pem 2048
openssl rsa -in secrets/private.pem -pubout -out secrets/public.pem

# Encode for env var (single line)
export JWT_PRIVATE_KEY=$(base64 secrets/private.pem | tr -d '\n')
export JWT_PUBLIC_KEY=$(base64 secrets/public.pem  | tr -d '\n')
```

Paste the base64 strings into Render. `security.py` already checks
`settings.JWT_PRIVATE_KEY` (the base64 env var path) before falling back to
the PEM file path used locally.

### Gmail Fernet key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set as `GMAIL_TOKEN_ENCRYPTION_KEY` in Render. **Back this up.** If you lose
it, all stored Gmail refresh tokens become unreadable and every user must
re-authenticate.

### Rotation policy

| Secret | Rotate when | Impact |
|---|---|---|
| `JWT_PRIVATE_KEY` | Every 90 days or if compromised | Users must re-login after existing tokens expire (max 30 days) |
| `GMAIL_TOKEN_ENCRYPTION_KEY` | Only if compromised | Requires a migration script to re-encrypt all tokens before swapping |
| `SECRET_KEY` | Only if compromised | Invalidates all sessions immediately |

---

## 7. LLM Scaling Strategy

This is the highest-risk scaling problem. A single shared API key runs out of
quota as concurrent users grow. Apply these layers in order.

### Layer 1 (already done) — Per-user rate limiting

`get_user_key()` in `rate_limit.py` rate-limits by JWT subject (user UUID),
not by IP. This prevents one power user from consuming the shared quota.
Current limits: 20 req/min for extraction, 10 req/min for application
preparation.

### Layer 2 (implement now) — Gemini primary + Groq automatic fallback

Update `infrastructure/ai/factory.py` to cascade instead of selecting one
provider:

```python
class FallbackAIProvider(IAIProvider):
    def __init__(self, primary: IAIProvider, fallback: IAIProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    async def extract_job_details(self, post_text: str) -> JobExtractionResult:
        try:
            return await self._primary.extract_job_details(post_text)
        except AIProviderError:
            return await self._fallback.extract_job_details(post_text)
    # ... same pattern for the other two methods

def get_ai_provider() -> IAIProvider:
    return FallbackAIProvider(
        primary=GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL),
        fallback=GroqProvider(settings.GROQ_API_KEY, settings.GROQ_MODEL),
    )
```

Combined free quota: ~45 RPM before any user sees an error.

### Layer 3 (when growing) — Bring Your Own Key (BYOK)

Add an optional `gemini_api_key` column to the `users` table. In
`dependencies.py`, `get_ai_provider()` reads the authenticated user's stored
key; if present, instantiates a `GeminiProvider` with that key; otherwise
falls back to the shared provider.

Power users or teams provide their own Gemini API key (free from
https://aistudio.google.com/app/apikey) and never touch your shared quota.

### Layer 4 (experimental) — Chrome Built-in AI

Chrome 127+ ships `window.ai` (Gemini Nano, on-device) via the Prompt API.
For **job extraction** specifically (small task: parse ~500 words of text into
JSON), the on-device model is capable enough.

In the content script:

```typescript
if ('ai' in window && (window as any).ai?.languageModel) {
  // Run extraction locally, POST the parsed JSON to the backend
  // instead of posting raw text — eliminates one AI call entirely
}
```

Email generation requires a larger model — keep that server-side.

### Layer 5 (when monetising) — Usage-based quota per user tier

Track AI operations per user in a `user_usage` table. Free tier: 20
applications/month. Pro tier ($4/month via Stripe): unlimited. Implement only
when you have real paying users — premature quota gates kill growth.

### Summary: effective free capacity

| Source | RPM | req/day | Notes |
|---|---|---|---|
| Gemini 2.0 Flash | 15 | ~21 600 | 1 M tokens/day hard cap |
| Groq LLaMA 3.3 70B | 30 | 14 400 | fallback only |
| **Combined** | **~45** | **~36 000** | 3 AI calls per application = ~12 000 applications/day |

That is more than enough for a beta with hundreds of daily active users.

---

## 8. Building and Packaging the Extension

### Step 1 — Point at the production API

Create `extension/.env.production`:

```
VITE_API_BASE_URL=https://<your-service>.onrender.com/api/v1
```

`api-client.ts` already reads `import.meta.env.VITE_API_BASE_URL`.

In `vite.config.ts`, update `host_permissions` to remove localhost and add
your Render URL:

```typescript
host_permissions: [
  'https://www.linkedin.com/*',
  'https://<your-service>.onrender.com/*',
],
```

### Step 2 — Production build

```bash
cd extension
nvm use 20
npm run build   # runs tsc --noEmit then vite build
```

Output lands in `extension/dist/`.

### Step 3 — Smoke-test the build

Load `dist/` as an unpacked extension in `chrome://extensions` → Developer
mode → Load unpacked. Run the full flow end-to-end (OAuth → upload resume →
LinkedIn post → analyse → send) before packaging.

### Step 4 — Package for the store

The zip must have `manifest.json` at its root (not inside a `dist/` folder):

```bash
cd extension/dist
zip -r ../smartapply-v1.0.0.zip .
```

---

## 9. Google Cloud Console: Production Setup

### OAuth consent screen

APIs & Services → OAuth consent screen → switch from "Testing" to "External".
Without verification, Google shows a security interstitial to users and caps
you at 100 test users. Begin the verification process early — it takes 4–6
weeks for the `gmail.send` scope.

Required scopes to declare:

- `openid`
- `email`
- `profile`
- `https://www.googleapis.com/auth/gmail.send`

### Authorised redirect URIs

In your OAuth 2.0 Client ID credentials, add:

```
https://<your-service>.onrender.com/api/v1/auth/google/callback
```

Keep `http://localhost:8000/api/v1/auth/google/callback` for local dev.

### Authorised JavaScript origins

Add:

```
https://<your-service>.onrender.com
```

The extension's `chromiumapp.org` redirect URI does **not** need to be added
to the Google console — it is automatically trusted for installed Chrome
extensions.

---

## 10. Chrome Web Store Submission

### Required assets checklist

- [ ] Extension icon: 128×128 PNG
- [ ] Store screenshots: 1–5 images at 1280×800 or 640×400
- [ ] Privacy policy URL (required for `gmail.send` — host on GitHub Pages or Notion)
- [ ] Short description: ≤ 132 characters
- [ ] Detailed description

### Privacy policy minimum content

Because you store resume text, job post text, and Gmail OAuth refresh tokens,
explicitly cover: what you collect, how it is stored, how it is used, that you
do not sell data, and how users can request deletion.

Example `gmail.send` justification for the store review form:

> "This extension sends job application emails via the user's own Gmail
> account. The email is generated by AI from the LinkedIn post and the
> user's resume. The `gmail.send` scope is the minimum permission required
> and is used only when the user explicitly clicks the Send button."

### Submission steps

1. Go to https://chrome.google.com/webstore/devconsole
2. Pay the one-time $5 developer registration fee
3. New Item → Upload `smartapply-v1.0.0.zip`
4. Fill in store listing, select category **Productivity**
5. Under Privacy → justify each permission (`identity`, `storage`, `tabs`,
   `activeTab`, `gmail.send`)
6. Submit for review — initial review: 1–3 business days

### After approval

1. Copy the published extension ID from the dashboard.
2. Update `CORS_ALLOWED_ORIGINS` in Render to
   `chrome-extension://<published-id>`.
3. Trigger a Render redeploy (push an empty commit or use the manual deploy
   button).
4. Install from the store and do a final end-to-end smoke test.

---

## 11. Monitoring and Error Tracking

### Sentry

Create a free account at https://sentry.io. Create two projects: one Python
(backend), one JavaScript (extension popup).

Backend setup (`pyproject.toml` → add `sentry-sdk[fastapi]>=1.45.0`):

```python
# main.py — inside create_app()
import sentry_sdk
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=0.1,   # 10% of requests traced; stays within free tier
    environment=settings.APP_ENV,
)
```

Add `SENTRY_DSN` to Render env vars.

Free tier: 5 000 errors/month — sufficient for a beta.

### Render log drain → Papertrail

Render dashboard → your service → Log Stream → Add log drain → Papertrail
(https://papertrailapp.com, free: 50 MB/day, 7-day retention). `structlog`
emits structured JSON; Papertrail's search can filter by `"level":"error"`.
Set a Papertrail alert to email you on any error-level log line.

### Health check

Set the Render health check path to `/api/v1/health`. Render restarts the
instance automatically if the check fails three consecutive times.

---

## 12. Security Hardening Checklist

Work through this before publishing.

**Backend**

- [ ] `APP_ENV=production` is set — disables SQLAlchemy echo (which would
  log all SQL queries, leaking user data to logs)
- [ ] `CORS_ALLOWED_ORIGINS` is set to exactly `chrome-extension://<id>`
  (empty string = blocks all cross-origin requests)
- [ ] JWT private key is never referenced in any log statement
  (`grep -r "private_key\|PRIVATE_KEY" backend/app/` — should appear only in
  `config.py` and `security.py`)
- [ ] `GMAIL_TOKEN_ENCRYPTION_KEY` is set before any user authenticates Gmail
- [ ] Rate limiting is per-user (not per-IP) via `get_user_key()`
- [ ] Resume filenames are UUID-based, never the user-supplied filename
- [ ] Uploaded files validated by both MIME claim and `%PDF-` magic bytes

**Extension**

- [ ] `host_permissions` in production build contains only
  `https://www.linkedin.com/*` and the Render URL — no localhost
- [ ] Tokens stored in `chrome.storage.local`, not `localStorage`
- [ ] Content script matches list is `https://www.linkedin.com/*` only
- [ ] No `eval()` or `new Function()` calls (MV3 blocks these; Web Store
  review will reject the submission if detected)
- [ ] No API keys bundled in the extension source

**Data residency**

- Neon defaults to AWS us-east-2. For GDPR users, create the Neon project in
  the EU region (`eu-central-1`) and document this in the privacy policy.
- Implement `DELETE /api/v1/auth/me` (hard delete of all user rows, resumes,
  and R2 objects) before launch — GDPR Article 17 (right to erasure) requires
  this for any EU users.

---

## 13. Post-Launch Runbook

### Day-1 checklist after Chrome Web Store approval

- [ ] Copy published extension ID
- [ ] Update `CORS_ALLOWED_ORIGINS` in Render with `chrome-extension://<id>`
- [ ] Redeploy backend (Render dashboard → Manual Deploy)
- [ ] Install from store, run full end-to-end test
- [ ] Check Sentry dashboard — zero errors expected
- [ ] Confirm UptimeRobot is pinging and reporting green

### When Gemini 15 RPM is hit

Check Render logs for `429` from Gemini. Switch to Groq immediately without a
code change: set `AI_PROVIDER=groq` in Render env vars and hit "Save" (Render
auto-restarts). Long-term, implement the `FallbackAIProvider` from section 7,
Layer 2 — then no manual intervention is ever needed.

### When Neon 0.5 GB storage is reached

Neon alerts at 80% usage. The main data growth is `resumes.parsed_text`
(multi-KB per resume) and `job_posts` rows. Run in Neon's SQL console to check:

```sql
SELECT pg_size_pretty(pg_database_size('neondb'));
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

Options: add a cleanup job that deletes `job_posts` older than 90 days
(applications retain a copy of the generated email), or upgrade to Neon's
Launch plan ($19/month, 10 GB).

### When Render 750 hours are consumed

With UptimeRobot pinging every 5 minutes the service never sleeps and uses
exactly 720 hours/month — Render pauses it for the remaining ~30 hours. At
this point you have real users; upgrade to the Starter plan ($7/month, always-on).

### Releasing a backend update

```bash
git push origin main   # Render auto-deploys from main
```

Alembic runs at startup — schema migrations apply automatically before
traffic is served.

### Releasing an extension update

1. Bump `version` in `vite.config.ts` (e.g., `"1.0.1"`)
2. `npm run build`
3. `cd extension/dist && zip -r ../smartapply-v1.0.1.zip .`
4. Chrome Web Store dashboard → your extension → Package → Upload new package
5. Review: 24–48 hours for updates

Backend and extension release independently. The API is versioned at
`/api/v1/` — breaking changes require a new `/api/v2/` prefix and a
coordinated extension release.
