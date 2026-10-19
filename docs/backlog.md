# Prasang — Backlog

**Status date:** 2026-10-19 · Legend: `[x]` done · `[~]` in progress · `[ ]` todo · 🔑 needs an account/credential from you

**Source of truth:** spec [backend design v2](superpowers/specs/2026-09-29-backend-mvp-design.md) · API [contract](../contracts/README.md) · plans [A](superpowers/plans/2026-09-29-plan-a-api-contract-mock-ui.md), [B](superpowers/plans/2026-10-19-plan-b-backend.md)

**Stack (locked 2026-10-19):** React web + React Native (Android/iOS) clients · FastAPI · PostgreSQL 16 (writes) · **Elasticsearch 8 for all UI search/listing reads** (CQRS via outbox projector) · SuperTokens self-hosted (Google + phone OTP) · Temporal self-hosted on Postgres · Amazon S3 · Razorpay · MSG91 / Resend · deploy on **AWS**.

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

## EB — Backend & whole app running locally `[~]` (Plan B, branch `feat/plan-b-backend`)
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
- [ ] B6 Artist profile CRUD, public profile, Instagram/YouTube/Facebook URL embeds, daily stats, dashboard
- [ ] B7 Media uploads to S3 (🔑 AWS dev bucket + credentials for uploads; embeds work without), quotas

**S5 Search (Elasticsearch read side)**
- [ ] B8 Outbox projector → Elasticsearch; search, suggestions, featured, similar — all UI listing reads from ES

**S6 Leads & notifications**
- [ ] B9 Leads with quota locking (concurrency-safe), artist leads, planner inquiries, plan usage
- [ ] B10 Temporal worker + `LeadNotificationWorkflow` (console notifier locally; 🔑 MSG91/Resend in prod)

**S7 Monetisation**
- [ ] B11 Plans, 7-day trial (`TrialWorkflow`), subscriptions (`SubscriptionWorkflow`), fake gateway locally (🔑 Razorpay test/live keys later), webhooks

**S8 Web app on the real backend**
- [ ] B12 React: SuperTokens auth mode (OTP + Google callback), Facebook embeds, iframes on profile
- [ ] B13 Everything in `docker compose` (api, worker, projector, migrate+seed, web); Plan A smoke passes against the real API; runbook

## EC — React Native apps (Android + iOS) `[ ]`
- [ ] C1 Expo/React Native project sharing `frontend/src/api/types.ts` (move to a shared `packages/contract`)
- [ ] C2 Auth with `supertokens-react-native` (header-token sessions), phone OTP + Google
- [ ] C3 Planner flows: search, profile with embeds, contact artist, inquiries
- [ ] C4 Artist flows: onboarding, media upload (presigned S3), leads, push notifications for new leads (FCM/APNs) 🔑 Apple/Google developer accounts
- [ ] C5 Store builds via EAS, internal testing tracks

## ED — Deploy on AWS `[ ]`
**Target topology (decided 2026-10-19):** one VPC · **2 public subnets** (nginx reverse proxy/TLS, NAT) · **2 private backend subnets** (EC2: FastAPI api, Temporal worker, outbox projector) · **2 private data subnets** (RDS PostgreSQL; EC2 for Temporal server, SuperTokens core, Elasticsearch) · **S3** for media · **NAT gateway** for outbound · **SSM Session Manager** for login (no SSH, no bastion) · goal: **lowest monthly cost**.
- [ ] D1 Cost estimate of the topology + cheaper variants to decide on: NAT gateway (~$32/mo/AZ + data) vs NAT instance (fck-nat t4g.nano); S3 gateway endpoint (free); single-AZ compute at launch; Graviton (t4g) sizes; RDS t4g.micro vs Postgres on EC2; public IPv4 charges 🔑 AWS account
- [ ] D2 Infrastructure as code (VPC, subnets, route tables, security groups, NAT, nginx EC2, private EC2s, RDS, S3 + CloudFront, IAM roles for SSM/S3)
- [ ] D3 Service install on EC2 (docker compose per host: data host = Temporal + SuperTokens + Elasticsearch; app host = api + worker + projector), TLS for `api.prasang.in` on nginx
- [ ] D4 CI/CD (GitHub Actions build/test → images → deploy via SSM Run Command), Alembic migrations on deploy, nightly RDS snapshots + SuperTokens/ES backups
- [ ] D5 Web app hosting (S3 + CloudFront or nginx) and DNS for `prasang.in`
- [ ] D6 Go-live checklist: Razorpay live + webhook URL 🔑, MSG91 DLT 🔑, Google OAuth production consent 🔑, SES/Resend domain 🔑

## Post-launch
Review submission, favourites, referrals, AI bio + semantic search, Instagram/Facebook/YouTube feed auto-import (Graph/Data APIs; 🔑 Meta app review), admin UI, analytics.
