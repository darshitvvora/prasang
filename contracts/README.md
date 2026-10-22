# Prasang API Contract (v1)

This folder is the contract between the React frontend and the FastAPI backend.

- **Types:** [`frontend/src/api/types.ts`](../frontend/src/api/types.ts) is the TypeScript source of truth.
- **Examples:** [`examples/`](examples/) holds one canonical JSON per request/response. The frontend type-checks them (`npx tsc -b`), and backend contract tests parse them into Pydantic models with `extra="forbid"`.
- **Mock server:** [`../mockoon/`](../mockoon/) serves this contract on `http://localhost:3001`.

## Conventions

| Topic | Rule |
|---|---|
| Base path | `/api/v1` |
| JSON keys | camelCase |
| Dates | `YYYY-MM-DD`; timestamps ISO-8601 UTC with `Z` (`2026-09-29T10:15:00Z`) |
| Money | integer rupees (`15000` = ₹15,000) |
| Lists | `{"items": [...], "total": n, "page": n, "size": n}` (1-based `page`, default `size` 20, max 50) plus endpoint extras |
| Errors | `{"error": {"code": "artist_not_found", "message": "Human readable", "details": {}}}` |
| Validation (422) | `details.fields` maps camelCase field → message |
| Auth | `Authorization: Bearer <Supabase access token>` |
| Nulls | Optional values are present with `null`, never omitted in responses |

## Enums

- `artistType`: `magician dj singer comedian bubble_artist band body_double anchor other`
- `eventType`: `birthday wedding pre_wedding anniversary corporate house_party other`
- `subscriptionTier`: `free basic pro premium`
- `budgetRange`: `5k_10k 10k_15k 15k_25k 25k_50k 50k_plus` (server derives `budgetMin`/`budgetMax`; `50k_plus` → max `null`)
- Lead `status`: `new contacted converted declined expired`
- Inquiry `status` (planner view): `pending responded confirmed declined` — mapped from lead status: new→pending, contacted→responded, converted→confirmed, declined/expired→declined
- Lead `source`: `search profile featured direct_link`

## Endpoints

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | /me | any | – | 200 Me · 401 `unauthenticated` · 404 `profile_required` |
| POST | /me | signed-in, no profile | CreateMeRequest | 201 Me · 409 `profile_exists` |
| PATCH | /me | user | UpdateMeRequest | 200 Me |
| DELETE | /me | any (fresh sign-in ≤10 min) | – | 204 — deletes the account now: artist profile hidden and anonymised, billing cancelled, media removed; planners' inquiries/reviews anonymised; payment records kept · 403 `reauth_required` with `details: {method: 'phone', phone} \| {method: 'google', email}` |
| GET | /auth/providers | public | – | AuthProvidersResponse — which sign-in methods are configured |
| * | /auth/* | – | SuperTokens SDK routes (phone OTP `signinup/code`, `signinup/code/consume`, Google `authorisationurl`, `signinup`, `session/refresh`, `signout`) | managed by `supertokens-web-js` / `supertokens-react-native` |
| GET | /locations | public | – | LocationsResponse |
| GET | /search/artists | public | SearchParams (query) | SearchResponse |
| GET | /search/suggestions?q= | public | – | `{items: Suggestion[]}` |
| GET | /artists/featured?size= | public | – | `{items: ArtistCard[]}` |
| GET | /artists/{slug} | public | – | ArtistDetail · 404 `artist_not_found` |
| GET | /artists/{slug}/reviews | public | page,size | Page<Review> |
| GET | /reviews/mine?page&size | artist | – | Page<Review> — reviews about the signed-in artist (hidden ones excluded) |
| POST | /reviews | planner | CreateReviewRequest | 201 Review · 404 `lead_not_found` · 403 `review_not_allowed` (booking not confirmed or event not over) · 409 `review_exists` |
| PATCH | /reviews/{id} | planner (author) | UpdateReviewRequest | Review · 409 `review_locked` after 7 days |
| PUT | /reviews/{id}/reply | artist (reviewed) | `{text}` | Review — one public reply, editable |
| POST | /reviews/{id}/report | artist (reviewed) | `{reason}` | 204 — one open report per review; Prasang decides |
| GET | /artists/{slug}/google-reviews | public | – | GoogleReviewsResponse (≤5 reviews, show with Google attribution) · 204 when the artist has no Google listing or the server has no Places key |
| GET | /artists/{slug}/similar?size= | public | – | `{items: ArtistCard[]}` |
| POST | /artists/{slug}/contact-click | public | – | 204 |
| POST | /artists | artist | ArtistProfileInput | 201 ArtistProfile · 409 `artist_exists` · 422 |
| GET | /artists/me | artist | – | ArtistProfile · 404 `artist_profile_not_found` |
| PATCH | /artists/me | artist | Partial<ArtistProfileInput> & {isPublished?} | ArtistProfile |
| GET | /artists/me/dashboard | artist | – | ArtistDashboard |
| GET | /artists/me/media | artist | – | MediaListResponse |
| POST | /artists/me/media/upload-url | artist | UploadUrlRequest (`hd: true` = Premium HD slot) | UploadUrlResponse · 409 `media_quota_exceeded` (incl. no HD slots / Free plan) · 422 `fields.sizeBytes` — photos ≤10 MB, videos ≤40 MB, HD ≤200 MB (no compression) |
| POST | /artists/me/media | artist | CreateMediaRequest | 201 Media · 422 `fields.url` for unsupported links · 503 `storage_not_configured` for uploads without S3 |
| POST | /artists/me/avatar | artist | `{storageKey}` | `{profileImageUrl}` |
| DELETE | /artists/me/media/{id} | artist | – | 204 |
| PUT | /artists/me/media/order | artist | `{ids: string[]}` | `{items: Media[]}` |
| POST | /leads | planner | CreateLeadRequest | 201 CreateLeadResponse (200 if duplicate) · 429 `lead_rate_limited` |
| GET | /leads/artist?status&page&size | artist | – | ArtistLeadsResponse |
| PATCH | /leads/{id} | artist | UpdateLeadRequest | ArtistLead · 409 `invalid_transition` |
| GET | /leads/planner?status&page&size | planner | – | PlannerInquiriesResponse |
| PATCH | /leads/{id}/planner-answer | planner (own inquiry) | `{answer: 'booked'\|'not_booked'\|'deciding'}` | PlannerInquiry · 404 `lead_not_found` — `booked` confirms the booking (and converts new/contacted/expired leads); either side's confirmation opens the review |
| GET | /subscriptions/plans | public | – | `{items: Plan[]}` |
| GET | /subscriptions/me | artist | – | MySubscriptionResponse |
| POST | /subscriptions/trial | artist | StartTrialRequest | PlanUsage · 409 `trial_used` |
| POST | /subscriptions | artist | CreateSubscriptionRequest | 201 CreateSubscriptionResponse — a PhonePe payment link (also emailed + texted), valid 24 h; also used to upgrade/switch (see rules) · 502 `payments_unavailable` |
| POST | /subscriptions/verify | artist | VerifyPaymentRequest `{subscriptionId}` | VerifyPaymentResponse — "I've paid": asks PhonePe for the link's status; `pending_activation` until PhonePe confirms · 404 `subscription_not_found` |
| POST | /subscriptions/cancel | artist | – | MySubscriptionResponse |
| GET | /site-info | public | – | SiteInfo — support email/phone and business address (nulls when not configured) |
| POST | /contact | public | ContactRequest | 201 `{id}` · 429 `contact_rate_limited` (5 per IP per hour) |
| GET | /subscriptions/downgrade-preview?tier= | artist | – | DowngradePreview — how many photos/videos/HD videos/embeds a move to `tier` would remove (hidden at once, deleted after 7 days) |
| GET | /subscriptions/me/payments | artist | – | BillingHistoryResponse — newest first, one row per PhonePe payment attempt; `receiptUrl` is null (the payment-received email is the receipt) |
| POST | /subscriptions/webhook | PhonePe `Authorization: SHA256(username:password)` | PhonePe `paylink.order.completed` / `paylink.order.failed` | 200 |

## Error codes

| Code | HTTP | Meaning |
|---|---|---|
| `unauthenticated` | 401 | Missing/invalid/expired token |
| `forbidden` | 403 | Wrong role or not the owner |
| `profile_required` | 404 | Signed in but `POST /me` not done yet |
| `profile_exists` | 409 | `POST /me` called twice |
| `validation_error` | 422 | Body/query invalid; see `details.fields` |
| `artist_not_found` | 404 | Unknown or unpublished slug |
| `artist_profile_not_found` | 404 | Artist user has not created a profile |
| `artist_exists` | 409 | `POST /artists` called twice |
| `media_quota_exceeded` | 409 | Tier limit reached; `details: {limit, used}` |
| `lead_rate_limited` | 429 | >10 leads per planner per day |
| `invalid_transition` | 409 | Lead status change not allowed |
| `trial_used` | 409 | Artist already used the 7-day trial |
| `invalid_signature` | 400 | PhonePe webhook authorization mismatch |
| `payments_unavailable` | 502 | PhonePe couldn't create the payment link; retry shortly |
| `search_unavailable` | 503 | Elasticsearch is unreachable; retry shortly |
| `storage_not_configured` | 503 | Photo/video uploads are not set up on this server (social links still work) |
| `artist_suspended` | 409 | The artist is suspended and not taking enquiries |
| `account_blocked` | 403 | The signed-in account has been blocked by Prasang |
| `review_not_allowed` | 403 | Reviews need a confirmed booking whose event date has passed |
| `review_exists` | 409 | This booking already has a review |
| `review_locked` | 409 | Reviews can be edited for 7 days only |
| `reauth_required` | 403 | Deleting the account needs a sign-in from the last 10 minutes; `details.method` says how |
| `contact_rate_limited` | 429 | More than 5 contact messages from one IP in an hour |
| `internal_error` | 500 | Unexpected server error |

## Business rules the contract encodes

- **Plans (2026-10-20, three plans):** **Basic** (tier key `free`, ₹0) — no uploads, 3 leads/month, Instagram/YouTube/Facebook embeds + widgets. **Pro** (₹599) — 5 photos + 1 video, 15 leads/month, embeds, search boost, no badge, not featured. **Premium** (₹1,199) — 50 photos + 8 videos + 2 HD videos, unlimited leads, embeds, verified badge (after admin verification), featured, top placement. Video caps: 40 MB (HD 200 MB). `isVerified`/`isFeatured` already reflect the plan. Show plan **names** from `GET /subscriptions/plans`, never the tier key.
- **Downgrades:** items beyond the new plan's limits (by the artist's display order; embeds on Free) are hidden at once and deleted after 7 days (`Media.deleteAfter`); upgrading earlier restores them. Quotas count visible items only.

- Monthly lead caps (calendar month, IST): free 3, basic 15, pro/premium unlimited (`-1`). Leads over the cap are stored with `isLocked: true`; the artist sees `plannerPhone`/`plannerEmail` as `null` until upgrade. Planners always receive the artist's contact info.
- `POST /leads` requires a signed-in planner. A second lead by the same planner for the same artist and event date returns `200` with the existing `leadId`.
- 7-day trial: once per artist, no card, any paid tier.
- **Payments are PhonePe payment links, not auto-debit.** Each paid period is one subscription with one link. `POST /subscriptions` never conflicts: if the artist already has an **active** plan this is a plan change — the new plan starts from the day it is paid and replaces the old one. Any unpaid link is cancelled and replaced, so retrying always works.
- **Renewals:** 5 days before a period ends the server creates a renewal link (emailed + texted; shown as `pendingPayment` with `renewal: true` on `/subscriptions/me`). Paying it early loses nothing — the new period starts when the current one ends. Unpaid, the plan moves to Free 3 days after the period ends. `POST /subscriptions/cancel` stops renewal links (and closes one already sent).
- Before `POST /artists`, artist-scoped reads (`/artists/me`, `/artists/me/dashboard`, `/artists/me/media`, `/leads/artist`) return 404 `artist_profile_not_found`; `/subscriptions/me` returns the Free plan with `trialAvailable: true`.
- Phone numbers are 10-digit Indian mobile numbers without country code (`9820011001`); the UI adds `+91`.
- `Review.eventMonth` is `YYYY-MM`.
- **Social embeds:** `POST /artists/me/media` with `kind` `youtube` | `instagram` | `facebook` and the public post URL. The server validates the link and returns `embedUrl` (the iframe `src`). Accepted: YouTube `watch?v=`, `youtu.be/`, `shorts/`; Instagram `/p/`, `/reel/`, `/tv/`; Facebook posts, photos, `/videos/` and `fb.watch`. Anything else → 422 `fields.url`. `facebookUrl` on a profile must be a `facebook.com` link.
- **Sessions:** web uses SuperTokens httpOnly cookies; mobile apps use header tokens (`st-auth-mode: header`). Both hit the same endpoints.

## Mock tokens (Mockoon only)

| Token | Behaves as |
|---|---|
| `mock-artist` | Artist *Arjun Malhotra* with a published profile (slug `arjun-malhotra-magic`) |
| `mock-planner` | Planner *Neha Kulkarni* with 5 inquiries |
| `mock-new` | Signed in, no profile yet (`GET /me` → 404 `profile_required`) |
