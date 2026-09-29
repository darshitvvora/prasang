# Prasang Backend MVP — Backlog

Spec: [docs/superpowers/specs/2026-09-29-backend-mvp-design.md](superpowers/specs/2026-09-29-backend-mvp-design.md)

Legend: `[ ]` todo · `[x]` done · 🔑 = needs an external account/credential from you

---

## E0 — Foundation
**S0.1 As a developer I can run the whole backend locally with one command.**
- [ ] T0.1.1 Scaffold `backend/` with uv, FastAPI app factory, config (pydantic-settings), `/healthz`, `/readyz`
- [ ] T0.1.2 `docker-compose.yml`: postgres 16, elasticsearch 8, Temporal dev server, MinIO, api (hot reload)
- [ ] T0.1.3 Async SQLAlchemy 2.0 engine/session, Base, Alembic (async env), first empty migration
- [ ] T0.1.4 Error model + domain exception handler, request-id + JSON logging, CORS
- [ ] T0.1.5 pytest harness: test DB schema per session, truncate per test, httpx AsyncClient fixture
- [ ] T0.1.6 GitHub Actions CI: ruff + pytest with Postgres/ES service containers

## E1 — Identity (Supabase Auth)
**S1.1 As a signed-in user my Supabase token is accepted by the API.**
- [ ] T1.1.1 JWKS verifier (cache, kid refetch, iss/aud/exp checks) + `AUTH_MODE=local` HS256 with production guard
- [ ] T1.1.2 `current_user` / `require_role` dependencies
**S1.2 As a new user I pick my role (artist/planner) once.**
- [ ] T1.2.1 `users` model + migration
- [ ] T1.2.2 `GET /api/v1/me` (404 `profile_required`), `POST /api/v1/me`, `PATCH /api/v1/me`

## E2 — Artist profiles & media
**S2.1 As an artist I can create and edit my profile (onboarding).**
- [ ] T2.1.1 `artist_profiles` model + migration (enums, arrays), slug generator
- [ ] T2.1.2 `POST /api/v1/artists`, `GET/PATCH /api/v1/artists/me`, publish/unpublish
**S2.2 As a visitor I can open an artist profile by slug.**
- [ ] T2.2.1 `GET /api/v1/artists/{slug}` (published only, media included, no contact numbers), view counter
**S2.3 As an artist I can upload photos/videos and embeds within my tier limits.**
- [ ] T2.3.1 S3 storage client (MinIO local / R2 prod) with presigned PUT + HEAD
- [ ] T2.3.2 `artist_media` model; upload-url, confirm, delete, reorder endpoints; tier quotas
**S2.4 Seed data** — [ ] T2.4.1 `cli seed` loads the 12 mock artists + plans for local/dev

## E3 — Search (CQRS read side)
**S3.1 Every artist write is projected into Elasticsearch.**
- [ ] T3.1.1 `outbox_events` model + `emit()` helper used in artist/subscription services
- [ ] T3.1.2 ES client, index mapping (`artists_vN` + alias), document builder from Postgres
- [ ] T3.1.3 Projector loop (SKIP LOCKED batch, dedupe, reload, upsert/delete, retry bookkeeping) + `projector` process
- [ ] T3.1.4 `cli create-index` / `cli reindex` (alias swap)
**S3.2 As a planner I can search and filter artists.**
- [ ] T3.2.1 Query builder: filters, fuzzy multi_match, function_score boost, sorts, pagination, facets
- [ ] T3.2.2 `GET /api/v1/search/artists`, `GET /api/v1/search/suggestions`, `GET /api/v1/artists/featured`

## E4 — Leads & inquiries
**S4.1 As a planner I get an artist's contact info by sharing event details.**
- [ ] T4.1.1 `leads` model + migration; create service (quota → `is_locked`, rate limit, duplicate guard)
- [ ] T4.1.2 `POST /api/v1/leads` returns contact numbers; starts workflow after commit (non-fatal on failure)
**S4.2 As an artist I'm notified instantly about new leads.**
- [ ] T4.2.1 Temporal client + worker process (local dev server / Temporal Cloud API key)
- [ ] T4.2.2 `Notifier` interface: console, MSG91 (WhatsApp + SMS), Resend (email)
- [ ] T4.2.3 `LeadNotificationWorkflow` + activities + time-skipping tests
**S4.3 As an artist I manage my leads; as a planner I track my inquiries.**
- [ ] T4.3.1 `GET /api/v1/leads/artist` (masking), `PATCH /api/v1/leads/{id}`, `GET /api/v1/leads/planner` (status mapping)
- [ ] T4.3.2 `cli expire-leads`, `cli resend-lead-notifications`

## E5 — Paid subscriptions (Razorpay + Temporal)
**S5.1 As an artist I can see plans and subscribe.**
- [ ] T5.1.1 `subscription_plans`, `subscriptions`, `payment_events` models + seed
- [ ] T5.1.2 Razorpay client (create/cancel subscription, signature verify) + `cli sync-razorpay-plans` 🔑 test keys
- [ ] T5.1.3 `SubscriptionWorkflow` (update `get_checkout`, activation wait, apply tier, renew/halt/cancel loop, grace timer, continue-as-new) + tests
- [ ] T5.1.4 `GET /plans`, `POST /subscriptions`, `POST /subscriptions/verify`, `GET /subscriptions/me`, `POST /subscriptions/cancel`
**S5.2 Razorpay webhooks drive subscription state reliably.**
- [ ] T5.2.1 Webhook endpoint: signature, idempotent `payment_events`, signal by subscription id
**S5.3 Paid tier changes search ranking and unlocks leads.** — [ ] T5.3.1 `apply_tier` / `downgrade_to_free` activities (boost, featured, outbox, unlock)

## E6 — Frontend integration
**S6.1 Login with Google via Supabase.** 🔑 Supabase project + Google OAuth client
- [ ] T6.1.1 supabase-js client, Google Identity Services button → `signInWithIdToken`, session store, role picker → `POST /me`
- [ ] T6.1.2 API client with bearer token; route guards for `/artist/*`, `/planner/*`
**S6.2 Replace mock data with API.**
- [ ] T6.2.1 Search page, home featured, profile page
- [ ] T6.2.2 Contact modal → `POST /leads`
- [ ] T6.2.3 Artist onboarding (profile + media upload), dashboard, leads page
- [ ] T6.2.4 Planner dashboard + inquiries
- [ ] T6.2.5 Pricing → subscribe via Razorpay Checkout

## E7 — Deploy & go-live
- [ ] T7.1 `deploy/docker-compose.prod.yml`, Caddyfile, arm64 multi-stage Dockerfile, `.env.example` 🔑 Oracle VM
- [ ] T7.2 GitHub Actions: build/push GHCR + SSH deploy + migrations
- [ ] T7.3 Temporal Cloud namespace + API key wiring 🔑 Temporal Cloud
- [ ] T7.4 Cloudflare: Pages project, R2 bucket + CORS, DNS for `prasang.in` / `api.prasang.in` 🔑 Cloudflare
- [ ] T7.5 Nightly backup + lead expiry cron container; restore runbook
- [ ] T7.6 Production smoke test checklist; Razorpay live keys + webhook URL 🔑 Razorpay live; MSG91 prod sender 🔑 MSG91

## Post-launch (not scheduled)
Reviews, favourites, referrals, localities pages, phone OTP (MSG91 SMS hook), AI bio + semantic search, Instagram/YouTube import, admin UI, analytics.
