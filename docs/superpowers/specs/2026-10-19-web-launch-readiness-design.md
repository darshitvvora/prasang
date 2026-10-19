# Web launch readiness — design

**Date:** 2026-10-19 · **Backlog epic:** EL (L1–L7) · **Branch:** `feat/web-launch` (from `feat/plan-b-backend`)
**Decisions:** the backlog's EL decisions log is authoritative; this document carries the detail.
**Builds on:** [backend design v2](2026-09-29-backend-mvp-design.md), [API contract](../../../contracts/README.md)

## Why

Prasang ships on the **web first**, and the owner wants the site feature complete before any deployment work (LocalStack, AWS). Launch day picture: an artist shares their Prasang profile on Instagram/WhatsApp, a planner opens it, contacts the artist, books them, and leaves a review. Today that loop works up to "contacts the artist". What's missing is what a real business needs on day one: trust (verified reviews, About/Contact), operations (admin actions), money hygiene (receipts), retention (lifecycle messages), compliance (account deletion), and marketing (link previews).

Long-term direction (post-launch, backlog EH): Prasang becomes a **personal agent for event booking** — an AI copilot on WhatsApp and in the app. Design choices here should not block that: booking confirmations and nudges become the copilot's first jobs.

## Goals

1. **L1 Admin actions via CLI** — the owner can verify, feature, suspend, grant plans, hide reviews, block users and repair subscriptions without a UI and without editing the database by hand.
2. **L2 Link previews** — a shared `/profile/{slug}` link unfurls with the artist's photo, name, type and city on WhatsApp, Instagram, Facebook, X.
3. **L3 Verified reviews** — only planners whose inquiry became a booking can review; planners are nudged to confirm the booking; Google reviews shown separately.
4. **L4 Billing history** — artists see their charges and open Razorpay's receipt.
5. **L5 Lifecycle messages** — welcome, trial ending, annual renewal reminder, payment failed, plan ended.
6. **L6 Account deletion** — self-serve, immediate, compliant with India's DPDP Act and Google sign-in policy.
7. **L7 About and Contact pages.**

## Non-goals (now)

- Admin web UI (post-launch backlog). No impersonation, no editing artist content, no refunds (Razorpay dashboard), no charts, no admin permission levels.
- Generating our own invoices or GST handling — the owner is **not GST-registered**; Razorpay's standard invoice serves as the receipt. After registration, turn on GST invoicing in the Razorpay dashboard (verify availability during KYC).
- WhatsApp as a channel for nudges/lifecycle (comes with the copilot, EH). SMS + email only.
- Server-side rendering of the whole app. Only preview tags are rendered server-side.
- Review photos/videos, review voting, AI review summaries.

## Anti-goals (would be a failure even if it "works")

- An artist can block a bad review by never marking the booking — **either side's confirmation must unlock the review**.
- Admin actions that leave search (Elasticsearch) out of sync with Postgres — every artist-visible change goes through the existing outbox (`artist_changed`).
- A deleted artist keeps getting billed, or a deleted user's phone/email remains visible to anyone.
- Planners spammed: **at most 4 nudge messages per inquiry**, stop as soon as anyone answers.
- Showing Google reviews in a way that violates Google's terms (missing attribution, long-term storage of review text).

## Constraints

- Existing stack and patterns: FastAPI + async SQLAlchemy, Alembic (next migration `0006`), Pydantic camelCase contract, contract-first (`contracts/README.md` + `frontend/src/api/types.ts` + examples + Mockoon routes updated together; Plan A smoke must keep passing on both Mockoon and the real API).
- Writes in Postgres; artist-visible reads (search/listing) via Elasticsearch through the outbox projector. Profile detail reads follow whatever they do today.
- Timers/durable follow-ups on **Temporal** (self-hosted), with the existing `scheduler` sweeper as the safety net when Temporal was unreachable (same pattern as `notification_started_at`).
- Notifications through the existing `Notifier` (console locally, MSG91 SMS / Resend email in production). SMS text must fit a DLT template later — keep each SMS one short sentence plus a link.
- Everything must run locally with `docker compose up` and no third-party accounts; features needing a key (Google Places) degrade to "not shown".
- Never add AI/Claude co-author lines to commits, PRs or files.
- Verification by tests, `tsc`/build and curl — not browser automation.

## Design

### L1 Admin via CLI

- New CLI group `python -m app.cli admin <action> …` (run on the server via SSM; locally via `docker compose exec api`).
- Actions:

| Command | Effect |
|---|---|
| `make-admin <phone\|user-id>` | sets `users.role = admin` (admin also keeps API access to everything via `require_role`) |
| `verify <slug>` / `unverify <slug>` | `is_verified` |
| `feature <slug>` / `unfeature <slug>` | manual feature flag, kept even when the plan doesn't grant it (new column `featured_override`); search boost unchanged |
| `suspend <slug> --reason "…"` / `restore <slug>` | new `artist_profiles.suspended_at` + `suspension_reason`; billing keeps running (refunds manually in Razorpay); suspended artists are excluded from search/featured/similar and their profile returns 404 publicly; the artist sees a banner with the reason in their dashboard; new leads to them are refused |
| `grant-plan <slug> <tier> --days N --reason "…"` | sets tier with `tier_source = "grant"` and `grant_ends_at`; sweeper/Temporal timer downgrades at the end (reuse trial-end mechanics); a later paid activation replaces it. Refused while the artist has a live paid subscription (for "paid but no plan" use `sync-subscription`); replaces a running trial. *(Builder-check call.)* |
| `hide-review <id> --reason` / `restore-review <id>` | `reviews.hidden_at`; hidden reviews excluded from profile and rating aggregates |
| `block-user <phone\|user-id> --reason` / `unblock-user …` | `users.blocked_at`; revoke all SuperTokens sessions; `current_user` rejects blocked users with 403 `account_blocked`; an artist who is blocked is also suspended and their live subscription is cancelled at the gateway immediately |
| `sync-subscription <slug>` | fetch subscription(s) from the gateway and run them through the existing webhook state machine (`handle_webhook`) |
| `reports` | list open review reports and deletion/contact messages (plain table output) |

- Every action writes an `admin_actions` row: `id, actor (OS user or "cli"), action, target_type, target_id, reason, payload json, created_at`. `--reason` is required for suspend, grant-plan, hide-review, block-user.
- Every artist-visible change calls `artist_changed()` so the projector updates Elasticsearch.

### L2 Link previews

- Social crawlers don't run JavaScript, so `/profile/{slug}` must return HTML that already contains the tags.
- The API serves `GET /profile/{slug}` (outside `/api/v1`) by taking the built web app's `index.html` and injecting into `<head>`: `<title>`, `meta description`, `og:title` ("Arjun Mehta · DJ · Mumbai"), `og:description` (first ~160 chars of bio), `og:image` (profile photo, absolute URL; fallback Prasang default card), `og:url`, `og:type=profile`, `twitter:card=summary_large_image`. The SPA then boots normally, so people and crawlers get the same URL.
- Unknown/suspended/unpublished slug → index.html with the generic Prasang tags (the SPA shows its own not-found).
- All other pages get generic Prasang tags baked into `frontend/index.html` (also fix its `<title>frontend</title>`).
- Production: nginx routes `/profile/` to the API, everything else to static files. Locally the web app runs on the Vite dev server, so the mechanism there is the **builder's call**; the requirement is that `curl http://localhost:5173/profile/<slug>` shows the artist's `og:` tags and the page still works in a browser.
- Values are HTML-escaped (artist names/bios are user input).

### L3 Verified reviews and booking confirmation

**Booking confirmation**
- A booking is confirmed when **either** the artist marks the lead `converted` (existing transition) **or** the planner answers "Yes, I booked" on the inquiry.
- New lead columns: `booking_confirmed_at`, `booking_confirmed_by` (`artist` | `planner`), `planner_answer` (`booked` | `not_booked` | `deciding` | null), `planner_answered_at`.
- Booking confirmation is stored **separately from the artist's lead status**, so neither side can block the other. Planner "Yes" also moves the lead to `converted` if it was `new`, `contacted` or `expired` (the nightly expiry job turns past-dated `new` leads into `expired`, often the same day check-in 2 goes out). If the artist had marked it `declined`, the status stays `declined` but the booking is still confirmed and the review allowed; the artist can report the review. *(Builder-check call.)* Planner "No" does not change the artist's lead status.
- **Locked (over-quota) leads** get follow-ups and reviews like any other — the planner side is unaffected by the artist's quota; the artist sees the confirmation once the lead unlocks. *(Builder-check call.)*
- Planner inquiries page gets per-inquiry actions: **Booked** / **Not booked** / **Still deciding**, and **Write a review** when eligible.

**Nudges (Temporal `BookingFollowUpWorkflow`, one per lead, started with the lead notification)**
1. **Check-in 1** — 3 days after the inquiry: SMS + email to the planner: "Did you book {artist} for your {event}?" with a link to the inquiry. If unanswered, one reminder 2 days later.
2. **Check-in 2** — only if still no confirmation and no planner answer: the day after the event date (or 14 days after the inquiry when no date). Reminder once, 2 days later.
- Stop immediately when the booking is confirmed by either side or the planner answers `booked`/`not_booked`. "Still deciding" skips to check-in 2. Max 4 messages per inquiry.
- Signals from the API (`answered`, `confirmed`) end/advance the workflow; the sweeper starts any follow-up that Temporal missed (column `followup_started_at`).
- Links go to the planner's inquiries page; the planner signs in (OTP) if needed. No magic-login links (security).
- Leads created before this release get no follow-up.

**Reviews**
- Eligibility: the planner of a confirmed-booking lead, **after the event date** (or immediately if no date), one review per lead.
- Fields as today (rating 1–5, event type and month from the lead, text 20–2000 chars) plus `lead_id` (unique), `planner_id`, `artist_reply`, `artist_replied_at`, `hidden_at`, `hidden_reason`.
- The planner can edit their review for 7 days after posting. The artist can post **one public reply** (editable). The artist can **report** a review with a reason → `review_reports` row, listed by `admin reports`.
- Reviews go live immediately. Rating aggregates (`average_rating`, `total_reviews`) recalc on create/edit/hide/restore and propagate to search via the outbox.
- Profile shows "Booked via Prasang" on each review. Existing seeded reviews stay (marked as seed data; no `lead_id`).
- When check-in 2 gets a "Yes", the planner lands on the review form directly.

**Google reviews**
- Artist adds a Google Maps link to their Google Business listing in profile edit (optional field `googlePlaceUrl`); the backend resolves it to a Place ID (store `google_place_id`).
- Profile shows a separate "From Google" block: Google rating, review count, up to 5 reviews, author names, relative times, Google attribution and a link to the listing. Prasang's star rating counts only verified reviews.
- Fetched via Google Places API (New) Place Details; cached in memory/short TTL (≤ 24 h), never stored long-term beyond the Place ID. No key configured (`GOOGLE_PLACES_API_KEY`) → block not shown, field still saved.
- Admin can clear a wrong/abusive Place ID via `admin` CLI (`clear-google-place <slug>`).

### L4 Billing history

- New table `subscription_payments`: `id, subscription_id, gateway_payment_id (unique), gateway_invoice_id, amount (paise), currency, status (paid|failed), paid_at, receipt_url`.
- Filled from `subscription.charged` webhooks (and `payment.failed` if received) and from `verify` on first activation; `sync-subscription` back-fills from the gateway.
- `GET /subscriptions/me/payments` → list (date, plan, cycle, amount, status, receipt URL). Shown on the artist's subscription section ("Billing history").
- Receipt URL = Razorpay's hosted invoice (`short_url`). FakeGateway produces a local fake receipt URL.
- Razorpay already emails its own receipt; we send no duplicate email.

### L5 Lifecycle messages

All via the Notifier (SMS + email when the user has an email), sent from Temporal activities or existing workflows:

| Message | When | Who |
|---|---|---|
| Welcome | after `POST /me` (profile created) — artist version links to onboarding, planner version to search | new user |
| Trial ending | 2 days before `trial_ends_at` (inside the existing `TrialWorkflow`) | artist |
| Renewal reminder | 7 days before an **annual** renewal (inside `SubscriptionWorkflow`) | artist |
| Payment failed | `subscription.halted` / `payment.failed` webhook | artist |
| Plan ended | when a trial, grant or paid plan downgrades to Free | artist |

- Each message is sent at most once per (user, kind, period) — `notifications_sent` table with a unique key, so retries/sweeps never double-send.
- Plain text, one short SMS sentence plus link; email slightly longer. No marketing messages.

### L6 Account deletion

- Settings section (artist and planner) → "Delete my account" → confirm with a fresh phone OTP (SuperTokens passwordless; Google-only users re-confirm via Google) → `DELETE /me`.
- Immediate, no grace period. In one transaction plus follow-up jobs:
  - **Artist:** cancel live gateway subscription(s) immediately; profile removed (unpublished + anonymised: name "Former artist", contact fields cleared) and removed from search; media files deleted from S3 (background job, retried); planners' inquiries show "Artist no longer on Prasang"; reviews about them are hidden.
  - **Planner:** their leads keep event details but `planner_name` → "Deleted user", phone/email cleared; their reviews stay as "Verified booking — former user"; pending follow-up workflows cancelled.
  - **Both:** `users` row anonymised (keep id for foreign keys, clear phone/email/name/avatar, set `deleted_at`); SuperTokens user deleted (sessions revoked); welcome/lifecycle stop.
  - **Kept:** subscription and payment records (financial record-keeping) with no contact details.
- An `admin_actions`-style audit row with kind `self_delete`.
- After deletion the same phone can sign up again as a brand-new user.

### L7 About and Contact

- `/about`: what Prasang is, for artists and for planners, no-commission model, contact details.
- `/contact`: form (name, phone or email, topic: general / artist support / payments / report a problem, message) → `POST /contact` → stored in `contact_messages` and emailed to `SUPPORT_EMAIL`. Rate-limited per IP (e.g. 5/hour). Also shows support email/phone and business address placeholders the owner fills via config (Razorpay KYC checks these).
- Footer links on every page: About, Contact, Pricing, Privacy, Terms, Cookies.

## Contract changes (summary)

New/changed endpoints (exact shapes are the builder's to define in `contracts/README.md` + types + examples + Mockoon):
`GET /profile/{slug}` (HTML, outside `/api/v1`) · `PATCH /leads/{id}/planner-answer` (planner) · `POST /reviews` · `PATCH /reviews/{id}` (planner, 7 days) · `PUT /reviews/{id}/reply` (artist) · `POST /reviews/{id}/report` (artist) · `GET /artists/{slug}/google-reviews` · `GET /subscriptions/me/payments` · `DELETE /me` · `POST /contact`.
Changed: `Review` gains `verified`, `artistReply`; `PlannerInquiry` gains booking/answer/review-eligibility fields; `ArtistProfile` gains `googlePlaceUrl`, `suspended` + `suspensionReason` (own view only); new error codes `account_blocked`, `review_not_allowed`, `review_exists`, `artist_suspended`.

## Testing

- Backend: unit + API tests per feature (pytest, compose Postgres/ES), Temporal time-skipping tests for `BookingFollowUpWorkflow` (each branch: artist confirms, planner yes/no/deciding, no event date, max 4 messages) and the new lifecycle timers; CLI tests for each admin command (including that search reflects suspend/feature).
- Frontend: vitest for new pages/logic; `tsc` + build.
- Contract: examples validated by Pydantic tests and TS compile check; Mockoon smoke extended for new endpoints, passing on both Mockoon and the real API.
- Manual curl checks: `/profile/{slug}` tags; deletion flow end to end.

## Left to the builder

- Exact payload shapes, component layout and copy (plain, friendly, Indian English).
- Local dev mechanism for profile preview HTML (L2), as long as the curl check passes.
- Place ID resolution approach for Google Maps share links.
- Whether lifecycle messages are activities inside existing workflows or small new workflows, keeping the at-most-once table.
- Production nginx config and the production web image are **out of scope** (deployment epics ED/EG); the API reads `index.html` from a configurable path, served locally. *(Builder-check call.)*
- Task order; suggested: L7 → L2 → L1 → L4 → L5 → L3 → L6 (deletion last because it touches everything).
