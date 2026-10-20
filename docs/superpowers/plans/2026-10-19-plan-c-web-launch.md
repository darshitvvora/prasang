# Plan C — Web Launch Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Prasang web app feature complete for launch: About/Contact, profile link previews, admin CLI, billing history, lifecycle messages, booking confirmation + verified reviews (+ Google reviews), and account deletion.

**Architecture:** Same stack and patterns as Plan B. Every API change is contract-first (README + Pydantic + TS types + examples + Mockoon). Durable follow-ups run on Temporal with the `scheduler` sweeper as the safety net; every outbound message goes through one queued, at-most-once `outbound_messages` table. Artist visibility is one rule (`is_public`) used by the public API, the projector and reindex.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Pydantic v2, Temporal Python SDK, SuperTokens python 0.31, Elasticsearch 8, React 19 + Vite 8 + TanStack Query 5, vitest, Mockoon CLI 9.8.

**Spec:** [docs/superpowers/specs/2026-10-19-web-launch-readiness-design.md](../specs/2026-10-19-web-launch-readiness-design.md) · decisions log: backlog epic EL ([docs/backlog.md](../../backlog.md)) is authoritative.

## Global Constraints

- Branch `feat/web-launch`. Never add AI/Claude co-author lines or "Generated with" footers to commits, PRs or files.
- Verification by pytest/vitest, `npx tsc -b`, `npm run build`, curl and `mockoon/smoke.sh` — **no browser automation**.
- Backend tests: `cd backend && uv run pytest` with compose `postgres` + `elasticsearch` up. Frontend: `cd frontend && npm test -- --run && npx tsc -b && npm run build`.
- One Alembic migration per task that changes schema, numbered from `0006`; after writing it, `docker compose run --rm migrate` must succeed (tests use `create_all`, so this is the only migration check).
- **Contract bundle (CB)** — every new/changed endpoint in a task updates, in the same commit: `contracts/README.md` (endpoint table + error codes), `backend/app/contract/*.py`, `frontend/src/api/types.ts`, a JSON example under `contracts/examples/…` registered in `backend/tests/contract/test_examples.py::TABLE` and `frontend/src/api/__contract__/examples.check.ts`, `frontend/src/api/endpoints.ts` (+ hook in `queries.ts` when a page uses it), and `mockoon/routes.mjs` (then `node mockoon/build.mjs`). Pydantic models use the existing `ContractModel` (camelCase aliases).
- Every artist-visible write calls `artist_changed(session, artist_id)` (app/outbox/emit.py) before commit.
- New error codes (exact): `account_blocked` 403, `artist_suspended` 409, `review_not_allowed` 403, `review_exists` 409, `review_locked` 409, `reauth_required` 403, `contact_rate_limited` 429, `grant_conflict` 409.
- Messages: SMS = one short sentence + one `https://prasang.in/…` link (base from `Settings.public_web_url`, default `http://localhost:5173`); email = subject + a few plain lines. Indian English, friendly, no marketing.
- Max 4 booking check-in messages per lead (2 check-ins × optional 1 reminder), counted per *message* (SMS+email of the same nudge = 1).
- Google reviews: never persist review text; cache ≤ 24 h in process; only `google_place_id` is stored.
- Local stack must keep working with no third-party keys: missing `GOOGLE_PLACES_API_KEY` → no Google block; missing `SUPPORT_EMAIL` → contact messages are only stored and logged.

## Review Focus

1. **Hostile profile text in link previews** — an artist named `"><script>alert(1)</script>` must produce escaped meta tags, never executable HTML (test in Task 2).
2. **Acting on someone else's inquiry or review** — a planner answering/reviewing another planner's lead, or an artist replying to/reporting a review of another artist, gets 404 (tests in Tasks 6 and 7).
3. **Confirmation arriving between check-ins** — if the artist marks "converted" after check-in 1 was sent, no further check-in messages go out (time-skipping test in Task 6).
4. **Suspended/blocked/deleted artists leaking back** — they must stay out of search, featured, similar and public profile after `reindex` and after any later profile edit by the projector (test in Task 3).
5. **Deleted user signs up again with the same phone** — they get a brand-new empty account; old inquiries stay anonymised and are not re-linked (test in Task 9).

---

### Task 1: About & Contact pages, site info, footer, generic meta (L7)

**Files:**
- Create: `backend/app/site/__init__.py`, `backend/app/site/models.py` (`ContactMessage`), `backend/app/site/router.py`, `backend/alembic/versions/0006_contact_messages.py`, `frontend/src/pages/AboutPage.tsx`, `frontend/src/pages/ContactPage.tsx`, `frontend/src/pages/site.css`, `frontend/src/pages/contactPage.test.ts`
- Modify: `backend/app/config.py`, `backend/app/main.py`, `backend/app/models.py`, `frontend/src/App.tsx`, `frontend/src/components/Footer.tsx`, `frontend/index.html`, CB files
- Test: `backend/tests/api/test_site.py`

**Interfaces:**
- Produces: `Settings.support_email: str | None`, `support_phone: str | None`, `business_address: str | None`, `public_web_url: str = "http://localhost:5173"`; `GET /site-info` → `SiteInfo {supportEmail, supportPhone, businessAddress}` (nulls allowed); `POST /contact` body `ContactRequest {name (1–120), contact (phone or email, 3–255), topic: 'general'|'artist_support'|'payments'|'report', message (10–4000)}` → 201 `{id}`; table `contact_messages(id uuid, name, contact, topic, message, ip, created_at)`; `index.html` generic block between `<!--og:start-->` and `<!--og:end-->` (Task 2 replaces it).

- [ ] **Step 1: Write failing tests** in `test_site.py`: `test_site_info_returns_configured_values` (override settings → exact values), `test_contact_stores_and_emails` (fake notifier captures `send_email(to=support_email, subject startswith "Contact: ")`, row exists), `test_contact_without_support_email_only_stores`, `test_contact_rate_limited_after_5_per_ip_per_hour` (6th → 429 `contact_rate_limited`), `test_contact_validation` (message of 5 chars → 422 `details.fields.message`).
- [ ] **Step 2: Run** `uv run pytest tests/api/test_site.py -v` — Expected: FAIL (404 routes).
- [ ] **Step 3: Implement** model, migration 0006, router (`site_router`, mounted under `/api/v1`), CB for both endpoints. Rate limit = count rows for the IP in the last hour (same idea as `otp_limits.py`). Send email via `get_notifier(settings).send_email`, failures logged, never fail the request.
- [ ] **Step 4: Run** the test file — Expected: PASS. `docker compose run --rm migrate` — Expected: exit 0.
- [ ] **Step 5: Frontend** — routes `/about`, `/contact`; About copy: what Prasang is, for artists (no commission, keep 100%), for planners (free), contact details from `/site-info`; Contact form with client validation mirroring the backend (unit-tested in `contactPage.test.ts`: `validateContact({...message:'short'})` returns `{message: 'Please write at least 10 characters'}`), success state "Thanks — we'll get back to you within 2 working days". Footer: replace `href="#"` placeholders for Success Stories/Referral with About and Contact links; legal links stay. `index.html`: `<title>Prasang — Find artists for every prasang</title>`, generic `description`, `og:title`, `og:description`, `og:image` (`/og-default.png`, add a 1200×630 PNG to `frontend/public/`), `og:type=website`, `twitter:card=summary_large_image` inside the marker comments.
- [ ] **Step 6: Run** frontend checks — Expected: tests pass, tsc clean, build OK.
- [ ] **Step 7: Commit** `feat(site): about and contact pages, site info, generic share tags`

### Task 2: Profile link previews (L2)

**Files:**
- Create: `backend/app/share/__init__.py`, `backend/app/share/meta.py`, `backend/app/share/router.py`, `frontend/vite-plugins/profileMeta.ts`
- Modify: `backend/app/config.py` (`web_index_path: str | None = None`), `backend/app/main.py` (share router mounted at root, not under `/api/v1`), `frontend/vite.config.ts`, `docker-compose.yml` (web service env `API_ORIGIN=http://api:8000` if not present)
- Test: `backend/tests/unit/test_share_meta.py`, `backend/tests/api/test_share.py`

**Interfaces:**
- Consumes: `get_public`-style visibility — use `is_public` from Task 3 if already present, else `is_published` (Task 3 swaps it).
- Produces: `share_meta(profile, settings) -> ShareMeta` (dataclass: title, description, image, url); `render_head(meta: ShareMeta) -> str` (escaped tag block, no markers); `inject(index_html: str, head: str) -> str` (replaces between `<!--og:start-->`/`<!--og:end-->`, keeps markers); routes `GET /profile/{slug}` (text/html full page; 404-free: unknown slug → generic index unchanged) and `GET /api/v1/artists/{slug}/share-head` (text/html fragment; unknown → 404).

- [ ] **Step 1: Failing unit tests** — `test_title_format` (`"Arjun Mehta · DJ · Mumbai"`), `test_description_truncates_bio_to_160_with_ellipsis`, `test_image_falls_back_to_default` (`{public_web_url}/og-default.png`), `test_render_escapes_hostile_name` (name `"><script>alert(1)</script>` → output contains `&quot;&gt;&lt;script&gt;` and not `<script>`), `test_inject_replaces_only_marked_block`.
- [ ] **Step 2: Failing API tests** — `test_profile_page_has_artist_tags` (with `web_index_path` pointing to a tmp index.html containing markers → body contains `og:title" content="Arjun Mehta · DJ · Mumbai"`), `test_profile_page_unknown_slug_serves_generic_index` (200, generic tags), `test_share_head_unknown_slug_404`, `test_profile_page_without_index_path_503`.
- [ ] **Step 3: Run** both files — Expected: FAIL.
- [ ] **Step 4: Implement** `meta.py` (use `html.escape(quote=True)`), router. `og:url` = `{public_web_url}/profile/{slug}`; `og:type=profile`.
- [ ] **Step 5: Run** — Expected: PASS.
- [ ] **Step 6: Vite dev plugin** `profileMeta()` using `transformIndexHtml` with `ctx.originalUrl`: for `/profile/<slug>` fetch `${API_ORIGIN ?? 'http://localhost:8000'}/api/v1/artists/<slug>/share-head` (1.5 s timeout); on 200 replace the marked block; on any failure return html unchanged. Register in `vite.config.ts`.
- [ ] **Step 7: Verify** with the stack up (`docker compose up -d --build api web`): `curl -s localhost:5173/profile/<seeded-slug> | grep 'og:title'` — Expected: the artist's title. `curl -s localhost:5173/ | grep 'og:title'` — Expected: generic Prasang title.
- [ ] **Step 8: Commit** `feat(share): link previews for artist profiles`

### Task 3: Admin CLI, visibility rule, suspension/block/grant (L1)

**Files:**
- Create: `backend/app/admin/__init__.py`, `backend/app/admin/models.py` (`AdminAction`), `backend/app/admin/actions.py`, `backend/app/admin/cli.py`, `backend/app/artists/visibility.py`, `backend/app/reviews/ratings.py`, `backend/alembic/versions/0007_admin.py`
- Modify: `backend/app/cli.py` (register `admin` subcommand group), `backend/app/artists/models.py`, `backend/app/auth/models.py`, `backend/app/reviews/models.py`, `backend/app/artists/service.py` (`get_public`), `backend/app/search/projector.py` (both `is_published` checks), `backend/app/leads/service.py` (`create_lead` refuses suspended), `backend/app/auth/deps.py` (`current_user`), `backend/app/subscriptions/service.py` (`_apply_tier` honours `featured_override`; grant handling), `backend/app/subscriptions/gateway.py` (`fetch_subscription`), `backend/app/sweeps.py` (`end_overdue_grants`), `backend/app/enums.py`/`contract/common.py` (tier source `grant`), `backend/app/contract/artists.py` (own profile: `suspended: bool`, `suspensionReason: str | None`), CB, `frontend/src/pages/artist/DashboardPage.tsx` (suspension banner)
- Test: `backend/tests/unit/test_admin_actions.py`, `backend/tests/api/test_visibility.py`

**Interfaces:**
- Produces:
  - Columns: `artist_profiles.suspended_at timestamptz null`, `suspension_reason text null`, `featured_override bool not null default false`, `grant_ends_at timestamptz null`; `users.blocked_at timestamptz null`, `users.deleted_at timestamptz null` (used in Task 9); `reviews.hidden_at`, `reviews.hidden_reason`.
  - `is_public(profile: ArtistProfile) -> bool` = `is_published and suspended_at is None`; SQL twin `public_filter()` returning the SQLAlchemy clause. Used by `get_public`, projector (deletes the doc when not public), `reindex_all`, `similar`.
  - `recalc_rating(session, artist_id) -> None` (avg/count over reviews with `hidden_at is null`; calls `artist_changed`).
  - `actions.py` async functions, each `(session, *, actor: str, …) -> None`, each writing `AdminAction(actor, action, target_type, target_id, reason, payload)` and committing: `make_admin(user_ref)`, `set_verified(slug, value)`, `set_featured(slug, value)`, `suspend(slug, reason)`, `restore(slug)`, `grant_plan(slug, tier, days, reason)`, `hide_review(review_id, reason)`, `restore_review(review_id)`, `block_user(user_ref, reason)`, `unblock_user(user_ref)`, `sync_subscription(slug)`, `clear_google_place(slug)` (column arrives in Task 8; until then the command is registered in Task 8). `user_ref` = 10-digit phone or user id.
  - `PaymentGateway.fetch_subscription(gateway_subscription_id) -> dict` (Razorpay subscription entity shape; FakeGateway returns `{"id", "status": "active", "current_end": <now+30d epoch>}`).
  - `current_user` raises 403 `account_blocked` when `blocked_at` set.
- Rules (from decisions log): suspend leaves billing; `block_user` on an artist also suspends and calls `gateway.cancel_subscription(id, at_cycle_end=False)` for live subs and runs the existing `end()` path; blocking revokes all SuperTokens sessions (`supertokens_python.recipe.session.asyncio.revoke_all_sessions_for_user`) — the CLI must `init_supertokens(settings, …)` first. `grant_plan` raises `grant_conflict` when a live paid subscription exists; replaces a running trial; sets `tier_source='grant'`, `grant_ends_at=now+days`; `end_overdue_grants` downgrades to free when past. `set_featured` sets `featured_override` and `is_featured = featured_override or plan.is_featured`. `sync_subscription` feeds `fetch_subscription` output to `handle_webhook` as `subscription.activated` when status active, `subscription.halted`/`cancelled`/`completed` otherwise.

- [ ] **Step 1: Failing tests** — `test_suspend_hides_from_public_search_and_similar` (suspend → `GET /artists/{slug}` 404, projector run → ES doc absent; `reindex` → still absent; artist PATCH bio → still absent), `test_restore_brings_back`, `test_suspended_artist_rejects_new_leads` (409 `artist_suspended`), `test_own_profile_shows_suspension_reason`, `test_block_user_rejects_requests` (403 `account_blocked`), `test_block_artist_cancels_live_subscription` (FakeGateway spy called with `at_cycle_end=False`), `test_grant_plan_sets_tier_and_expires` (sweep after end → free), `test_grant_refused_with_live_paid` (`grant_conflict`), `test_feature_override_survives_plan_change`, `test_hide_review_recalculates_rating`, `test_every_action_logs_admin_action` (parametrised over actions: row with actor/action/target), `test_reason_required` (suspend without reason → CLI exit code 2), `test_sync_subscription_activates_missed_payment`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** migration 0007, models, `visibility.py`, `ratings.py`, `actions.py`, gateway method (Razorpay: `GET /v1/subscriptions/{id}`), CLI (`python -m app.cli admin <command> …`; `--reason` required for suspend/grant-plan/hide-review/block-user; `--actor` default `$USER` or `cli`; prints one confirmation line). Add `end_overdue_grants` to `run_sweeps`. Dashboard banner: "Your profile is hidden: {reason}. Contact us at /contact."
- [ ] **Step 4: Run** test files + full backend suite — Expected: PASS. `docker compose run --rm migrate` — exit 0.
- [ ] **Step 5: Verify** `docker compose exec api python -m app.cli admin suspend <slug> --reason test` then `curl -s localhost:8000/api/v1/artists/<slug>` → 404; `admin restore <slug>` → 200.
- [ ] **Step 6: Commit** `feat(admin): CLI actions, suspension, block, plan grants, audit log`

### Task 4: Billing history and subscription page (L4)

**Files:**
- Create: `backend/app/subscriptions/payments.py`, `backend/alembic/versions/0008_subscription_payments.py`, `frontend/src/pages/artist/SubscriptionPage.tsx`, `frontend/src/pages/artist/billing.ts`, `frontend/src/pages/artist/billing.test.ts`
- Modify: `backend/app/subscriptions/models.py` (`SubscriptionPayment`), `backend/app/subscriptions/router.py` (webhook passes payment entity; new GET), `backend/app/subscriptions/service.py` (`handle_webhook(session, event, entity, payment: dict | None = None)`; `verify` records first payment), `backend/app/subscriptions/gateway.py` (`invoice_url(invoice_id) -> str | None`; Fake returns `{public_web_url}/receipts/mock/{invoice_id}`), `backend/app/admin/actions.py` (`sync_subscription` back-fills payments via `fetch_payments`), `frontend/src/App.tsx` (`/artist/subscription`), artist sidebar link, CB
- Test: `backend/tests/api/test_billing.py`

**Interfaces:**
- Produces: table `subscription_payments(id uuid, subscription_id fk, gateway_payment_id unique, gateway_invoice_id null, amount int paise, currency, status 'paid'|'failed', paid_at, receipt_url null)`; `record_payment(session, sub, payment_entity: dict) -> SubscriptionPayment | None` (idempotent on `gateway_payment_id`); `PaymentGateway.fetch_payments(gateway_subscription_id) -> list[dict]` (Fake: `[]`); `GET /subscriptions/me/payments` → `{items: BillingItem[]}` where `BillingItem {id, paidAt, tier, billingCycle, amount (rupees int), currency, status, receiptUrl | null}`, newest first.
- Consumes: `sync_subscription` from Task 3.

- [ ] **Step 1: Failing tests** — `test_charged_webhook_records_payment_with_receipt`, `test_duplicate_charged_webhook_records_once`, `test_payment_failed_webhook_records_failed_row` (event `payment.failed` with subscription id in payment notes/`subscription_id`), `test_verify_records_first_payment`, `test_payments_endpoint_lists_newest_first_for_own_artist_only`, `test_payments_endpoint_requires_artist`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; receipt URL resolved at record time via `invoice_url` (failure → null, logged).
- [ ] **Step 4: Run** — Expected: PASS; migrate exits 0.
- [ ] **Step 5: Frontend** `/artist/subscription`: current plan card (from `GET /subscriptions/me`), "Cancel at period end" button (existing `useCancelSubscription`, confirm dialog), Billing history table (date, plan, amount `₹599`, status, "Receipt" link opening in new tab; empty state "No payments yet"). `billing.ts` `formatBillingRow(item)` unit-tested (`amount 599 → '₹599'`, `status 'failed' → 'Failed'`).
- [ ] **Step 6: Run** frontend checks — Expected: pass.
- [ ] **Step 7: Commit** `feat(billing): payment history with Razorpay receipts; subscription page`

### Task 5: Outbound message queue and lifecycle messages (L5)

**Files:**
- Create: `backend/app/notifications/models.py` (`OutboundMessage` table — name the ORM class `QueuedMessage` to avoid clashing with the workflow dataclass), `backend/app/notifications/queue.py`, `backend/app/notifications/templates.py`, `backend/app/workflows/message.py` (`DeliverMessageWorkflow`), `backend/alembic/versions/0009_outbound_messages.py`
- Modify: `backend/app/workflows/starter.py` + `client.py` (`start_message`), `activities.py` (`MessageActivities.deliver_message`), `worker.py`, `backend/app/sweeps.py` (`retry_pending_messages`, `queue_due_reminders`), `backend/app/auth/router.py` (welcome on `POST /me`), `backend/app/subscriptions/service.py` (`downgrade_to_free` queues `plan_ended`; `handle_webhook` halted/`payment.failed` queues `payment_failed`)
- Test: `backend/tests/unit/test_message_queue.py`, `backend/tests/unit/test_templates.py`, `backend/tests/workflows/test_deliver_message.py`

**Interfaces:**
- Produces:
  - Table `outbound_messages(id uuid, user_id fk users, kind, period_key, context jsonb, status 'pending'|'sent'|'failed', attempts int, created_at, sent_at)`, unique `(user_id, kind, period_key)`.
  - `queue_message(session, user_id: str, kind: MessageKind, period_key: str, context: dict | None = None) -> uuid.UUID | None` — inserts with `ON CONFLICT DO NOTHING`, returns id or None; caller commits then calls `await get_starter().start_message(str(id))` (errors logged; sweeper retries `pending` older than 2 min).
  - `MessageKind = Literal['welcome_artist','welcome_planner','trial_ending','renewal_reminder','payment_failed','plan_ended','booking_check_1','booking_check_1_reminder','booking_check_2','booking_check_2_reminder']`.
  - `render(kind, user, context) -> RenderedMessage(sms: str, email_subject: str, email_text: str)`.
  - Activity `deliver_message(message_id: str) -> str` (skips if not pending or user `deleted_at`/`blocked_at` set; sends SMS when user has phone, email when user has email; marks `sent`); workflow id `msg-{message_id}`.
  - Period keys: welcome → `"once"`; trial_ending → trial end date ISO; renewal_reminder → `current_period_end` ISO; payment_failed → gateway payment id or `halted-{period_end}`; plan_ended → `"{source}-{date}"`; booking_* → lead id.
  - `queue_due_reminders(session, now)`: trial_ending for `tier_source='trial'` and `trial_ends_at` within 48 h; renewal_reminder for annual live subs with `current_period_end` within 7 days and not `cancel_at_period_end`.
- Exact SMS copy (templates.py; `{url}` = `public_web_url`):
  - welcome_artist: `Welcome to Prasang! Finish your profile so planners can find you: {url}/artist/onboarding`
  - welcome_planner: `Welcome to Prasang! Find artists for your next event: {url}/search`
  - trial_ending: `Your Prasang {plan} trial ends on {date}. Keep your plan: {url}/pricing`
  - renewal_reminder: `Your Prasang {plan} plan renews on {date}. Manage it: {url}/artist/subscription`
  - payment_failed: `We couldn't charge your Prasang {plan} plan. Update payment to keep it: {url}/artist/subscription`
  - plan_ended: `Your Prasang {plan} plan has ended and you're now on Free. Upgrade: {url}/pricing`
  - booking_check_* (planner): `Did you book {artist} for your {event}? Tell us: {url}/planner/inquiries`

- [ ] **Step 1: Failing tests** — `test_queue_is_at_most_once` (second call returns None), `test_deliver_sends_sms_and_email_and_marks_sent`, `test_deliver_skips_deleted_or_blocked_user`, `test_deliver_twice_sends_once`, `test_templates_exact_copy` (each kind, exact strings above), `test_post_me_queues_welcome_for_role`, `test_downgrade_queues_plan_ended`, `test_halted_webhook_queues_payment_failed`, `test_due_reminders_trial_48h_and_annual_7d_only` (monthly sub not reminded), `test_sweeper_restarts_pending_messages`, workflow test with time-skipping env: `DeliverMessageWorkflow` calls `deliver_message` once.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; add `queue_due_reminders` and `retry_pending_messages` to `run_sweeps`.
- [ ] **Step 4: Run** new tests + full backend suite — Expected: PASS; migrate exit 0.
- [ ] **Step 5: Verify** live: sign up a new phone via OTP (README flow), `docker compose logs worker | grep "Welcome to Prasang"` — Expected: one SMS line.
- [ ] **Step 6: Commit** `feat(notifications): queued at-most-once lifecycle messages`

### Task 6: Booking confirmation and check-ins (L3a)

**Files:**
- Create: `backend/app/workflows/booking_followup.py`, `backend/alembic/versions/0010_booking_confirmation.py`, `frontend/src/pages/planner/bookingAnswer.ts`, `frontend/src/pages/planner/bookingAnswer.test.ts`
- Modify: `backend/app/leads/models.py`, `backend/app/leads/service.py`, `backend/app/leads/router.py`, `backend/app/workflows/{starter,client,activities,worker}.py`, `backend/app/sweeps.py`, `backend/app/contract/leads.py`, `frontend/src/pages/planner/InquiriesPage.tsx`, CB
- Test: `backend/tests/api/test_booking_confirmation.py`, `backend/tests/workflows/test_booking_followup.py`

**Interfaces:**
- Consumes: `queue_message` + `deliver_message` (Task 5).
- Produces:
  - Lead columns: `booking_confirmed_at`, `booking_confirmed_by` ('artist'|'planner'), `planner_answer` ('booked'|'not_booked'|'deciding'), `planner_answered_at`, `followup_started_at`.
  - `PATCH /leads/{id}/planner-answer` (planner, own lead else 404 `lead_not_found`) body `{answer: 'booked'|'not_booked'|'deciding'}` → `PlannerInquiry`. `booked`: sets confirmation (by planner) if not set, status → `converted` when `new|contacted|expired`, keeps `declined`. Artist `update_status(... 'converted')` sets confirmation (by artist) if not set.
  - `PlannerInquiry` gains `bookingConfirmed: bool`, `plannerAnswer: … | null`, `canReview: bool`, `reviewId: string | null` (`canReview` = confirmed and (event_date is null or event_date < today IST) and no review yet; `reviewId` filled in Task 7, null until then).
  - Workflow `BookingFollowUpWorkflow.run(lead_id: str, inquiry_at_iso: str, event_date_iso: str | None)`; signal `settled()`; workflow id `booking-{lead_id}`; started in `create_lead` after commit (new leads only), `followup_started_at` set; sweeper starts missing ones for leads created after the migration (`followup_started_at is null and created_at > now-30d and created_at < now-2min`).
  - Activities `booking_state(lead_id) -> str` ('open'|'settled') and `send_booking_check(lead_id, kind) -> None` (queue + deliver to the planner user).
- Schedule (algorithm the tests pin): check-1 at inquiry+3 d; if still open, reminder at +2 d; check-2 at (event_date+1 d, or inquiry+14 d if no date), skipped if open==false; if still open, reminder +2 d. `deciding` = skip remaining check-1 messages, keep check-2. Before every send call `booking_state`; `settled` signal (sent by API on confirmation or planner `booked`/`not_booked`) ends the workflow. If check-2's time is earlier than check-1's reminder, skip that reminder.

- [ ] **Step 1: Failing API tests** — `test_planner_booked_confirms_and_converts`, `test_planner_booked_on_expired_lead_converts`, `test_planner_booked_on_declined_lead_keeps_status_but_confirms`, `test_planner_not_booked_keeps_artist_status`, `test_artist_converted_confirms_by_artist`, `test_other_planner_gets_404`, `test_can_review_only_after_event_date`, `test_locked_lead_can_be_confirmed`.
- [ ] **Step 2: Failing workflow tests** (time-skipping, activities mocked by name): `test_no_answer_sends_four_messages_in_order` (kinds and times), `test_confirmed_after_check1_sends_nothing_more` (Review Focus 3), `test_deciding_skips_to_check2`, `test_no_event_date_uses_day_14`, `test_event_soon_skips_overlapping_reminder`.
- [ ] **Step 3: Run** — Expected: FAIL.
- [ ] **Step 4: Implement**.
- [ ] **Step 5: Run** new + full suite — Expected: PASS; migrate exit 0.
- [ ] **Step 6: Frontend** inquiries page: per inquiry buttons Booked / Not booked / Still deciding (hidden once answered or confirmed; shows "Booking confirmed"), "Write a review" button when `canReview` (links to `/planner/inquiries/{id}/review`, page built in Task 7). Answering **Booked** on an inquiry whose `canReview` becomes true navigates straight to the review form. `bookingAnswer.ts` `inquiryActions(inquiry)` and `afterAnswer(inquiry) -> 'review' | 'stay'` unit-tested for each state.
- [ ] **Step 7: Run** frontend checks — Expected: pass.
- [ ] **Step 8: Commit** `feat(leads): booking confirmation with planner check-ins`

### Task 7: Verified reviews, replies, reports (L3b)

**Files:**
- Create: `backend/app/reviews/service.py`, `backend/alembic/versions/0011_verified_reviews.py`, `frontend/src/pages/planner/ReviewFormPage.tsx`, `frontend/src/pages/artist/ReviewsPage.tsx`, `frontend/src/pages/reviewForm.ts`, `frontend/src/pages/reviewForm.test.ts`
- Modify: `backend/app/reviews/models.py` (`lead_id` unique null, `planner_id` null, `artist_reply`, `artist_replied_at`; `ReviewReport` model), `backend/app/reviews/router.py`, `backend/app/leads/service.py` (`reviewId` in inquiries), `backend/app/contract/artists.py` (`Review` + `verified: bool`, `artistReply: str | null`), `frontend/src/pages/ArtistProfilePage.tsx` ("Booked via Prasang" badge, reply), `frontend/src/App.tsx`, artist sidebar, CB
- Test: `backend/tests/api/test_reviews.py`

**Interfaces:**
- Consumes: `recalc_rating` (Task 3), `canReview` rule (Task 6).
- Produces: `POST /reviews` (planner) `{leadId, rating 1–5, text 20–2000}` → 201 `Review` (403 `review_not_allowed` if not eligible, 409 `review_exists`); `PATCH /reviews/{id}` (author, within 7 days else 409 `review_locked`) `{rating?, text?}`; `PUT /reviews/{id}/reply` (artist of the review) `{text 1–1000}`; `POST /reviews/{id}/report` (artist of the review) `{reason 10–1000}` → 204, one open report per review; `GET /reviews/mine` (artist) → `Page<Review>`; public list excludes `hidden_at`. Event type/month copied from the lead (month = event_date or inquiry month). `reviewer_name` = planner's first name + last initial. Seed reviews: `verified=false` (no lead).

- [ ] **Step 1: Failing tests** — `test_planner_can_review_confirmed_past_event`, `test_cannot_review_before_event_date`, `test_cannot_review_unconfirmed`, `test_one_review_per_lead`, `test_other_planner_cannot_review_404`, `test_edit_within_7_days_then_locked`, `test_artist_reply_shows_publicly`, `test_other_artist_reply_404` (Review Focus 2), `test_report_listed_by_admin_reports`, `test_rating_aggregates_update_and_reach_search`, `test_hidden_review_not_listed`, `test_inquiry_shows_review_id_after_review`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; `admin reports` CLI command (Task 3 file) lists open `ReviewReport`s and the last 20 contact messages.
- [ ] **Step 4: Run** new + full suite — Expected: PASS; migrate exit 0.
- [ ] **Step 5: Frontend** review form (stars, text with counter, validation in `reviewForm.ts`: `validateReview({rating:0,text:'ok'})` → errors for both), artist Reviews page (list, reply box, report dialog), profile shows badge and artist reply.
- [ ] **Step 6: Run** frontend checks — Expected: pass.
- [ ] **Step 7: Commit** `feat(reviews): verified reviews with replies and reports`

### Task 8: Google reviews (L3c)

**Files:**
- Create: `backend/app/reviews/google.py`, `backend/alembic/versions/0012_google_place.py`
- Modify: `backend/app/config.py` (`google_places_api_key: str | None`), `backend/app/artists/models.py` (`google_place_url`, `google_place_id`), `backend/app/artists/service.py` (resolve on save), `backend/app/contract/artists.py` (`googlePlaceUrl` in input/patch/own profile), `backend/app/reviews/router.py`, `backend/app/admin/{actions,cli}.py` (`clear-google-place`), `.env.example`, `frontend/src/pages/artist/OnboardingPage.tsx` (optional field), `frontend/src/pages/ArtistProfilePage.tsx` ("From Google" block), CB
- Test: `backend/tests/unit/test_google_reviews.py`, `backend/tests/api/test_google_reviews_api.py`

**Interfaces:**
- Produces: `GooglePlaces` client with `resolve_place_id(url: str) -> str | None` (follow `maps.app.goo.gl` redirects; extract from `place_id`/`!1s` data or fall back to Places Text Search on the place name in the URL) and `reviews(place_id) -> GoogleReviews | None` (Places API (New) `GET https://places.googleapis.com/v1/places/{id}` with `X-Goog-FieldMask: rating,userRatingCount,reviews,googleMapsUri`); in-process TTL cache 24 h keyed by place id. `GET /artists/{slug}/google-reviews` → `GoogleReviewsResponse {rating, count, mapsUrl, items: [{author, rating, relativeTime, text}] (≤5)}` or 204 when unavailable (no key, no place, Google error).
- `googlePlaceUrl` validation: host in `google.com`, `www.google.com`, `maps.google.com`, `maps.app.goo.gl`, `goo.gl`, path containing `/maps` for google.com hosts; else 422 `fields.googlePlaceUrl`.

- [ ] **Step 1: Failing tests** (httpx mocked with `respx` or a fake transport): `test_resolve_from_full_maps_url`, `test_resolve_follows_short_link`, `test_reviews_cached_24h` (second call no HTTP), `test_endpoint_204_without_key`, `test_endpoint_returns_at_most_5`, `test_invalid_url_422`, `test_clear_google_place_cli`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; resolution failure keeps the URL, `google_place_id` null.
- [ ] **Step 4: Run** — Expected: PASS; migrate exit 0.
- [ ] **Step 5: Frontend** field "Google Maps link to your business (optional)"; profile block with Google rating, count, items, "Reviews from Google" attribution and "See all on Google" link; nothing rendered on 204.
- [ ] **Step 6: Run** frontend checks — Expected: pass.
- [ ] **Step 7: Commit** `feat(reviews): show Google reviews from the artist's listing`

### Task 9: Account deletion (L6)

**Files:**
- Create: `backend/app/accounts/__init__.py`, `backend/app/accounts/deletion.py`, `backend/app/accounts/router.py`, `frontend/src/pages/SettingsPage.tsx`, `frontend/src/pages/settings.test.ts`
- Modify: `backend/app/main.py`, `backend/app/workflows/{starter,client,activities,worker}.py` (`delete_media_files` activity + `DeleteMediaWorkflow` or reuse a generic retrying activity workflow), `backend/app/leads/service.py` + views (deleted artist label), `backend/app/admin/models.py` usage (`self_delete` row), `frontend/src/App.tsx` (`/settings`, both roles), navbar user menu link, `frontend/src/auth/AuthProvider.tsx` (re-auth helper), CB
- Test: `backend/tests/api/test_account_deletion.py`

**Interfaces:**
- Consumes: `users.deleted_at` (Task 3), `public_filter` (Task 3), gateway cancel, `queue_message` skip rule (Task 5), booking `settled` signal (Task 6).
- Produces: `DELETE /me` → 204. Requires a fresh session: SuperTokens session `time_created` within the last 10 minutes (`get_session_information(handle)`), else 403 `reauth_required` (dev tokens exempt). `delete_account(session, user, gateway) -> list[str]` returns S3 keys to delete.
- Effects (exact): artist → cancel live subs `at_cycle_end=False` (gateway errors logged, still proceed) and mark them `cancelled`; profile `is_published=false`, `stage_name='Former artist'`, contact/whatsapp/social/bio/image cleared, media rows deleted, `artist_changed`; reviews about them `hidden_at=now, hidden_reason='artist_deleted'`; planner → their leads `planner_name='Deleted user'`, `planner_phone=''`, `planner_email=null`, booking workflows signalled `settled`; their reviews keep text, `reviewer_name='Former user'`; both → user `full_name='Deleted user'`, `phone=null`, `email=null`, `avatar_url=null`, `deleted_at=now`, `id` kept; pending `outbound_messages` → `failed`; `AdminAction(actor='self', action='self_delete')`; then SuperTokens `delete_user(user_id)` after commit; S3 deletion started via workflow (retrying).
- Re-signup: SuperTokens issues a new user id for the same phone → `/me` 404 `profile_required` → fresh account (old rows untouched).
- Planner inquiry for a deleted artist shows artist name "Artist no longer on Prasang" and no contact details.

- [ ] **Step 1: Failing tests** — `test_delete_requires_fresh_session` (stale → 403 `reauth_required`), `test_artist_delete_cancels_billing_and_hides_profile` (404 public, ES doc gone, gateway spy), `test_artist_delete_hides_reviews_about_them`, `test_planner_delete_anonymises_leads_and_keeps_reviews`, `test_deleted_user_messages_not_sent`, `test_payment_records_kept_without_contact`, `test_same_phone_signs_up_as_new_user` (Review Focus 5: new identity → `/me` 404 `profile_required`; old leads still "Deleted user"), `test_inquiry_shows_artist_gone`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** new + full suite — Expected: PASS.
- [ ] **Step 5: Frontend** `/settings`: account details, "Delete my account" danger zone → explains what is deleted/kept → for phone users, sends an OTP and asks for it (existing passwordless functions), then calls `DELETE /me`; for Google users, redirects through Google with return path `/settings?confirmDelete=1` and then calls it; on success signs out and shows "Your account has been deleted". `settings.test.ts`: `deletionSteps(me)` returns `['otp','confirm']` for phone users and `['google','confirm']` for Google-only users.
- [ ] **Step 6: Run** frontend checks — Expected: pass.
- [ ] **Step 7: Verify** live: OTP sign in a new planner, `DELETE /api/v1/me` with that session (curl, header mode) → 204; same phone again → `/me` 404 `profile_required`.
- [ ] **Step 8: Commit** `feat(accounts): self-serve account deletion`

### Task 10: Smoke, runbook, backlog

**Files:**
- Modify: `mockoon/smoke.sh`, `README.md`, `docs/backlog.md`, `.env.example`

- [ ] **Step 1:** Extend `mockoon/smoke.sh` with: `GET /site-info`, `POST /contact`, `GET /subscriptions/me/payments` (artist), `PATCH /leads/{id}/planner-answer` (planner, first inquiry), `GET /artists/{slug}/google-reviews` (200 or 204 accepted), `GET /reviews/mine` (artist). Destructive calls (`DELETE /me`) are not in the smoke.
- [ ] **Step 2: Run** `bash mockoon/smoke.sh` against Mockoon (`npx @mockoon/cli start --data mockoon/prasang.json --port 3001`) and against `http://localhost:8000/api/v1` — Expected: `SMOKE PASS` on both, twice in a row on the real API.
- [ ] **Step 3:** README: admin CLI section (each command, one line), link previews check, settings env vars (`SUPPORT_EMAIL`, `SUPPORT_PHONE`, `BUSINESS_ADDRESS`, `PUBLIC_WEB_URL`, `WEB_INDEX_PATH`, `GOOGLE_PLACES_API_KEY`). Backlog: mark EL L1–L7 done with notes, keep decisions log.
- [ ] **Step 4: Run** full backend + frontend suites and `bash scripts/stack-health.sh` — Expected: all green, `STACK HEALTHY`.
- [ ] **Step 5: Commit** `docs: runbook and backlog for web launch readiness`
