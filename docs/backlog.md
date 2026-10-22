# Prasang — Backlog

**Status date:** 2026-10-19 · Legend: `[x]` done · `[~]` in progress · `[ ]` todo · 🔑 needs an account/credential from you

**Source of truth:** spec [backend design v2](superpowers/specs/2026-09-29-backend-mvp-design.md) · API [contract](../contracts/README.md) · plans [A](superpowers/plans/2026-09-29-plan-a-api-contract-mock-ui.md), [B](superpowers/plans/2026-10-19-plan-b-backend.md)

**Stack (locked 2026-10-19):** React web + React Native (Android/iOS) clients · FastAPI · PostgreSQL 16 (writes) · **Elasticsearch 8 for all UI search/listing reads** (CQRS via outbox projector) · SuperTokens self-hosted (Google + phone OTP) · Temporal self-hosted on Postgres · Amazon S3 · **PhonePe Payment Links** · MSG91 (SMS/WhatsApp) · SendPulse SMTP (email) · deploy on **AWS**, rehearsed first on **LocalStack** (Docker).

**Release order (decided 2026-10-19): web first.** EL web launch readiness ✅ → EF follow-ups → EG LocalStack AWS simulation → ED AWS deploy → web go-live. React Native (EC) starts after the web release.

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

## EB — Backend & whole app running locally ✅ (Plan B, merged to `main`)
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
- [ ] F6 Decide: proration on plan change (today a plan change starts a fresh period from the day it is paid; unused days of the old plan are lost)
- [ ] F7 Booking check-ins: re-check confirmation right before delivery; skip overdue steps when a follow-up starts late; add `workflow.patched` before changing BookingFollowUpWorkflow (runs last months)
- [ ] F8 Account deletion: retry SuperTokens user deletion (else the phone is locked out); blank planners' free-text lead notes; replace a deleted artist's name-based slug
- [ ] F9 Contact-form rate limit: use the client IP nginx sets, not the first X-Forwarded-For entry
- [ ] F10 Google reviews: validate place ids; cache failed lookups briefly (API cost)
- [ ] F11 Billing: `sync-subscription` should prefer the open/live link over the newest row
- [ ] F12 PhonePe sandbox run: confirm the webhook `Authorization` header format (plain SHA256 hex vs a prefix — both accepted today), payment `timestamp` unit (ms assumed) and that `cancel` on a paid link answers `BAD_REQUEST … terminal` 🔑 PhonePe sandbox keys
- [ ] F13 Vite dev plugin: encode the slug (dev only)
- [ ] F14 MSG91: confirm the WhatsApp Authentication template's copy-code button payload on the first real OTP 🔑 MSG91 WhatsApp

## EP — PhonePe payment links, SendPulse email, MSG91 WhatsApp (replaces Razorpay) — code ✅ (branch `feat/phonepe-msg91`), accounts `[ ]` ← do the accounts next
**Decided 2026-10-22:** no auto-debit. Every paid period is one PhonePe payment link, shown on the site and sent by email + WhatsApp;
the webhook (and status checks) mark it paid and set the artist's plan. Email over SMTP via SendPulse (free tier); WhatsApp (and SMS only if DLT is added later) via MSG91.
Each provider switches on by itself once its variables are set (see README → "Turning on real payments, email and SMS" — WhatsApp included).

**Decisions log:**
- Purchase / plan change: link valid **24 h**; the plan starts the day it's paid (plan change replaces the old plan at once, no proration — F6)
- Renewal: link sent **5 days** before the period ends, payable until the end of the **3-day grace**; paying early loses nothing (the new period follows the current one); unpaid → Free after grace
- "Cancel" = no more renewal links (and closes one already sent); the paid period runs out
- Missed webhooks: the "I've paid" button, the expiry timer and the scheduler (every 5 min, links older than 10 min) all ask PhonePe for the status
- Underpaid links, payments on deleted/blocked accounts and late payments of replaced links while another plan is live → not applied; listed in `admin reports` as `refund_needed`
- PhonePe's own SMS/email for links is **off** (we send our own wording); receipts = our "payment received" email

**Code (done):**
- [x] P1 `PhonePeGateway` (OAuth token cached + refreshed on 401; create / status / cancel; webhook `Authorization: SHA256(username:password)`), fake gateway locally
- [x] P2 Subscriptions as payment-link periods: `renews_id`, `payment_url`, `pay_by` (migration 0015); `pendingPayment` on `/subscriptions/me`; verify = status check
- [x] P3 Scheduler: renewal links, expire overdue links, reconcile open links; workflow waits until the link's pay-by time
- [x] P4 Messages: payment link, renewal link, payment received (WhatsApp/SMS + email); removed renewal reminder / payment failed
- [x] P5 `SmtpEmailer` (465 implicit TLS, else STARTTLS) replaces Resend; MSG91 and SMTP auto-enable from env
- [x] P6 Web: "Pay with PhonePe" panel with "I've paid" + background check on the pricing and plan pages; Razorpay checkout removed; Mockoon updated

**Accounts and setup (you) — in this order:**
- [ ] P7 **PhonePe Business account**: sign up at business.phonepe.com with PAN + bank account; finish KYC (business proof, the live website with About/Contact/Terms/Privacy/Refund pages — they review it)
- [ ] P8 **Ask for Payment Links API access** — it needs approval: write to the PhonePe Business team (dashboard → Help, or your onboarding contact) asking to enable "Payment Links API" for your merchant id
- [ ] P9 **Sandbox keys**: dashboard → Test Mode ON → Developer Settings → copy Client ID, Client Secret, Client Version into `.env` (`PHONEPE_ENV=sandbox`)
- [ ] P10 **Webhook**: Developer Settings → Webhook → Create: URL `https://<api-domain>/api/v1/subscriptions/webhook`, SHA256 auth, pick a username + long random password (same values in `PHONEPE_WEBHOOK_USERNAME` / `PHONEPE_WEBHOOK_PASSWORD`), events `paylink.order.completed` + `paylink.order.failed`. Locally, expose the API with a tunnel (e.g. `cloudflared tunnel --url http://localhost:8000`) to receive it
- [ ] P11 **Sandbox test** (F12): buy Pro monthly, pay with PhonePe's UAT test instruments, check the plan activates, the billing row and the "payment received" email; then fail one payment; then `admin sync-subscription`
- [ ] P12 **Go live**: Test Mode OFF → production keys + a production webhook; `PHONEPE_ENV=production`
- [ ] P13 **SendPulse**: create an account → SMTP → request SMTP access (they review new senders, ~1 day) → add and verify the sender `hello@prasang.in` → add SendPulse's **SPF and DKIM** DNS records for prasang.in (and a DMARC record `v=DMARC1; p=none`) → copy the SMTP password into `SMTP_PASSWORD` (`SMTP_USERNAME` = your SendPulse login email, `SMTP_HOST=smtp-pulse.com`, `SMTP_PORT=465`). Free tier: 12,000 emails/month
- [x] P16 MSG91 integration in code: one template per message type (`app/notifications/texts.py`); each type goes on WhatsApp (Meta template, no DLT) or SMS (DLT template) — SMS wins when both are set; OTP via a WhatsApp Authentication template; Pro/Premium lead alerts on WhatsApp; 200-with-error responses are failures; `python -m app.cli msg91-templates` checklist
- **Decided 2026-10-22: no DLT.** Without DLT no SMS reaches Indian numbers, so OTP and all messages go on **WhatsApp** (+ email). Basic (free) artists get lead alerts by **email only** (WhatsApp alerts stay a Pro/Premium perk); register DLT later and set `MSG91_SMS_TEMPLATE_*` to add SMS without code changes
- [ ] P14 **MSG91 WhatsApp** (Meta approval takes 1–3 days; start early):
  1. MSG91 account → KYC → copy the **Authkey** into `MSG91_AUTH_KEY`
  2. A phone number **not** already on WhatsApp (a new SIM or a landline) for the business sender
  3. MSG91 → WhatsApp → connect the number (Embedded Signup with your Facebook Business account) → finish **Meta Business verification** (business documents, prasang.in) — without it you're limited to 250 conversations/day
  4. Set the display name "Prasang" and profile picture; put the number with 91 in `MSG91_WHATSAPP_NUMBER`
  5. Run `python -m app.cli msg91-templates`; create every WhatsApp template it lists in MSG91 → WhatsApp → Templates, language `en`. **OTP**: category *Authentication*, code-expiry 10 minutes, *Copy code* button. All others: category *Utility*, body exactly as printed (`{{1}}`, `{{2}}`… in that order). Paste each approved template *name* into `MSG91_WHATSAPP_TEMPLATE_<TYPE>` — OTP first
  6. Top up WhatsApp prepaid balance in MSG91 (Meta charges per conversation: authentication and utility conversations are a few paise each in India)
  7. Restart (`docker compose up -d api worker scheduler`) and check: log in with your phone (the code arrives on WhatsApp), create a lead on your own profile from a planner account, and `msg91-templates` shows `[set]` / `Channel now: …=WhatsApp`
  8. Verify in the first real send (F14): the Authentication template's copy-code button parameter (`button_1` with `subtype: url`) — MSG91's spec doesn't show an authentication example
- [ ] P15 Refund policy page (PhonePe KYC asks for it): no refunds for used periods; mistaken double payments refunded within 7 days

## EL — Web launch readiness (feature-complete web) ✅ (Plan C, merged to `main` in #2)
**Decided 2026-10-19:** finish these on the web before any deploy work. Design: [web launch readiness](superpowers/specs/2026-10-19-web-launch-readiness-design.md) · plan [C](superpowers/plans/2026-10-19-plan-c-web-launch.md).

**Decisions log (change here; the design follows):**
- Not GST-registered → the "payment received" email is the receipt *(was Razorpay invoices; see EP)*
- Reviews only for confirmed bookings; **either** artist ("booked") **or** planner ("Yes, I booked") confirms; planner's yes counts even if the artist declined or the inquiry expired
- Booking check-ins: 3 days after inquiry, then the day after the event if still unmarked (14 days after inquiry if no date); max 4 messages; SMS + email (WhatsApp with the copilot, EH)
- Google reviews shown separately with attribution; Prasang rating counts only verified reviews
- Admin at launch is CLI only; admin UI post-launch
- Grant-plan refused while a paid plan is live; replaces a running trial
- **Suspend** leaves the paid period running (refunds manually on PhonePe); **block** = suspend + end the plan and cancel any open payment link *(recommended default — change here if you disagree)*
- Account deletion immediate after OTP re-confirm; payment records kept without contact details
- Production nginx/web image stay in ED/EG
- **Plans (2026-10-20, revised same day): three plans.** **Basic** = free (internal tier key `free`): no uploads, 3 leads/month, Instagram/YouTube/Facebook embeds + widgets. **Pro** ₹599: 5 photos + 1 video, 15 leads/month, embeds, boosted, no badge, not featured. **Premium** ₹1,199 unchanged: 50 photos + 8 videos + 2 HD, unlimited leads, badge, featured, top placement. Old Basic subscribers moved to Pro (migration 0014)
- Videos are **not compressed**: caps of 40 MB (HD 200 MB, Premium only)
- Downgrade: extras beyond the new limits (by the artist's display order; embeds on Free) are hidden at once and **deleted after 7 days** with SMS/email + warning; upgrading earlier restores them. The pricing page and the cancel dialog warn with exact counts first
- [x] L1 Admin at launch = **CLI commands, no UI** (run on the server via SSM): verify/unverify, feature/unfeature, suspend/restore artist, grant plan for N days, hide/restore review, block user, sync subscription from PhonePe; each updates search via the outbox and writes an `admin_actions` log row
- [x] L2 Link previews for shared profiles (Open Graph/Twitter tags: photo, name, type, city) for Instagram/WhatsApp
- [x] L3 Reviews: only for confirmed bookings (artist marks booked **or** planner says yes); planner nudged 3 days after inquiry and again the day after the event if still unmarked (Temporal); review form opens after the event; artist reply + report; Google reviews shown separately with attribution (🔑 Google Places API key)
- [x] L4 Billing history: one row per payment attempt (receipt = the payment-received email since EP)
- [x] L5 Lifecycle messages: welcome, trial ending, plan ended (SMS + email); payment link / renewal link / payment received since EP
- [x] L6 Account and data deletion (DPDP Act, Google sign-in policy)
- [x] L7 About and Contact pages (contact form emails the team)
- [x] L8 Plan entitlements: three plans (Basic free / Pro / Premium), media limits, video size caps + Premium HD slots, embeds on all plans, badge + featured on Premium only, downgrade warning + 7-day clean-up

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
- [ ] D6 Go-live checklist: PhonePe production keys + webhook URL 🔑, MSG91 DLT 🔑, Google OAuth production consent 🔑, SendPulse sender domain (SPF/DKIM) 🔑 — accounts in EP; start PhonePe approval and MSG91 DLT now (days–weeks)

## EC — React Native apps (Android + iOS) `[ ]` — after the web release
- [ ] C1 Expo/React Native project sharing `frontend/src/api/types.ts` (move to a shared `packages/contract`)
- [ ] C2 Auth with `supertokens-react-native` (header-token sessions), phone OTP + Google
- [ ] C3 Planner flows: search, profile with embeds, contact artist, inquiries
- [ ] C4 Artist flows: onboarding, media upload (presigned S3), leads, push notifications for new leads (FCM/APNs) 🔑 Apple/Google developer accounts
- [ ] C5 Store builds via EAS, internal testing tracks

## Post-launch
Server-side video compression (720p transcode; HD 1080p); admin web UI (overview counts, artist/payment/review screens, activity log viewer); favourites/shortlist, compare, recently viewed; locality pages, trending/new/top-rated, map/nearby; referrals; AI bio + semantic search; Instagram/Facebook/YouTube feed auto-import (Graph/Data APIs; 🔑 Meta app review); full analytics page; blog; Spotify embeds; ticketing (tixcraft/Insider).

## EH — AI event-planning copilot (post-launch, direction of the product) `[ ]`
**Vision (2026-10-19):** Prasang grows from a directory into a **personal agent for event booking** — an AI copilot that helps a planner plan and run an event end to end, available **on WhatsApp and in our app** (web + React Native).
- [ ] H1 Discovery: conversations the copilot must handle (brief → shortlist → contact → follow-up → booking → day-of checklist); success measures
- [ ] H2 WhatsApp channel 🔑 WhatsApp Business API (Meta) via MSG91/Gupshup/Meta Cloud API; in-app chat
- [ ] H3 Agent core: tools over existing APIs (search, artist detail, create lead, inquiries, reviews), durable conversations/reminders on Temporal
- [ ] H4 Semantic artist matching (embeddings) feeding the copilot's shortlist
- [ ] H5 Guardrails: no contact sharing without the planner's consent, human handoff, cost caps per conversation
