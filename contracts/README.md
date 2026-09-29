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
| GET | /locations | public | – | LocationsResponse |
| GET | /search/artists | public | SearchParams (query) | SearchResponse |
| GET | /search/suggestions?q= | public | – | `{items: Suggestion[]}` |
| GET | /artists/featured?size= | public | – | `{items: ArtistCard[]}` |
| GET | /artists/{slug} | public | – | ArtistDetail · 404 `artist_not_found` |
| GET | /artists/{slug}/reviews | public | page,size | Page<Review> |
| GET | /artists/{slug}/similar?size= | public | – | `{items: ArtistCard[]}` |
| POST | /artists/{slug}/contact-click | public | – | 204 |
| POST | /artists | artist | ArtistProfileInput | 201 ArtistProfile · 409 `artist_exists` · 422 |
| GET | /artists/me | artist | – | ArtistProfile · 404 `artist_profile_not_found` |
| PATCH | /artists/me | artist | Partial<ArtistProfileInput> & {isPublished?} | ArtistProfile |
| GET | /artists/me/dashboard | artist | – | ArtistDashboard |
| GET | /artists/me/media | artist | – | MediaListResponse |
| POST | /artists/me/media/upload-url | artist | UploadUrlRequest | UploadUrlResponse · 409 `media_quota_exceeded` |
| POST | /artists/me/media | artist | CreateMediaRequest | 201 Media |
| POST | /artists/me/avatar | artist | `{storageKey}` | `{profileImageUrl}` |
| DELETE | /artists/me/media/{id} | artist | – | 204 |
| PUT | /artists/me/media/order | artist | `{ids: string[]}` | `{items: Media[]}` |
| POST | /leads | planner | CreateLeadRequest | 201 CreateLeadResponse (200 if duplicate) · 429 `lead_rate_limited` |
| GET | /leads/artist?status&page&size | artist | – | ArtistLeadsResponse |
| PATCH | /leads/{id} | artist | UpdateLeadRequest | ArtistLead · 409 `invalid_transition` |
| GET | /leads/planner?status&page&size | planner | – | PlannerInquiriesResponse |
| GET | /subscriptions/plans | public | – | `{items: Plan[]}` |
| GET | /subscriptions/me | artist | – | MySubscriptionResponse |
| POST | /subscriptions/trial | artist | StartTrialRequest | PlanUsage · 409 `trial_used` |
| POST | /subscriptions | artist | CreateSubscriptionRequest | 201 CreateSubscriptionResponse · 409 `subscription_exists` |
| POST | /subscriptions/verify | artist | VerifyPaymentRequest | VerifyPaymentResponse · 400 `invalid_signature` |
| POST | /subscriptions/cancel | artist | – | MySubscriptionResponse |
| POST | /subscriptions/webhook | Razorpay HMAC | Razorpay event | 200 |

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
| `subscription_exists` | 409 | Active/pending subscription exists |
| `invalid_signature` | 400 | Razorpay signature mismatch |
| `internal_error` | 500 | Unexpected server error |

## Business rules the contract encodes

- Monthly lead caps (calendar month, IST): free 3, basic 15, pro/premium unlimited (`-1`). Leads over the cap are stored with `isLocked: true`; the artist sees `plannerPhone`/`plannerEmail` as `null` until upgrade. Planners always receive the artist's contact info.
- `POST /leads` requires a signed-in planner. A second lead by the same planner for the same artist and event date returns `200` with the existing `leadId`.
- 7-day trial: once per artist, no card, any paid tier.

## Mock tokens (Mockoon only)

| Token | Behaves as |
|---|---|
| `mock-artist` | Artist *Arjun Malhotra* with a published profile (slug `arjun-malhotra-magic`) |
| `mock-planner` | Planner *Neha Kulkarni* with 5 inquiries |
| `mock-new` | Signed in, no profile yet (`GET /me` → 404 `profile_required`) |
