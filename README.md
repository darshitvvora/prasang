# Prasang (प्रसंग)

Find artists for every prasang — an artist discovery platform for India (web now, React Native apps next).

| Path | What |
|---|---|
| [`frontend/`](frontend/README.md) | React 19 + Vite web app |
| [`backend/`](backend/) | FastAPI API, Temporal worker, Elasticsearch projector |
| [`contracts/`](contracts/README.md) | API contract (source of truth for web + mobile) |
| [`mockoon/`](mockoon/README.md) | Mock API serving the contract (frontend work without the backend) |
| [`docs/backlog.md`](docs/backlog.md) | Epics, stories, progress |

## Run everything locally

Requires Docker (8 GB RAM for Docker is plenty).

```bash
docker compose up -d --build        # first run builds images and seeds demo data (~2–3 min)
bash scripts/stack-health.sh        # STACK HEALTHY
open http://localhost:5173          # the app
```

| URL | Service |
|---|---|
| http://localhost:5173 | Web app (Vite, hot reload; proxies `/api` to the API) |
| http://localhost:8000/api/v1/docs | API docs (OpenAPI) |
| http://localhost:8080 | Temporal UI (lead notifications, subscription/trial timers) |
| http://localhost:9200 | Elasticsearch (search read model) |
| localhost:5433 | Postgres (`prasang`/`prasang`; dbs `prasang`, `supertokens`, `temporal`, `temporal_visibility`) |
| http://localhost:3567 | SuperTokens core |

### Signing in

- **Mobile OTP** works with no accounts: enter any 10-digit mobile number, then read the code from the API log:
  ```bash
  docker compose logs api | grep "login code"
  ```
- **Google** needs an OAuth client: put `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in a root `.env` (see [`.env.example`](.env.example)) and `docker compose up -d api`.
- New users pick **artist** or **planner** once. Artists then go through onboarding (profile, social links, media, plan).

Demo data: 12 artists (Mumbai, Pune, Delhi, Bengaluru), reviews, leads. For API scripting, local dev tokens act as demo users:
`Authorization: Bearer mock-artist` (Arjun, Basic plan), `mock-planner` (Neha), `mock-new` (no profile).

### What works without third-party accounts

| Feature | Locally |
|---|---|
| Phone OTP sign-in | OTP printed in API logs |
| Lead notifications (Temporal) | WhatsApp/SMS/email printed in `docker compose logs worker` |
| Welcome, trial-ending, renewal, payment-failed, plan-ended and "did you book?" messages | printed in `docker compose logs worker` |
| Google reviews on profiles | Need `GOOGLE_PLACES_API_KEY`; otherwise hidden |
| Contact form | Stored; emailed to `SUPPORT_EMAIL` when email is set up |
| Paid plans | Fake gateway: checkout succeeds instantly; trial/renewal timers run in Temporal |
| Instagram / YouTube / Facebook | Post embeds + profile widgets from links (YouTube `@handle` widgets need `YOUTUBE_API_KEY`) |
| Photo / video uploads | Need `S3_BUCKET` + AWS credentials; otherwise the API answers `storage_not_configured` and links still work |

### Admin (no admin UI yet — commands, each one audit-logged)

```bash
docker compose exec api python -m app.cli admin --help
docker compose exec api python -m app.cli admin make-admin 9820012345              # by phone or user id
docker compose exec api python -m app.cli admin verify <slug>                       # / unverify
docker compose exec api python -m app.cli admin feature <slug>                      # / unfeature (home page, any plan)
docker compose exec api python -m app.cli admin suspend <slug> --reason "…"         # hidden; billing keeps running / restore
docker compose exec api python -m app.cli admin grant-plan <slug> pro --days 30 --reason "…"
docker compose exec api python -m app.cli admin hide-review <review-id> --reason "…" # / restore-review
docker compose exec api python -m app.cli admin block-user <phone> --reason "…"     # artists: also suspended + billing cancelled
docker compose exec api python -m app.cli admin sync-subscription <slug>            # re-read Razorpay (missed webhook)
docker compose exec api python -m app.cli admin clear-google-place <slug>
docker compose exec api python -m app.cli admin reports                             # reported reviews + contact messages
```

In production run the same commands on the app server through an SSM session.

### Link previews

Shared profile links unfold with the artist's photo, name, type and city on WhatsApp/Instagram/Facebook. Check locally:
`curl -s localhost:5173/profile/arjun-malhotra-magic | grep og:` — production nginx must route `/profile/*` to the API's
`GET /profile/{slug}` (with `WEB_INDEX_PATH` pointing at the built `index.html`).

### Everyday commands

```bash
docker compose logs -f api worker projector          # follow the backend
docker compose run --rm migrate                        # re-run migrations + seed + reindex
docker compose exec api python -m app.cli reindex      # rebuild the Elasticsearch index
curl -X POST localhost:8000/api/v1/_mock/reset         # reset demo data (local only)
bash mockoon/smoke.sh http://localhost:8000/api/v1     # contract smoke test against the real API
docker compose down                                    # stop (data kept)
docker compose down -v                                 # stop and wipe all data
```

### Backend tests

The suite uses the compose Postgres (db `prasang_test`) and Elasticsearch (`test_` indices):

```bash
docker compose up -d postgres elasticsearch
cd backend && uv run pytest
```

## Architecture

Writes go to **Postgres**; every artist change also writes an outbox row in the same transaction, and the **projector** copies it into **Elasticsearch**, which serves all search/listing reads. **SuperTokens** (self-hosted) handles sessions — cookies for web, header tokens for mobile. **Temporal** (self-hosted on Postgres) runs lead notifications and the subscription/trial timers. Media lives in **S3**. Details: [backend design spec](docs/superpowers/specs/2026-09-29-backend-mvp-design.md).
