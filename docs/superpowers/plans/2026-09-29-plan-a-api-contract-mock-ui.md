# Plan A — API Contract, Mockoon Mock Server, Frontend Wired to Mock

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define every JSON payload the backend will serve, serve them from Mockoon, and make every frontend page read/write through a typed API client instead of hard-coded mock arrays — so Plan B (DB + FastAPI) only has to satisfy an already-exercised contract.

**Architecture:** `contracts/` holds the contract (README conventions + one canonical request/response JSON per endpoint). `mockoon/` holds datasets and a Node build script that assembles a Mockoon environment (`mockoon/prasang.json`) served by the natively installed `mockoon-cli`. The frontend gets `src/api/` (types, fetch client, endpoint functions), `src/auth/` (AuthProvider with `mock` mode now, `supabase` mode in Plan B), TanStack Query for data fetching, and a Vite dev proxy `/api → http://localhost:3001`.

**Tech Stack:** Mockoon CLI 9.8 (native), Node 25, React 19, React Router 7, TypeScript 6, Vite 8, @tanstack/react-query 5, vitest.

**Spec:** [docs/superpowers/specs/2026-09-29-backend-mvp-design.md](../specs/2026-09-29-backend-mvp-design.md)

## Global Constraints

- Base path `/api/v1`; JSON keys **camelCase**; dates `YYYY-MM-DD`, timestamps ISO-8601 UTC with `Z`; money = integer rupees.
- Error body always `{"error": {"code": string, "message": string, "details"?: object}}`.
- Lists always `{"items": [...], "total": n, "page": n, "size": n}` (plus endpoint-specific extras).
- Auth: `Authorization: Bearer <token>`. Mock tokens: `mock-artist`, `mock-planner`, `mock-new` (signed in, no profile yet).
- Enums exactly as `frontend/src/types/artist.ts` (`ArtistType`, `EventType`, `SubscriptionTier`).
- Lead caps: free 3 / basic 15 / pro & premium unlimited (`-1`). Budget ranges `5k_10k|10k_15k|15k_25k|25k_50k|50k_plus`.
- No Playwright/browser automation for verification: use `npm run build` (tsc), `npm test` (vitest), `curl` against Mockoon.
- Commit messages plain — no co-author/AI attribution lines.
- Mock server port `3001`; Vite dev server `5173`.

## Review Focus

1. Signed-out user opens `/artist/*` or `/planner/*` → redirected to `/login?next=…`, not a blank page. (Task 5 guard test via tsc + manual curl-free check in `RequireRole` unit test.)
2. API returns an error (4xx/5xx or network down) → pages show an inline error state, never crash; `ApiError` carries `code`. (Task 4 client tests.)
3. Unknown profile slug → "Artist not found" page, not the first mock artist (current behaviour). (Task 7 mock 404 route + curl.)
4. Artist over lead quota → leads show masked planner details with an upgrade prompt, planner still gets contact info. (Task 3 datasets include a locked lead; Task 9 renders it.)
5. Signed-in user with no profile (`mock-new`) → role picker / onboarding, never a dashboard that 404s. (Task 5/6 flow.)

---

## File Structure

```
contracts/
  README.md                         # conventions, endpoint index, mock tokens, error codes
  examples/<area>/<endpoint>.<request|response>.json
mockoon/
  data/artists.json                 # 12 full artist records (card + detail + private fields)
  data/reviews.json, leads.json, inquiries.json, plans.json, locations.json, media.json
  routes.mjs                        # route table (method, path, responses, rules)
  build.mjs                         # assembles prasang.json from routes + data + examples
  prasang.json                      # generated Mockoon environment (committed, openable in Mockoon app)
  README.md                         # how to run
frontend/
  vite.config.ts                    # + /api proxy, vitest config
  .env.example                      # VITE_API_BASE_URL, VITE_AUTH_MODE, VITE_API_PROXY_TARGET
  src/api/types.ts                  # contract types (single TS source of truth)
  src/api/client.ts                 # fetch wrapper, ApiError, token injection
  src/api/endpoints.ts              # one typed function per endpoint
  src/api/queries.ts                # TanStack Query hooks
  src/api/format.ts                 # formatPrice, budget labels, relative time
  src/auth/AuthProvider.tsx         # context: user, token, signIn(role), signOut, completeProfile
  src/auth/RequireRole.tsx          # route guard
  src/components/QueryState.tsx     # loading / error / empty renderer
  src/pages/NotFoundPage.tsx
  src/pages/* (modified)            # wired to API
  src/data/mockArtists.ts, mockPlannerActivity.ts   # DELETED at the end (data moves to mockoon/data)
```

---

### Task 1: Contract conventions + TypeScript contract types

**Files:**
- Create: `contracts/README.md`
- Create: `frontend/src/api/types.ts`
- Modify: `frontend/src/types/artist.ts` (add `BudgetRange`, `LeadStatus`, `InquiryStatus`, labels; keep existing exports)

**Interfaces — Produces** (every later task uses these names verbatim):

```ts
// frontend/src/api/types.ts
import type { ArtistType, EventType, SubscriptionTier, BudgetRange, LeadStatus, InquiryStatus } from '../types/artist';

export interface ApiErrorBody { error: { code: string; message: string; details?: Record<string, unknown> } }
export interface Page<T> { items: T[]; total: number; page: number; size: number }

export type Role = 'artist' | 'planner' | 'admin';
export interface Me { id: string; email: string | null; fullName: string; phone: string | null; role: Role; avatarUrl: string | null; artistSlug: string | null; createdAt: string }
export interface CreateMeRequest { role: 'artist' | 'planner'; fullName: string; phone?: string }
export interface UpdateMeRequest { fullName?: string; phone?: string }

export interface City { name: string; areas: string[] }
export interface LocationsResponse { cities: City[] }

export interface ArtistCard {
  artistId: string; slug: string; name: string; artistType: ArtistType; profileImageUrl: string | null; bio: string;
  locationCity: string; locationArea: string; perEventRateMin: number; perEventRateMax: number;
  averageRating: number; totalReviews: number; isVerified: boolean; isFeatured: boolean; subscriptionTier: SubscriptionTier;
  instagramHandle: string | null; youtubeChannel: string | null; experienceYears: number;
  eventTypesSupported: EventType[]; languagesSpoken: string[]; readyToTravel: boolean;
}
export type MediaKind = 'image' | 'video' | 'youtube' | 'instagram';
export interface Media { id: string; kind: MediaKind; url: string; thumbnailUrl: string | null; caption: string | null; displayOrder: number }
export interface ArtistDetail extends ArtistCard { media: Media[] }
export interface Review { id: string; reviewerName: string; rating: number; eventType: EventType; eventMonth: string; text: string; createdAt: string }

export interface ArtistProfileInput {
  name: string; artistType: ArtistType; locationCity: string; locationArea: string; bio: string; experienceYears: number;
  perEventRateMin: number; perEventRateMax: number; eventTypesSupported: EventType[]; languagesSpoken: string[];
  readyToTravel: boolean; instagramHandle: string | null; youtubeChannel: string | null;
  contactPhone: string; whatsappNumber: string | null;
}
export interface CompletenessItem { key: 'basic_info' | 'photo' | 'bio' | 'media' | 'instagram' | 'review'; label: string; done: boolean }
export interface ProfileCompleteness { percent: number; items: CompletenessItem[] }
export interface ArtistProfile extends ArtistDetail { contactPhone: string; whatsappNumber: string | null; isPublished: boolean; completeness: ProfileCompleteness }

export interface PlanUsage {
  tier: SubscriptionTier; name: string; status: 'free' | 'trial' | 'active' | 'cancelling' | 'halted';
  leadLimitMonthly: number; leadsUsedThisMonth: number; leadsRemaining: number | null;
  periodEnd: string | null; trialEndsAt: string | null; trialAvailable: boolean;
}
export interface Metric { value: number; changePct: number | null }
export interface LeadSourceStat { source: LeadSource; label: string; pct: number }
export interface ArtistDashboard {
  greetingName: string; plan: PlanUsage;
  metrics: { profileViews: Metric; contactClicks: Metric; leadsThisMonth: Metric; averageRating: { value: number; totalReviews: number } };
  recentLeads: ArtistLead[]; leadSources: LeadSourceStat[]; completeness: ProfileCompleteness;
}

export interface MediaQuota { images: { used: number; limit: number }; videos: { used: number; limit: number } }
export interface MediaListResponse { items: Media[]; quota: MediaQuota }
export interface UploadUrlRequest { kind: 'image' | 'video' | 'avatar'; contentType: string; sizeBytes: number }
export interface UploadUrlResponse { uploadUrl: string; storageKey: string; expiresAt: string; headers: Record<string, string> }
export type CreateMediaRequest = { kind: 'image' | 'video'; storageKey: string; caption?: string } | { kind: 'youtube' | 'instagram'; url: string; caption?: string };

export type SortOption = 'relevance' | 'rating' | 'price_low' | 'price_high' | 'popular' | 'newest';
export interface SearchParams {
  q?: string; city?: string; area?: string; artistType?: ArtistType; eventType?: EventType; language?: string;
  readyToTravel?: boolean; minPrice?: number; maxPrice?: number; minRating?: number;
  verifiedOnly?: boolean; featuredOnly?: boolean; sort?: SortOption; page?: number; size?: number;
}
export interface FacetBucket { value: string; count: number }
export interface SearchResponse extends Page<ArtistCard> { facets: { artistType: FacetBucket[]; city: FacetBucket[] } }
export interface Suggestion { type: 'artist' | 'artistType' | 'area'; label: string; value: string; slug: string | null }

export type LeadSource = 'search' | 'profile' | 'featured' | 'direct_link';
export interface CreateLeadRequest {
  artistId: string; plannerName: string; plannerPhone: string; plannerEmail: string | null; eventType: EventType;
  eventDate: string | null; eventCity: string | null; budgetRange: BudgetRange; notes: string | null; source: LeadSource;
}
export interface CreateLeadResponse { leadId: string; artist: { name: string; contactPhone: string; whatsappNumber: string | null; instagramHandle: string | null } }
export interface ArtistLead {
  id: string; plannerName: string; plannerPhone: string | null; plannerEmail: string | null; eventType: EventType; eventTitle: string;
  eventDate: string | null; eventCity: string | null; budgetMin: number; budgetMax: number | null; notes: string | null;
  status: LeadStatus; isLocked: boolean; createdAt: string;
}
export interface ArtistLeadsResponse extends Page<ArtistLead> { counts: Record<'all' | LeadStatus, number>; plan: PlanUsage }
export interface UpdateLeadRequest { status: 'contacted' | 'converted' | 'declined' }
export interface PlannerInquiry {
  id: string; artist: { artistId: string; slug: string; name: string; artistType: ArtistType; profileImageUrl: string | null };
  eventType: EventType; eventTitle: string; eventDate: string | null; daysToEvent: number | null;
  budgetMin: number; budgetMax: number | null; notes: string | null; status: InquiryStatus; contactedAt: string;
}
export interface PlannerInquiriesResponse extends Page<PlannerInquiry> {
  counts: Record<'all' | InquiryStatus, number>;
  summary: { artistsContacted: number; responsesReceived: number; confirmedBookings: number;
    upcoming: { inquiryId: string; eventTitle: string; artistName: string; eventDate: string; daysToEvent: number } | null };
}

export type BillingCycle = 'monthly' | 'annual';
export interface PlanFeature { label: string; value: boolean | string }
export interface Plan {
  tier: SubscriptionTier; name: string; tagline: string; monthlyPrice: number; annualPrice: number; annualMonthlyEquivalent: number;
  leadLimitMonthly: number; maxImages: number; maxVideos: number; popular: boolean; features: PlanFeature[];
}
export interface SubscriptionSummary { id: string; tier: SubscriptionTier; billingCycle: BillingCycle; status: 'created' | 'active' | 'halted' | 'cancelled' | 'completed' | 'expired'; currentPeriodEnd: string | null; cancelAtPeriodEnd: boolean }
export interface MySubscriptionResponse { plan: PlanUsage; subscription: SubscriptionSummary | null }
export interface CreateSubscriptionRequest { tier: Exclude<SubscriptionTier, 'free'>; billingCycle: BillingCycle }
export interface CreateSubscriptionResponse { subscriptionId: string; checkout: { keyId: string; razorpaySubscriptionId: string; name: string; description: string; prefill: { name: string; email: string | null; contact: string | null } } }
export interface VerifyPaymentRequest { razorpayPaymentId: string; razorpaySubscriptionId: string; razorpaySignature: string }
export interface VerifyPaymentResponse { status: 'active' | 'pending_activation'; plan: PlanUsage }
export interface StartTrialRequest { tier: Exclude<SubscriptionTier, 'free'> }
```

Additions to `frontend/src/types/artist.ts`:

```ts
export type BudgetRange = '5k_10k' | '10k_15k' | '15k_25k' | '25k_50k' | '50k_plus';
export const BUDGET_RANGE_LABELS: Record<BudgetRange, string> = {
  '5k_10k': '₹5K–10K', '10k_15k': '₹10K–15K', '15k_25k': '₹15K–25K', '25k_50k': '₹25K–50K', '50k_plus': '₹50K+',
};
export type LeadStatus = 'new' | 'contacted' | 'converted' | 'declined' | 'expired';
export type InquiryStatus = 'pending' | 'responded' | 'confirmed' | 'declined';
```

`contracts/README.md` content: conventions from Global Constraints; the endpoint table below; error codes table; mock tokens.

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

Lead ↔ inquiry status mapping: new→pending, contacted→responded, converted→confirmed, declined/expired→declined.

- [ ] **Step 1:** Write `frontend/src/api/types.ts` and the `artist.ts` additions exactly as above.
- [ ] **Step 2:** Write `contracts/README.md` (conventions, table above, error codes: `unauthenticated, forbidden, profile_required, profile_exists, validation_error, artist_not_found, artist_profile_not_found, artist_exists, media_quota_exceeded, lead_rate_limited, invalid_transition, trial_used, subscription_exists, invalid_signature, internal_error`).
- [ ] **Step 3:** Run `cd frontend && npx tsc -b` → expect PASS (types are unused but must compile).
- [ ] **Step 4:** Commit `feat(contract): API conventions and TypeScript contract types`.

### Task 2: Canonical example payloads

**Files:** Create `contracts/examples/**` — one file per request/response in the table (e.g. `me/get.response.json`, `me/post.request.json`, `leads/post.request.json`, `leads/post.response.json`, `errors/validation_error.json`, …).

**Interfaces:** Consumes Task 1 types. Produces JSON files that Plan B contract tests parse into Pydantic response models (`extra='forbid'`), and that Task 3 reuses as Mockoon bodies.

- [ ] **Step 1:** Write a type-check harness `frontend/src/api/__contract__/examples.check.ts` that imports each example with `import x from '../../../../contracts/examples/…json'` and assigns it through a helper `check<T>()(x)` that compares keys structurally (`satisfies` fails on widened string enums, so the helper is `function check<T>() { return <U extends DeepKeys<T>>(u: U) => u; }` where `DeepKeys<T>` maps every property to `unknown` recursively — catches missing/extra/misspelled keys). Add `"resolveJsonModule": true` to `tsconfig.app.json`.
- [ ] **Step 2:** Run `npx tsc -b` → FAIL (files missing).
- [ ] **Step 3:** Author all example JSON files using realistic Indian data (Mumbai areas, ₹ amounts from the Pricing page).
- [ ] **Step 4:** `npx tsc -b` → PASS. Commit `feat(contract): canonical request/response examples`.

### Task 3: Mockoon datasets, routes, build script

**Files:** Create `mockoon/data/*.json`, `mockoon/routes.mjs`, `mockoon/build.mjs`, `mockoon/README.md`, generated `mockoon/prasang.json`. Modify `frontend/package.json` (script `"mock": "node ../mockoon/build.mjs && mockoon-cli start --data ../mockoon/prasang.json --repair"`).

**Interfaces:** `routes.mjs` exports `routes: Array<{ method: 'get'|'post'|'patch'|'put'|'delete', path: string, responses: Array<{ status: number, body?: string, file?: string, rules?: Array<{target:'header'|'query'|'body'|'params', modifier:string, value:string, operator?:'equals'|'regex'|'null'}>, rulesOperator?: 'AND'|'OR', default?: boolean }> }>`. `build.mjs` inlines each `data/*.json` as a data bucket with id = filename, inlines `file` bodies, and writes a Mockoon env (`port 3001`, `endpointPrefix 'api/v1'`, `cors true`, latency 300 ms).

Verified templating facts (spike, Mockoon 9.8): `{{#if (queryParam 'x')}}` is always truthy — use `{{#unless (eq (queryParam 'x' '') '')}}`; `setVar` + `filter` + `find` + `len` + `stringify` + `dataRaw` work; never place `}}}}` — add a space.

Mock behaviour:
- `/me`: rules on `Authorization` header — `Bearer mock-artist` → artist Me (artistSlug `arjun-malhotra-magic`), `Bearer mock-planner` → planner Me, `Bearer mock-new` → 404 profile_required, else 401.
- `POST /me` → 201 Me built from body (`role`, `fullName`).
- `/search/artists` → filter bucket `artists` by `artistType`, `city`, `area`, `featuredOnly`, `verifiedOnly` (exact match); other params accepted and ignored (documented).
- `/artists/{slug}` → `find` by slug; 404 when not found (rule on template result via second response with rule `params slug` regex not matching known slugs — implemented by a template that outputs 404 body and `{{status 404}}` when `find` is empty).
- `/artists/{slug}/reviews`, `/similar` (same `artistType`, excluding self, first 3), `/featured` (`isFeatured`).
- `/artists/me*` → artist dataset record `art-001` + profile extras; `mock-new` token → 404 artist_profile_not_found on `GET /artists/me`.
- Media: `upload-url` returns `uploadUrl: http://localhost:3001/api/v1/_mock/upload/{{faker 'string.uuid'}}`; `PUT /_mock/upload/:key` → 200.
- Leads: `POST /leads` → 201 with artist contact from bucket; `GET /leads/artist` filters `leads` bucket by `status`; `GET /leads/planner` filters `inquiries` bucket by `status`; counts precomputed in the dataset file.
- Subscriptions: plans bucket; `POST /subscriptions` → checkout with `keyId: "rzp_test_mock"`; `verify` → active.

- [ ] **Step 1:** Write datasets (move the 12 artists from `frontend/src/data/mockArtists.ts` into `mockoon/data/artists.json` with added `media`, `contactPhone`, `whatsappNumber`; leads from `LeadsPage`, inquiries from `mockPlannerActivity.ts`, reviews from `ArtistProfilePage`, plans from `PricingPage`, locations from `indian_cities.json` + SearchPage `AREAS`).
- [ ] **Step 2:** Write `routes.mjs`, `build.mjs`.
- [ ] **Step 3:** Write `mockoon/smoke.sh` — curls every route and asserts status codes with `test`; run `npm run mock &` then `bash ../mockoon/smoke.sh` → expect all `OK`.
- [ ] **Step 4:** Commit `feat(mock): Mockoon environment generated from contract datasets`.

### Task 4: API client, endpoints, query hooks

**Files:** Create `frontend/src/api/client.ts`, `endpoints.ts`, `queries.ts`, `format.ts`, `frontend/src/api/client.test.ts`, `format.test.ts`. Modify `package.json` (deps `@tanstack/react-query`; dev `vitest`; script `"test": "vitest run"`), `vite.config.ts` (proxy + test), `.env.example`, `src/main.tsx` (QueryClientProvider).

**Interfaces — Produces:**

```ts
// client.ts
export class ApiError extends Error { constructor(public status: number, public code: string, message: string, public details?: Record<string, unknown>) }
export function setTokenProvider(fn: () => string | null): void;
export async function api<T>(path: string, init?: { method?: string; body?: unknown; query?: Record<string, string | number | boolean | undefined> }): Promise<T>;
// format.ts
export function formatPrice(n: number): string;          // 15000 → "₹15K", 800 → "₹800"
export function formatBudget(min: number, max: number | null): string; // → "₹15K – ₹25K" | "₹50K+"
export function relativeTime(iso: string, now?: Date): string;          // "5 hours ago", "3 days ago"
export function formatDate(d: string): string;            // "2026-01-05" → "Jan 5, 2026"
```

`endpoints.ts` exports one function per contract row, named: `getMe, createMe, updateMe, getLocations, searchArtists, getSuggestions, getFeaturedArtists, getArtist, getArtistReviews, getSimilarArtists, trackContactClick, createArtist, getMyArtist, updateMyArtist, getArtistDashboard, getMyMedia, requestUploadUrl, uploadToUrl, createMedia, setAvatar, deleteMedia, reorderMedia, createLead, getArtistLeads, updateLead, getPlannerInquiries, getPlans, getMySubscription, startTrial, createSubscription, verifyPayment, cancelSubscription`.

`queries.ts` exports hooks `useMe, useLocations, useSearchArtists(params), useFeaturedArtists, useArtist(slug), useArtistReviews(slug), useSimilarArtists(slug), useMyArtist, useArtistDashboard, useMyMedia, useArtistLeads(status), usePlannerInquiries(status), usePlans, useMySubscription` and mutations `useCreateLead, useUpdateLead, useCreateArtist, useUpdateMyArtist, useStartTrial, useCreateSubscription` with query-key invalidation.

- [ ] **Step 1: Failing tests** `client.test.ts`: (a) 200 JSON parsed; (b) 204 returns `undefined`; (c) 404 with error body → `ApiError{status:404, code:'artist_not_found'}`; (d) non-JSON 502 → `ApiError{code:'http_502'}`; (e) network failure → `ApiError{status:0, code:'network_error'}`; (f) token provider value sent as `Authorization: Bearer x`; (g) query params skip `undefined`/`''`. `format.test.ts` for each formatter.
- [ ] **Step 2:** `npm test` → FAIL.
- [ ] **Step 3:** Implement client, format, endpoints, queries; Vite proxy `server.proxy['/api'] = { target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:3001', changeOrigin: true }`; `VITE_API_BASE_URL=/api/v1`.
- [ ] **Step 4:** `npm test && npm run build` → PASS. Commit `feat(frontend): typed API client, endpoints and query hooks`.

### Task 5: Auth provider (mock mode), guards, login/signup/role flow

**Files:** Create `src/auth/AuthProvider.tsx`, `src/auth/RequireRole.tsx`, `src/auth/authStorage.ts`, `src/auth/authStorage.test.ts`, `src/pages/NotFoundPage.tsx`. Modify `App.tsx`, `LoginPage.tsx`, `SignupPage.tsx`, `Navbar.tsx`.

**Interfaces — Produces:**

```ts
type AuthStatus = 'loading' | 'signedOut' | 'needsProfile' | 'signedIn';
interface AuthContextValue {
  status: AuthStatus; user: Me | null;
  signInWithGoogle(intendedRole: 'artist' | 'planner'): Promise<void>; // mock: stores token; supabase (Plan B): GIS → signInWithIdToken
  completeProfile(req: CreateMeRequest): Promise<Me>;
  signOut(): Promise<void>;
}
export function useAuth(): AuthContextValue;
export function homePathFor(user: Me): string; // artist w/o artistSlug → '/artist/onboarding', artist → '/artist/dashboard', planner → '/planner/dashboard'
```

Mock mode (`VITE_AUTH_MODE=mock`): Login → token `mock-artist`/`mock-planner`; Signup → token `mock-new`, then `completeProfile({role, fullName})` and swap token to `mock-<role>` (artist signup lands on onboarding because the mock `POST /me` returns `artistSlug: null`). Token in `localStorage['prasang.token']`. OTP tab stays but shows "Coming soon" (phone OTP is post-launch per spec). Buyer role renamed `planner`.
`RequireRole role="artist"` → loading spinner / redirect `/login?next=` / redirect to `homePathFor(user)` when role mismatches / `/signup` completion when `needsProfile`.
Navbar: signed-in shows "Dashboard" link (`homePathFor`) + "Sign out"; city select sourced from `useLocations`. `*` route → NotFoundPage.

- [ ] **Step 1: Failing tests** for `authStorage` (get/set/clear token) and `homePathFor` (3 cases).
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** implement. **Step 4:** `npm test && npm run build` PASS; with mock running, `curl -H 'Authorization: Bearer mock-new' localhost:3001/api/v1/me` → 404.
- [ ] **Step 5:** Commit `feat(frontend): auth provider with mock mode and role guards`.

### Task 6: Public pages — Home, Search, Profile (+ lead modal)

**Files:** Modify `HomePage.tsx`, `SearchPage.tsx`, `ArtistProfilePage.tsx`, `ArtistGrid.tsx`, `ArtistCard.tsx` (type `ArtistCard` from api types; guard `profileImageUrl` null with placeholder `/artists/magician.png`), create `src/components/QueryState.tsx`, `src/components/ContactModal.tsx` (extracted from profile page).

Behaviour:
- Home: `useSearchArtists({ artistType: active === 'all' ? undefined : active, size: 12, sort: 'relevance' })`.
- Search: all filter state → `SearchParams` (URL-synced via `useSearchParams` so links are shareable); cities/areas from `useLocations`; results/total from response; pagination "Load more" (page+1).
- Profile: `useArtist(slug)`; 404 → NotFound-style block "Artist not found" + link to search; media grid from `artist.media` (fallback to profile image if empty); reviews tab `useArtistReviews`; similar `useSimilarArtists`.
- ContactModal: requires auth — if signed out, show "Sign in with Google to see contact details" button (`signInWithGoogle('planner')`), prefill name/phone from `user`; fields add Event city (select from locations, default artist city); budget chips use `BUDGET_RANGE_LABELS`; submit `useCreateLead` → reveal `contactPhone`/`whatsappNumber` from response (no hard-coded numbers); `trackContactClick(slug)` on open. The sidebar WhatsApp button opens the modal instead of a hard-coded wa.me link.

- [ ] **Step 1:** Implement QueryState + ContactModal. **Step 2:** Wire pages. **Step 3:** `npm run build` PASS; `curl localhost:3001/api/v1/artists/nope` → 404, `/search/artists?artistType=dj` → only DJs.
- [ ] **Step 4:** Commit `feat(frontend): public pages read from API; contact modal creates leads`.

### Task 7: Artist area — Onboarding/profile edit, media, Dashboard, Leads

**Files:** Modify `artist/OnboardingPage.tsx`, `artist/DashboardPage.tsx`, `artist/LeadsPage.tsx`; create `src/components/ArtistSidebar.tsx` (shared sidebar with live plan usage from `PlanUsage`), `src/components/MediaUploader.tsx`.

Behaviour:
- Onboarding: if `useMyArtist` 404 → create mode, else edit mode prefilled. Step 0 adds **Contact phone** (required, 10 digits) and **WhatsApp number** (optional). Validation client-side mirrors 422 details (`details.fields`). Step 0 "Next" → `createArtist` (create mode) / `updateMyArtist`. Profile photo: `requestUploadUrl({kind:'avatar'})` → `uploadToUrl` → `setAvatar`. Step 1 media: MediaUploader (quota text from `MediaListResponse.quota`, delete, YouTube/Instagram URL add). Step 2 plan: "Launch Profile" → `updateMyArtist({isPublished:true})` then `startTrial({tier})` (409 trial_used ignored) → dashboard.
- Dashboard: all figures from `useArtistDashboard`; "View Profile" link uses `user.artistSlug`; greeting from `greetingName`.
- Leads: tabs `all|new|contacted|converted|declined|expired` with `counts`; banner from `plan.leadsRemaining`; locked lead card shows "Upgrade to see details" (no phone/call buttons); expanded card buttons "Mark contacted / Mark booked / Decline" → `useUpdateLead`.

- [ ] **Step 1–3:** implement; `npm run build` PASS; smoke via curl `GET /leads/artist?status=new` with artist token.
- [ ] **Step 4:** Commit `feat(frontend): artist onboarding, media, dashboard and leads on API`.

### Task 8: Planner area + Pricing/subscribe

**Files:** Modify `planner/DashboardPage.tsx`, `planner/InquiriesPage.tsx`, `PricingPage.tsx`; create `src/payments/razorpay.ts`.

**Interfaces — Produces:** `openCheckout(checkout: CreateSubscriptionResponse['checkout']): Promise<VerifyPaymentRequest>` — loads `https://checkout.razorpay.com/v1/checkout.js` and resolves on handler; when `keyId` starts with `rzp_test_mock` it resolves immediately with fake ids (mock mode).

Behaviour:
- Planner dashboard: metrics + upcoming from `summary`, recent = first 3 items. Inquiries: tabs from `counts`, artist data embedded in each item (no mockArtists lookups).
- Pricing: plans from `usePlans` (feature table rows = union of `features[].label` in order); monthly/annual toggle; CTA: signed-out → `/signup`; planner → hidden; artist on that tier → "Current plan"; otherwise `createSubscription` → `openCheckout` → `verifyPayment` → invalidate `mySubscription`/`dashboard` → toast "You're on Pro".

- [ ] **Step 1–3:** implement; `npm run build` PASS.
- [ ] **Step 4:** Delete `src/data/mockArtists.ts`, `src/data/mockPlannerActivity.ts`; `grep -r "mockArtists\|mockPlannerActivity" src` → no results; `npm run build && npm test` PASS.
- [ ] **Step 5:** Commit `feat(frontend): planner pages and subscriptions on API; remove inline mocks`.

### Task 9: End-to-end smoke of mock stack + docs

- [ ] **Step 1:** `mockoon/smoke.sh` extended to walk the main journeys with curl (planner: search → profile → POST lead; artist: me → dashboard → leads → PATCH lead; subscribe → verify).
- [ ] **Step 2:** Update `frontend/README.md` (replace Vite template text): setup, `npm run mock`, `npm run dev`, env vars, mock tokens.
- [ ] **Step 3:** Update `docs/backlog.md`: add E-A (contract + mock UI) as done; renumber so Plan B epics follow.
- [ ] **Step 4:** Commit `docs: mock stack runbook and backlog update`.

---

## Self-review notes
- Spec coverage: every spec §5 flow has endpoints in Task 1 table (auth 5.1, profile 5.2, search 5.3, leads 5.4, subscriptions 5.5 incl. trial from onboarding copy, media 5.6). Reviews are read-only (spec §4 says submission out of scope) — `GET /artists/{slug}/reviews` added because the profile page renders reviews; Plan B backs it with a `reviews` table seeded empty.
- Additions to spec found from UI: `contact-click` tracking, dashboard metrics with month-over-month change (Plan B needs `artist_daily_stats`), `locations` endpoint (Plan B `localities` table), 7-day trial (`/subscriptions/trial`), lead `eventCity`. Spec to be amended in Plan B's first task.
