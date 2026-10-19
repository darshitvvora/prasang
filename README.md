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
| Paid plans | Fake gateway: checkout succeeds instantly; trial/renewal timers run in Temporal |
| Instagram / YouTube / Facebook | Post embeds + profile widgets from links (YouTube `@handle` widgets need `YOUTUBE_API_KEY`) |
| Photo / video uploads | Need `S3_BUCKET` + AWS credentials; otherwise the API answers `storage_not_configured` and links still work |

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
