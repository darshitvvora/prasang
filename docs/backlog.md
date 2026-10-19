# Prasang — Backlog

**Status date:** 2026-10-19 · Legend: `[x]` done · `[~]` in progress · `[ ]` todo · 🔑 needs an account/credential from you

**Source of truth:** spec [backend design v2](superpowers/specs/2026-09-29-backend-mvp-design.md) · API [contract](../contracts/README.md) · plans [A](superpowers/plans/2026-09-29-plan-a-api-contract-mock-ui.md), [B](superpowers/plans/2026-10-19-plan-b-backend.md)

**Stack (locked 2026-10-19):** React web + React Native (Android/iOS) clients · FastAPI · PostgreSQL 16 (writes) · **Elasticsearch 8 for all UI search/listing reads** (CQRS via outbox projector) · SuperTokens self-hosted (Google + phone OTP) · Temporal self-hosted on Postgres · Amazon S3 · Razorpay · MSG91 / Resend · deploy on **AWS**, rehearsed first on **LocalStack** (Docker).

**Release order (decided 2026-10-19): web first.** EF follow-ups → EG LocalStack AWS simulation → ED AWS deploy → web go-live. React Native (EC) starts after the web release.

---

## EA — API contract & mock UI ✅ (Plan A, merged to `main`)
- [x] Contract conventions, error codes, TypeScript contract types
- [x] Canonical request/response examples with compile-time shape check
- [x] Mockoon mock API + smoke test
- [x] Typed API client, TanStack Query, Vite proxy
- [x] Auth provider (mock mode), role guards, shared login/signup with profile step
- [x] Home, search (URL filters, pagination), profile, contact modal → leads
- [x] Artist onboarding/edit, media, dashboard, leads (locked leads, status actions)
- [x] Planner dashboard/inquiries, pricing + Razorpay checkout (mocked)
- [x] Review fixes: outage ≠ sign-out, expired sessions, no-profile routing, plan-change contract

## EB — Backend & whole app running locally ✅ (Plan B, branch `feat/plan-b-backend`)
**Goal:** `docker compose up` → full app on http://localhost:5173 with real API, auth, search, workflows.

**S1 Local infrastructure**
- [x] B1 Postgres (prasang, prasang_test, supertokens, temporal, temporal_visibility), Elasticsearch 8.19, Temporal 1.32 (server + schema job + namespace job + UI :8080), SuperTokens core 12.3 — `scripts/stack-health.sh`

**S2 API foundation**
- [x] B2 FastAPI scaffold: config, async SQLAlchemy, error contract (incl. 422 → `details.fields`), `/healthz` `/readyz`, pytest harness
- [x] B3 Pydantic contract models + contract tests; contract additions: Facebook embeds, `Media.embedUrl`, `facebookUrl`, `GET /auth/providers`
- [x] B4 Schema migration + seed (localities, plans, 12 demo artists, demo leads)

**S3 Identity**
- [x] B5 SuperTokens: phone OTP (code in API logs locally) + Google (🔑 Google OAuth client), cookie + header sessions (web + mobile), `/me`

**S4 Artists & media**
- [x] B6 Artist profile CRUD, public profile, Instagram/YouTube/Facebook post embeds + profile widgets (Facebook page timeline, Instagram profile, YouTube channel), daily stats, dashboard (🔑 optional YouTube Data API key for @handle channels)
- [x] B7 Media uploads to S3 (🔑 AWS dev bucket + credentials for uploads; embeds work without), quotas

**S5 Search (Elasticsearch read side)**
- [x] B8 Outbox projector → Elasticsearch; search, suggestions, featured, similar — all UI listing reads from ES

**S6 Leads & notifications**
- [x] B9 Leads with quota locking (concurrency-safe), artist leads, planner inquiries, plan usage
- [x] B10 Temporal worker + `LeadNotificationWorkflow` (console notifier locally; 🔑 MSG91/Resend in prod)

**S7 Monetisation**
- [x] B11 Plans, 7-day trial (`TrialWorkflow`), subscriptions (`SubscriptionWorkflow`), fake gateway locally (🔑 Razorpay test/live keys later), webhooks

**S8 Hardening from review** ✅
- [x] Razorpay webhook state machine + retry-safe processing; plan change cancels the old subscription at the gateway
- [x] Locked leads unlock up to the new plan's limit on any upgrade/trial
- [x] `scheduler` service sweeps missed lead notifications, overdue trials/subscriptions, expired leads
- [x] Upload size/type/kind enforced (signed size + confirm checks)
- [x] OTP SMS rate limits (5/phone/h, 20/IP/h)
- [x] Fail closed on public domains without `ENV=production`; configurable API/session domain for split deploys

**S8 Web app on the real backend**
- [x] B12 React: SuperTokens auth mode (OTP + Google callback), Facebook embeds, iframes on profile
- [x] B13 Everything in `docker compose` (api, worker, projector, migrate+seed, web); Plan A smoke passes against the real API; runbook

## EF — Follow-ups from review (before go-live) `[ ]` ← next
- [ ] F1 Search: map ES timeouts/missing index to 503 `search_unavailable`
- [ ] F2 Store canonical social link URLs; unique `storage_key`
- [ ] F3 Projector: external versioning for >1 instance; isolate poison events
- [ ] F4 Lock artist row in trial end vs activation; IST date in verify; gateway errors → 502/503 on cancel
- [ ] F5 Planner daily limit serialised; production build defaults to SuperTokens auth; JSON logs; hide API docs in production; require MSG91 notifier in production
- [ ] F6 Decide: proration on plan change; how Razorpay plan ids survive re-seeding

## EL — Web launch readiness (feature-complete web) `[~]` ← next, before deployment
**Decided 2026-10-19:** finish these on the web before any deploy work. Design: [web launch readiness](superpowers/specs/2026-10-19-web-launch-readiness-design.md).

**Decisions log (change here; the design follows):**
- Not GST-registered → Razorpay's standard invoice is the receipt; enable Razorpay GST invoices after registration
- Reviews only for confirmed bookings; **either** artist ("booked") **or** planner ("Yes, I booked") confirms; planner's yes counts even if the artist declined or the inquiry expired
- Booking check-ins: 3 days after inquiry, then the day after the event if still unmarked (14 days after inquiry if no date); max 4 messages; SMS + email (WhatsApp with the copilot, EH)
- Google reviews shown separately with attribution; Prasang rating counts only verified reviews
- Admin at launch is CLI only; admin UI post-launch
- Grant-plan refused while a paid plan is live; replaces a running trial
- **Suspend** leaves billing running (temporary; refunds manually in Razorpay); **block** = suspend + cancel billing at Razorpay immediately *(recommended default — confirm)*
- Account deletion immediate after OTP re-confirm; payment records kept without contact details
- Production nginx/web image stay in ED/EG
- [ ] L1 Admin at launch = **CLI commands, no UI** (run on the server via SSM): verify/unverify, feature/unfeature, suspend/restore artist, grant plan for N days, hide/restore review, block user, sync subscription from Razorpay; each updates search via the outbox and writes an `admin_actions` log row
- [ ] L2 Link previews for shared profiles (Open Graph/Twitter tags: photo, name, type, city) for Instagram/WhatsApp
- [ ] L3 Reviews: only for confirmed bookings (artist marks booked **or** planner says yes); planner nudged 3 days after inquiry and again the day after the event if still unmarked (Temporal); review form opens after the event; artist reply + report; Google reviews shown separately with attribution (🔑 Google Places API key)
- [ ] L4 Billing history: list of charges with links to Razorpay's hosted invoice/receipt (not GST-registered yet — enable Razorpay GST invoices after registration)
- [ ] L5 Lifecycle messages: welcome, trial ending, renewal reminder, payment failed/plan ended (SMS + email)
- [ ] L6 Account and data deletion (DPDP Act, Google sign-in policy)
- [ ] L7 About and Contact pages (contact form emails the team)

## EG — AWS simulation on LocalStack (Docker) `[ ]`
**Goal:** rehearse the AWS deploy locally — same IaC, same S3/IAM/SSM wiring — before spending on a real account. Also makes photo/video uploads work locally with no AWS credentials.
- [ ] G1 LocalStack service in `docker compose` (S3, IAM, SSM Parameter Store, STS); confirm edition/licensing of the current LocalStack image (newer images may need a free auth token 🔑)
- [ ] G2 S3 on LocalStack for local uploads: bucket bootstrap (init hook), `S3_ENDPOINT_URL` for API + presigned URLs reachable from the browser, CORS for direct PUT; uploads pass in `mockoon/smoke.sh`
- [ ] G3 Secrets/config from SSM Parameter Store (`/prasang/{env}/…`) instead of `.env` in deployed envs; LocalStack locally
- [ ] G4 IaC (from D2) applied to LocalStack: VPC, 2 public + 4 private subnets, route tables, security groups, NAT, S3 + bucket policy, IAM roles — `plan`/`apply` clean against LocalStack
- [ ] G5 Gaps to note, not emulate: RDS and real EC2 VMs are not full emulations (Community edition runs the API, not the machines) — locally the app keeps using compose Postgres/containers; decide whether LocalStack Pro is worth it

## ED — Deploy on AWS (web release) `[ ]`
**Target topology (decided 2026-10-19):** one VPC · **2 public subnets** (nginx reverse proxy/TLS, NAT) · **2 private backend subnets** (EC2: FastAPI api, Temporal worker, outbox projector) · **2 private data subnets** (RDS PostgreSQL; EC2 for Temporal server, SuperTokens core, Elasticsearch) · **S3** for media · **NAT gateway** for outbound · **SSM Session Manager** for login (no SSH, no bastion) · goal: **lowest monthly cost**.
- [ ] D1 Cost estimate of the topology + cheaper variants to decide on: NAT gateway (~$32/mo/AZ + data) vs NAT instance (fck-nat t4g.nano); S3 gateway endpoint (free); single-AZ compute at launch; Graviton (t4g) sizes; RDS t4g.micro vs Postgres on EC2; public IPv4 charges 🔑 AWS account
- [ ] D2 Infrastructure as code (VPC, subnets, route tables, security groups, NAT, nginx EC2, private EC2s, RDS, S3 + CloudFront, IAM roles for SSM/S3) — validated on LocalStack first (EG4)
- [ ] D3 Service install on EC2 (docker compose per host: data host = Temporal + SuperTokens + Elasticsearch; app host = api + worker + projector), TLS for `api.prasang.in` on nginx
- [ ] D4 CI/CD (GitHub Actions build/test → images → deploy via SSM Run Command), Alembic migrations on deploy, nightly RDS snapshots + SuperTokens/ES backups
- [ ] D5 Web app hosting (S3 + CloudFront or nginx), production build with `VITE_AUTH_MODE=supertokens`, DNS for `prasang.in`
- [ ] D6 Go-live checklist: Razorpay live + webhook URL 🔑, MSG91 DLT 🔑, Google OAuth production consent 🔑, SES/Resend domain 🔑 — start Razorpay KYC and MSG91 DLT now (days–weeks)

## EC — React Native apps (Android + iOS) `[ ]` — after the web release
- [ ] C1 Expo/React Native project sharing `frontend/src/api/types.ts` (move to a shared `packages/contract`)
- [ ] C2 Auth with `supertokens-react-native` (header-token sessions), phone OTP + Google
- [ ] C3 Planner flows: search, profile with embeds, contact artist, inquiries
- [ ] C4 Artist flows: onboarding, media upload (presigned S3), leads, push notifications for new leads (FCM/APNs) 🔑 Apple/Google developer accounts
- [ ] C5 Store builds via EAS, internal testing tracks

## Post-launch
Admin web UI (overview counts, artist/payment/review screens, activity log viewer); favourites/shortlist, compare, recently viewed; locality pages, trending/new/top-rated, map/nearby; referrals; AI bio + semantic search; Instagram/Facebook/YouTube feed auto-import (Graph/Data APIs; 🔑 Meta app review); full analytics page; blog; Spotify embeds; ticketing (tixcraft/Insider).

## EH — AI event-planning copilot (post-launch, direction of the product) `[ ]`
**Vision (2026-10-19):** Prasang grows from a directory into a **personal agent for event booking** — an AI copilot that helps a planner plan and run an event end to end, available **on WhatsApp and in our app** (web + React Native).
- [ ] H1 Discovery: conversations the copilot must handle (brief → shortlist → contact → follow-up → booking → day-of checklist); success measures
- [ ] H2 WhatsApp channel 🔑 WhatsApp Business API (Meta) via MSG91/Gupshup/Meta Cloud API; in-app chat
- [ ] H3 Agent core: tools over existing APIs (search, artist detail, create lead, inquiries, reviews), durable conversations/reminders on Temporal
- [ ] H4 Semantic artist matching (embeddings) feeding the copilot's shortlist
- [ ] H5 Guardrails: no contact sharing without the planner's consent, human handoff, cost caps per conversation
