# Prasang Backend MVP — Design

**Date:** 2026-09-29
**Status:** Draft for review
**Goal:** Ship a production backend for the existing React frontend (search, artist profile, contact-info leads, artist dashboard/onboarding/leads, planner dashboard/inquiries, pricing + paid subscriptions) as fast as possible, at near-zero hosting cost.

## 1. Decisions (locked)

| Area | Decision | Why |
|---|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Pydantic v2, `uv` | User choice; async fits I/O-heavy API |
| Write store | Supabase Postgres (free, Mumbai `ap-south-1`) via **session pooler** (IPv4) | Always-free; same DB as Supabase Auth |
| Read store (search) | Elasticsearch 8 single node on the Oracle VM | CQRS read side from day 1 (user choice) |
| Auth | Supabase Auth. Google via Google Identity Services button/One Tap → `supabase.auth.signInWithIdToken` (consent screen shows Prasang, not `*.supabase.co`). Phone OTP later via Supabase Send-SMS hook → MSG91 | No auth code in our backend; free to 50k MAU |
| Workflows | **Temporal Cloud** (paid, user choice). Local dev: Temporal CLI dev server in Docker | Durable retries/timers/signals only where needed |
| Compute | Oracle Cloud Always Free Ampere A1 (arm64), Mumbai, Docker Compose, Caddy (auto-HTTPS). Account converted to PAYG to avoid idle reclaim | Free indefinitely; fits ES + API + workers |
| Frontend hosting | Cloudflare Pages | Vercel Hobby forbids commercial use |
| Object storage | Cloudflare R2 (S3 API, presigned uploads). Local: MinIO | 10 GB free, zero egress |
| Payments | Razorpay Subscriptions (Checkout + webhooks) | Indian market, UPI AutoPay |
| Notifications | MSG91 (WhatsApp + SMS), Resend (email). All behind a `Notifier` interface with a `console` implementation for local/dev | Lets us ship before DLT/WhatsApp template approval |

Where Temporal is **not** used: CRUD, auth/profile bootstrap, onboarding, media uploads, search sync (outbox poller), webhooks ingestion.

Where Temporal **is** used:
1. `LeadNotificationWorkflow` — fan-out WhatsApp/SMS/email with independent retries after a lead is committed.
2. `SubscriptionWorkflow` — create Razorpay subscription, wait (≤24 h) for activation signal, apply tier, then track renewals/halts/cancellation with timers and signals until the subscription ends.

## 2. Architecture

```
 Browser (React, Cloudflare Pages)
   │  supabase-js (Google ID token → Supabase session)
   │  Bearer <Supabase access token>
   ▼
 Caddy (TLS, api.prasang.in)  ── Oracle A1 VM, docker compose ──────────────┐
   │                                                                         │
   ▼                                                                         │
 api (FastAPI)  ──writes + outbox (same tx)──►  Supabase Postgres            │
   │   ▲                                         ▲        ▲                  │
   │   └──── search reads ──── Elasticsearch ◄── projector (outbox poller)   │
   │                                                                         │
   ├── start/signal workflows ──► Temporal Cloud ◄── worker (activities:     │
   │                                                  DB, Razorpay, MSG91,   │
   │                                                  Resend, outbox)        │
   └── presigned URLs ──► Cloudflare R2 ◄── browser uploads directly          │
 Razorpay ──webhook──► api /api/v1/subscriptions/webhook                     │
 backup (cron container) ── nightly pg_dump ──► R2                          ─┘
```

Processes (one image, different commands): `api`, `projector`, `worker`, `backup`.

## 3. Code layout

```
backend/
  pyproject.toml, uv.lock, Dockerfile, alembic.ini, alembic/
  app/
    main.py                 # FastAPI app factory, routers, error handlers
    config.py               # pydantic-settings; ENV=local|test|production
    db.py                   # async engine/session, Base
    deps.py                 # get_session, current_user, require_role
    auth/        (jwt.py: JWKS verify; router: /me)
    artists/     (models, schemas, service, router)
    media/       (storage.py S3 client, service, router)
    leads/       (models, schemas, service, router)
    subscriptions/ (plans.py, razorpay_client.py, service, router, webhook)
    search/      (es_client.py, index_mapping.py, documents.py, query.py, router)
    outbox/      (models, emit.py, projector.py)
    notifications/ (notifier.py interface, console.py, msg91.py, resend.py)
    workflows/   (lead_notification.py, subscription.py, activities/*.py, worker.py, client.py)
    cli.py                  # reindex, seed, create-index
  tests/        (unit/, integration/, workflows/)
docker-compose.yml          # local: postgres, elasticsearch, temporal dev, minio, api, projector, worker
deploy/                     # docker-compose.prod.yml, Caddyfile, backup script, runbook
```

Each module owns its models/schemas/service; routers are thin; services take an `AsyncSession` and plain arguments so they are testable without HTTP.

## 4. Data model (Postgres, write side)

All ids UUID. Timestamps `timestamptz`. Enums as Postgres enums.

- **users**: `id` (= Supabase `auth.users.id`), `email`, `phone`, `full_name`, `role` (`artist|planner|admin`), `avatar_url`, `created_at`, `updated_at`. Created by `POST /api/v1/me` bootstrap on first login.
- **artist_profiles**: `id`, `user_id` (unique FK), `slug` (unique), `stage_name`, `artist_type`, `bio`, `location_city`, `location_area`, `per_event_rate_min/max` (int ₹), `experience_years`, `event_types_supported` (enum[]), `languages_spoken` (text[]), `ready_to_travel`, `availability_status`, `instagram_handle`, `youtube_channel`, `profile_image_url`, `contact_phone`, `contact_whatsapp`, `is_verified`, `is_featured`, `subscription_tier`, `search_boost_score`, `average_rating`, `total_reviews`, `profile_views`, `total_leads`, `is_published`, timestamps.
- **artist_media**: `id`, `artist_id`, `kind` (`image|video|youtube_embed|instagram_embed`), `url`, `storage_key`, `thumbnail_url`, `caption`, `display_order`, `created_at`.
- **subscription_plans**: seeded; `tier` (PK), `name`, `monthly_price`, `annual_price` (per-year ₹), `razorpay_plan_id_monthly/annual`, `lead_limit_monthly` (-1 unlimited), `max_images`, `max_videos` (-1 unlimited), `search_boost_score`, `is_featured`, `verified_badge`, `whatsapp_notifications`.
  Seed (matches Pricing page): free 0/0, 3 leads, 5 img/0 vid, boost 0 · basic ₹299/₹2,988, 15 leads, 20/3, boost 10 · pro ₹599/₹5,988, unlimited, 100/20, boost 25, featured · premium ₹1,199/₹11,988, unlimited, unlimited, boost 50, featured.
- **subscriptions**: `id`, `artist_id`, `tier`, `billing_cycle`, `status` (`created|active|halted|cancelled|completed|expired`), `razorpay_subscription_id` (unique), `current_period_start/end`, `workflow_id`, timestamps. At most one `active` and one `created` (awaiting payment) subscription per artist (partial unique indexes); creating a new one cancels any existing `created` one, and activation cancels the previous `active` one (plan change).
- **payment_events**: `id` (Razorpay event id, PK → idempotency), `event_type`, `razorpay_subscription_id`, `payload` jsonb, `received_at`, `signalled_at`.
- **leads**: `id`, `artist_id`, `planner_id` (FK users), `planner_name`, `planner_phone`, `planner_email`, `event_type`, `event_title`, `event_date`, `event_city`, `event_area`, `budget_min`, `budget_max`, `notes`, `source` (`search|profile|featured|direct_link`), `status` (`new|contacted|converted|declined|expired`), `is_locked` (over monthly quota), `created_at`, `updated_at`. Unique `(artist_id, planner_id, event_date)` to stop duplicate spam.
- **outbox_events**: `id` bigserial, `aggregate_type`, `aggregate_id`, `event_type`, `payload` jsonb, `created_at`, `processed_at`, `attempts`, `last_error`. Partial index on `processed_at IS NULL`.

Reviews, favourites, referrals, localities, search history: **not in MVP** (profile shows stored `average_rating`/`total_reviews`, default 0).

## 5. Key flows

### 5.1 Auth
1. Frontend: Google button → Google ID token → `supabase.auth.signInWithIdToken({provider:'google', token})` → Supabase session.
2. Every API call sends `Authorization: Bearer <access_token>`.
3. API verifies via Supabase JWKS (`/auth/v1/.well-known/jwks.json`, cached 10 min, refetch on unknown `kid`), checks `iss`, `aud=authenticated`, `exp`. `sub` → `users.id`.
4. First login: `GET /api/v1/me` returns 404 `profile_required` → frontend role picker → `POST /api/v1/me {role, full_name, phone?}`. Role is immutable after creation (admin can change).
5. Local/test: `AUTH_MODE=local` accepts HS256 tokens signed with `LOCAL_JWT_SECRET`; app refuses to start with this mode when `ENV=production`.

### 5.2 Artist profile (write) → search (read)
- `POST /api/v1/artists` (artist role, one per user) creates profile with generated unique slug; `PATCH /api/v1/artists/me`; `GET /api/v1/artists/me`; public `GET /api/v1/artists/{slug}` (Postgres, published only) increments `profile_views` asynchronously (fire-and-forget update, no outbox).
- Every profile/tier change writes `outbox_events(aggregate_type='artist', event_type='artist.upserted')` in the same transaction.
- **Projector**: loop every 2 s: `SELECT … WHERE processed_at IS NULL ORDER BY id LIMIT 100 FOR UPDATE SKIP LOCKED`; dedupe by aggregate; for each artist **reload current state from Postgres** and index (or delete if unpublished/missing) into ES alias `artists`; mark processed. Failures increment `attempts`, store `last_error`, retried next tick; after 10 attempts logged as dead (still visible in table). Idempotent by design. Its constant polling also keeps the Supabase project from pausing.
- `cli reindex`: create new index `artists_vN`, bulk load all published artists, atomically swap alias.

### 5.3 Search (read side, ES only)
`GET /api/v1/search/artists?q&city&area&artist_type&event_type&language&ready_to_travel&min_price&max_price&min_rating&verified_only&featured_only&sort=relevance|rating|price_low|price_high|popular|newest&page&size`
- `bool` filters for all facets; `q` → `multi_match` (stage_name^3, artist_type^2, location_area^2, bio) with `fuzziness: AUTO`.
- relevance = `function_score` with `field_value_factor(search_boost_score)` + featured weight + rating factor.
- Response: `{total, page, size, results:[ArtistCard]}` + `facets` (counts by artist_type, city).
- `GET /api/v1/search/suggestions?q` → `search_as_you_type` on stage_name / area / type, max 8.
- `GET /api/v1/artists/featured` → ES, featured + boost, limit 12.

### 5.4 Lead ("Get Contact Info")
1. Planner must be signed in (one-tap Google; protects artist numbers from scraping). Rate limit: 10 leads/planner/day, in Postgres (count query).
2. `POST /api/v1/leads` → one transaction: insert lead; compute artist's leads this calendar month (IST); `is_locked = count > plan.lead_limit_monthly` (unless unlimited); increment `total_leads`; commit.
3. After commit: start `LeadNotificationWorkflow(lead_id)` (workflow id `lead-{lead_id}`, idempotent). If Temporal is unreachable the request still succeeds (lead saved; error logged; `cli resend-lead-notifications` replays).
4. Response reveals `contact_phone`/`contact_whatsapp` to the planner (always — planner experience never depends on the artist's quota).
5. Workflow activities: `load_lead_context` → parallel `send_email` (all tiers), `send_whatsapp` (tier.whatsapp_notifications), `send_sms` (fallback if WhatsApp not allowed/failed). Locked leads send a "You have a new lead — upgrade to view" message without planner details. Each activity: 3 attempts, exponential backoff, non-retryable on 4xx validation errors.
6. Artist: `GET /api/v1/leads/artist?status` (locked leads returned with masked planner fields), `PATCH /api/v1/leads/{id}` status `contacted|converted|declined`.
7. Planner: `GET /api/v1/leads/planner` (inquiries), status mapped: new→pending, contacted→responded, converted→confirmed, declined/expired→declined.
8. Nightly: leads with `event_date < today` and status `new` → `expired` (simple cron in `backup` container calling `cli expire-leads`).
9. On upgrade, current-month locked leads are unlocked.

### 5.5 Subscription
1. `POST /api/v1/subscriptions {tier, billing_cycle}` (artist) → create `subscriptions` row (`created`) → start `SubscriptionWorkflow` (id `sub-{subscription_id}`) → workflow activity creates Razorpay subscription and stores its id → API waits for that via a workflow **update** (`get_checkout`) returning `{razorpay_subscription_id, key_id}` → frontend opens Razorpay Checkout.
2. Checkout success handler → `POST /api/v1/subscriptions/verify {razorpay_payment_id, razorpay_subscription_id, razorpay_signature}` verifies HMAC and signals `payment_authorized` (fast UX path).
3. Webhook `POST /api/v1/subscriptions/webhook`: verify `X-Razorpay-Signature`; insert `payment_events` (duplicate id → 200 no-op); signal the workflow by `razorpay_subscription_id` mapping; if signalling fails return 500 so Razorpay retries.
4. Workflow: wait ≤24 h for `activated`/`payment_authorized`; timeout → cancel at Razorpay, status `expired`, end. On activation → activity `apply_tier` (profile tier, boost, featured, unlock month's leads, outbox event, cancel any previous active subscription). Then loop: wait for `charged` (extend `current_period_end`), `halted`/`cancelled`/`completed` (activity `downgrade_to_free`), or timer `current_period_end + 3 days grace` with no charge → downgrade. `continue_as_new` after each charge to keep history small.
5. `POST /api/v1/subscriptions/cancel` → Razorpay cancel at cycle end; tier stays until period end (the webhook drives the workflow).
6. `GET /api/v1/subscriptions/plans` (public), `GET /api/v1/subscriptions/me`.

### 5.6 Media
`POST /api/v1/media/upload-url {kind, content_type, size}` → quota check by tier, returns presigned PUT (5 min, max 10 MB image / 100 MB video) + `storage_key`; `POST /api/v1/media {storage_key, kind, caption}` confirms (HEAD object to verify); `DELETE /api/v1/media/{id}`; `PUT /api/v1/media/order`. Embeds (YouTube/Instagram URL) skip upload. Profile photo uses the same flow with `kind=avatar`.

## 6. Errors, security, ops
- Error shape: `{"error": {"code": "...", "message": "...", "details": {...}}}`; domain exceptions mapped in one handler.
- CORS allowlist: `https://prasang.in`, Pages preview domain, `http://localhost:5173`.
- Webhook/verify signature checks with `hmac.compare_digest`. Secrets only via env; `.env.example` committed.
- Planner PII masked for locked leads; artist phone only returned from lead creation and to the artist themself.
- Logging: JSON to stdout (structlog), request id middleware. `/healthz` (process up), `/readyz` (DB + ES reachable).
- DB pool: size 5, overflow 5 (Supabase free connection limits). ES heap 1 GB.
- Backups: nightly `pg_dump` → R2, keep 14 days.

## 7. Testing
- `pytest` + `pytest-asyncio`; integration tests against the docker-compose Postgres and Elasticsearch (fresh schema per session, truncation per test).
- Auth tests use a locally generated RSA JWKS (no Supabase needed).
- Workflows: `temporalio.testing.WorkflowEnvironment.start_time_skipping()` with mocked activities (24 h timeout, grace timer, signals, continue-as-new).
- External clients (Razorpay, MSG91, Resend, R2) behind small interfaces; fakes in tests; `respx` for HTTP-level client tests.
- CI (GitHub Actions): ruff, pytest with service containers, build arm64 image on `main`.

## 8. Deployment
- Oracle A1 VM (Ubuntu 24.04, 4 OCPU/24 GB) with Docker; `deploy/docker-compose.prod.yml`: caddy, api, projector, worker, elasticsearch, backup. Images from GHCR (`linux/arm64`).
- GitHub Actions on `main`: test → build/push → SSH `docker compose pull && docker compose run --rm api alembic upgrade head && docker compose up -d`.
- Temporal Cloud namespace, API-key auth from worker/api.
- DNS on Cloudflare: `prasang.in` → Pages, `api.prasang.in` → VM (DNS-only, Caddy does TLS).

## 9. Out of scope (post-launch backlog)
Reviews & ratings submission, favourites, referrals, localities pages, AI bio/embeddings/semantic search, Instagram/YouTube import, admin UI (admin via SQL/CLI for now), phone OTP (enabled once MSG91 DLT approved — config only), analytics dashboard.
