# Prasang Backend MVP — Design (v2)

**Date:** 2026-09-29 · **Revised:** 2026-10-19 (v2: SuperTokens, self-hosted Temporal + Postgres, social embeds, local-first Docker stack, AWS + S3, React Native apps)
**Status:** Approved
**Goal:** Run the whole Prasang application — React frontend, FastAPI backend, auth, search, workflows — with one `docker compose up` (an S3 bucket is the only external dependency, and only for photo/video uploads), then deploy to AWS. The same API also serves the React Native apps (Android + iOS).

The API contract is defined in [`contracts/README.md`](../../../contracts/README.md) and [`frontend/src/api/types.ts`](../../../frontend/src/api/types.ts) (Plan A). **The contract is authoritative for request/response shapes**; this spec covers how the backend satisfies it.

## 1. Decisions

| Area | Decision |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2.0 async (asyncpg), Alembic, Pydantic v2, `uv` |
| Write store | PostgreSQL 16, self-hosted (one server, databases `prasang`, `supertokens`, `temporal`, `temporal_visibility`) |
| Read store | Elasticsearch 8 single node, fed by an outbox projector (CQRS) |
| Auth | **SuperTokens self-hosted** core (`registry.supertokens.io/supertokens/supertokens-postgresql`, pinned) + `supertokens-python` in FastAPI + `supertokens-web-js` in React. Recipes: **ThirdParty (Google)** and **Passwordless (phone OTP, `USER_INPUT_CODE`)**. Session = httpOnly cookies |
| Workflows | **Temporal self-hosted** (`temporalio/server`, `temporalio/admin-tools` schema job, `temporalio/ui`) on Postgres |
| Object storage | **Amazon S3** everywhere (no MinIO — its community images were discontinued). Local dev uses a dev bucket via the standard AWS credential chain; if `S3_BUCKET` is unset, upload endpoints return 503 `storage_not_configured` and everything else works. Browser/app uploads via presigned PUT. Tests use `moto` |
| Social | Instagram / YouTube / Facebook **URL embeds** (official iframe embed URLs, no API keys); feed auto-import is post-launch (needs Meta app review) |
| Payments | `PaymentGateway` interface: `razorpay` (Subscriptions API) and `fake` (default locally; checkout key `rzp_test_mock`) |
| Notifications | `Notifier` interface: `console` (default locally), `msg91` (SMS/WhatsApp), `resend` (email). OTP SMS uses the same interface |
| Hosting | **AWS** (exact services decided in the deployment plan). API on `api.prasang.in`, web on `prasang.in` — same site, so SuperTokens cookies work with `cookie_domain=.prasang.in` |
| Clients | React web app (this repo `frontend/`) and **React Native apps for Android and iOS** (later epic). Both use the same `/api/v1` contract. SuperTokens sessions support cookies (web) and header tokens (mobile, `st-auth-mode: header`), so the backend must not assume cookies |

**Temporal is used only for durable, long-running or retry-heavy work:**
1. `LeadNotificationWorkflow` — after a lead commits: email (all tiers), WhatsApp (tiers with WhatsApp), SMS fallback; independent retries.
2. `SubscriptionWorkflow` — create gateway subscription, wait ≤24 h for activation, apply tier, then follow charges/halts/cancellation with signals and a grace timer until it ends.
3. `TrialWorkflow` — start a 7-day trial on a tier, sleep 7 days (durable timer), then downgrade to Free unless a paid subscription took over.

Not Temporal: CRUD, auth, media, search projection (outbox poller), webhook ingestion, analytics counters.

## 2. Architecture (local and production share the same compose services)

```
 Browser ── React (Vite dev :5173 / Cloudflare Pages)
   │  supertokens-web-js (cookies, auto-refresh)    /api/* (Vite proxy locally, api.prasang.in in prod)
   ▼
 api (FastAPI :8000)  /api/v1/auth/* = SuperTokens routes, /api/v1/* = Prasang API
   │ ├─ SuperTokens core (:3567) ──► Postgres db `supertokens`
   │ ├─ writes + outbox_events (same tx) ──► Postgres db `prasang`
   │ ├─ search reads ──► Elasticsearch (:9200)  ◄── projector (outbox poller)
   │ ├─ start/signal workflows ──► Temporal (:7233) ──► Postgres dbs `temporal*`
   │ │                                   ▲
   │ │                                 worker (activities: DB, gateway, notifier, outbox)
   │ └─ presigned URLs ──► Amazon S3 ◄── browser / app PUT
 Temporal UI (:8080)
```

One backend image, four commands: `api`, `worker`, `projector`, `migrate`.

## 3. Code layout

```
backend/
  pyproject.toml, uv.lock, Dockerfile, alembic.ini, alembic/versions/
  app/
    main.py            create_app(): SuperTokens middleware, CORS, routers, error handlers
    config.py          Settings (pydantic-settings); ENV=local|test|production
    db.py              async engine/session; Base
    errors.py          AppError(code, status, message, details) + handlers (incl. 422 → details.fields)
    schemas.py         CamelModel base (alias_generator=to_camel, populate_by_name, extra=forbid on requests)
    auth/              supertokens_setup.py (init, recipes, SMS delivery → Notifier), deps.py (current_user, require_role), router (/me)
    artists/           models, schemas, service, router (incl. dashboard, contact-click), slugs.py, completeness.py
    embeds.py          parse social URLs → (kind, embed_url)
    media/             storage.py (S3 client), service, router
    leads/             models, schemas, service, router
    subscriptions/     plans.py (seed), gateway.py (razorpay|fake), service, router, webhook
    search/            es.py, mapping.py, documents.py, query.py, router
    outbox/            models, emit.py, projector.py
    notifications/     notifier.py (Protocol), console.py, msg91.py, resend.py
    locations/         models (localities), router
    workflows/         lead_notification.py, subscription.py, trial.py, activities.py, worker.py, client.py
    cli.py             migrate, seed, create-index, reindex, expire-leads
  tests/               conftest (DB/ES per session), unit/, api/, workflows/, contract/
docker-compose.yml     full local stack
docker/                postgres-init.sql, temporal/{setup-schema.sh,create-namespace.sh,dynamicconfig.yaml}
```

## 4. Data model (`prasang` database)

All timestamps `timestamptz`; ids are UUID unless noted.

- **users**: `id` text PK (SuperTokens user id), `email`, `phone` (10-digit national), `full_name`, `role` (`artist|planner|admin`), `avatar_url`, `created_at`, `updated_at`.
- **localities**: `id`, `city`, `area` (nullable for city-only rows), `sort_order`; unique (`city`,`area`). Seeded from the contract's locations.
- **artist_profiles**: `id`, `user_id` unique FK, `slug` unique, `stage_name`, `artist_type`, `bio`, `location_city`, `location_area`, `per_event_rate_min/max` int, `experience_years`, `event_types_supported` text[], `languages_spoken` text[], `ready_to_travel`, `instagram_handle`, `youtube_channel`, `facebook_url`, `profile_image_url`, `contact_phone`, `whatsapp_number`, `is_published`, `is_verified`, `is_featured`, `subscription_tier` (effective tier), `tier_source` (`free|trial|paid`), `trial_ends_at`, `trial_used`, `search_boost_score`, `average_rating`, `total_reviews`, `total_leads`, timestamps.
- **artist_daily_stats**: (`artist_id`, `day`) PK, `profile_views`, `contact_clicks` — dashboard month-over-month metrics.
- **artist_media**: `id`, `artist_id`, `kind` (`image|video|youtube|instagram|facebook`), `url` (public URL or original social URL), `embed_url` (iframe URL for social kinds, null otherwise), `storage_key`, `thumbnail_url`, `caption`, `display_order`, `created_at`.
- **reviews**: `id`, `artist_id`, `reviewer_name`, `rating` 1–5, `event_type`, `event_month` (`YYYY-MM`), `text`, `created_at`. Read-only in MVP (seeded/admin).
- **leads**: as contract `ArtistLead` + `artist_id`, `planner_id`, `source`, `budget_range`; status `new|contacted|converted|declined|expired`; `is_locked`; unique (`artist_id`,`planner_id`,`event_date`) with NULL dates allowed once per day via service check.
- **subscription_plans**: seeded from the contract plans (tier PK, prices, limits, features jsonb, `gateway_plan_monthly/annual`).
- **subscriptions**: `id`, `artist_id`, `tier`, `billing_cycle`, `status` (`created|active|halted|cancelled|completed|expired`), `gateway_subscription_id` unique, `current_period_end`, `cancel_at_period_end`, `workflow_id`, timestamps. Partial unique: one `active` and one `created` per artist.
- **payment_events**: `id` (gateway event id) PK, `event_type`, `gateway_subscription_id`, `payload` jsonb, `received_at`, `signalled_at`.
- **outbox_events**: bigserial `id`, `aggregate_type`, `aggregate_id`, `event_type`, `payload` jsonb, `created_at`, `processed_at`, `attempts`, `last_error`.

SuperTokens and Temporal own their databases; we never touch their tables.

## 5. Key flows

### 5.1 Auth (SuperTokens)
- Backend `init(app_info: api_domain=API_DOMAIN, website_domain=WEBSITE_DOMAIN, api_base_path="/api/v1/auth", website_base_path="/auth")`, recipes `session`, `thirdparty` (Google; enabled only when `GOOGLE_CLIENT_ID/SECRET` are set), `passwordless` (phone, OTP).
- **OTP delivery**: SMS delivery is overridden to call our `Notifier`; locally the console notifier logs `OTP for +91XXXXXXXXXX: 123456`. Production uses MSG91 once DLT is approved.
- **Google**: frontend `getAuthorisationURLWithQueryParamsAndSetState({thirdPartyId:'google', frontendRedirectURI: <site>/auth/callback/google})` → Google → `/auth/callback/google` page calls `signInAndUp()`.
- `GET /api/v1/auth/providers` (ours, public): `{google: bool, phoneOtp: true}` so the UI can disable Google when it is not configured.
- `current_user` dependency = `verify_session()` → users row lookup. `GET /me` returns 404 `profile_required` when the SuperTokens user has no `users` row; `POST /me` creates it (email/phone prefilled from the SuperTokens user: Google email, OTP phone without `+91`).
- Frontend `VITE_AUTH_MODE=supertokens`: `supertokens-web-js` patches `fetch` (cookies, anti-CSRF, refresh on 401). `AuthProvider` uses `Session.doesSessionExist()` instead of a stored token; `signOut()` → `Session.signOut()`. Mock mode stays for Mockoon.
- Tests: `current_user` is overridden via FastAPI `dependency_overrides` with a header-selected test user; SuperTokens core is not needed for the unit/API suite.

### 5.2 Artist profile → search
- `POST /artists`, `GET/PATCH /artists/me` as contract; slug = slugified stage name + short suffix on collision. Writes emit `artist.upserted` to the outbox in the same transaction.
- `GET /artists/{slug}` (published only) reads Postgres; increments today's `profile_views` (upsert into `artist_daily_stats`, not outbox).
- Projector polls every 1 s (`FOR UPDATE SKIP LOCKED`, batch 100), dedupes per artist, reloads from Postgres, indexes or deletes in ES alias `artists`, marks processed; failures increment `attempts`/`last_error`.
- Completeness (contract `ProfileCompleteness`) computed: basic info, photo, bio ≥ 50 chars, ≥1 media, instagram handle, ≥1 review.

### 5.3 Search (ES)
- `GET /search/artists`: filters (`city`, `area`, `artistType`, `eventType`, `language`, `readyToTravel`, price overlap `minPrice/maxPrice`, `minRating`, `verifiedOnly`, `featuredOnly`), `q` multi_match (stage_name^3, artist_type label^2, area^2, bio; fuzziness AUTO), relevance = function_score (boost score, featured, rating), sorts per contract, `page/size` (max 50), facets via terms aggs.
- `GET /search/suggestions`: `search_as_you_type` on name/area + artist-type labels.
- `GET /artists/featured`, `GET /artists/{slug}/similar` (same type, same city boosted, excludes self) also read ES.

### 5.4 Social embeds
`embeds.parse(url) -> Embed(kind, embed_url)`; rejects anything else with 422 `validation_error` (`details.fields.url`).
- YouTube: `youtube.com/watch?v=ID`, `youtu.be/ID`, `youtube.com/shorts/ID` → `https://www.youtube-nocookie.com/embed/ID`.
- Instagram: `instagram.com/p/CODE`, `/reel/CODE`, `/tv/CODE` → `https://www.instagram.com/p/CODE/embed` (reel → `/reel/CODE/embed`).
- Facebook: post/permalink/photo URLs → `https://www.facebook.com/plugins/post.php?href=<urlencoded>&show_text=true&width=500`; `/videos/` and `fb.watch` → `.../plugins/video.php?href=...`.
Profile page renders social media as sandboxed `<iframe>`s (`allow` limited to encrypted-media/picture-in-picture/fullscreen). Profile handles: `instagramHandle`, `youtubeChannel`, `facebookUrl` link out.

### 5.5 Leads
As contract: signed-in planner only; quota → `is_locked`; duplicate (same planner/artist/event date) returns 200 with existing id; 10/day planner rate limit; `contact_clicks` counter via `POST /artists/{slug}/contact-click`. After commit, start `LeadNotificationWorkflow` (`lead-{id}`); Temporal outage is logged, request still succeeds.

### 5.6 Subscriptions & trials
- Plans from DB. `POST /subscriptions` creates a `created` row (cancelling any previous `created`), starts `SubscriptionWorkflow` (`sub-{id}`), and uses a workflow **update** to obtain the checkout payload. `fake` gateway: checkout key `rzp_test_mock`; `/verify` accepts `mock-signature` and signals activation. `razorpay` gateway: HMAC verification and webhooks.
- Activation → effective tier, `tier_source=paid`, boost/featured from plan, unlock this month's locked leads, cancel previous active subscription, outbox event.
- `POST /subscriptions/trial` (once, `trial_used`) → `tier_source=trial`, `trial_ends_at=now+7d`, starts `TrialWorkflow`; on expiry downgrades to free unless `tier_source` changed.
- Plan usage (`PlanUsage`) computed from profile + leads this month (IST).

### 5.7 Media
Presigned PUT (5 min; image ≤10 MB, video ≤100 MB, avatar ≤5 MB); confirm by HEAD; tier quotas from plan; social URLs go through `embeds.parse`. Public URL = `PUBLIC_MEDIA_BASE_URL/<key>` (bucket public-read on `artists/*` or CloudFront in production). Bucket CORS must allow PUT from the web origin.

## 6. Errors, security, ops
- Error body per contract; FastAPI `RequestValidationError` mapped to 422 `validation_error` with `details.fields` (camelCase).
- CORS: website origin with credentials (SuperTokens headers). Cookies `SameSite=Lax`, secure in production.
- Planner PII masked on locked leads; artist phone only in lead response and to the owner.
- Logs: JSON to stdout; `/healthz` (process) and `/readyz` (Postgres, ES, Temporal reachable).

## 7. Testing
- `pytest` + `pytest-asyncio` against the compose Postgres (`prasang_test` db) and Elasticsearch (`test_` index prefix).
- Contract tests: every `contracts/examples/**/*.response.json` parses into its Pydantic response model with `extra="forbid"`, and API responses for seeded data parse too.
- Workflows: `WorkflowEnvironment.start_time_skipping()` with fake activities.
- End-to-end smoke: `mockoon/smoke.sh` pointed at the real API using a dev-only header session (`ENV=local` + `DEV_AUTH_HEADER=true`, refused in production).

## 8. Deployment
AWS topology (user, 2026-10-19): VPC with 2 public subnets (nginx, NAT gateway), 2 private backend subnets (EC2: api, worker, projector), 2 private data subnets (RDS PostgreSQL; EC2 hosting Temporal, SuperTokens, Elasticsearch), S3 for media, SSM Session Manager for access, optimised for lowest monthly cost. Implemented in its own plan. Requirements carried over: TLS on `api.prasang.in`, images built in GitHub Actions, migrations on deploy, nightly backups of `prasang` + `supertokens` to S3.

## 9. Out of scope (post-launch)
React Native apps (separate epic), review submission, favourites, referrals, AI bio/semantic search, Instagram/Facebook/YouTube feed auto-import (Graph/Data APIs), admin UI, analytics dashboard beyond the contract.
