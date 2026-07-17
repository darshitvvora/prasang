# Planner Dashboard — Design Spec

Date: 2026-07-17

## Problem

Prasang currently has a full artist-side dashboard (`/artist/dashboard`, `/artist/leads`, `/artist/onboarding`) for the supply side of the marketplace. There is no equivalent for the demand side: the event planner who searches artists (`/search`) and reaches out via the "Get Contact Info" flow on `/profile/:slug`. This spec adds a mirror-image "planner dashboard" area so planners can track who they've contacted and revisit artists they've saved.

## Scope

Frontend-only, matching the current stage of the codebase: everything today (`mockArtists.ts`, `LeadsPage`, artist `DashboardPage`) is driven by local mock data literals with no backend, no shared state/store, and no persistence. This feature follows the same pattern — no new global state, no API calls, no wiring into the real favorite-toggle state in `SearchPage`/`ArtistProfilePage` (those are page-local `useState` today, not shared anywhere).

## Routes

Added to `frontend/src/App.tsx`:

- `/planner/dashboard` → `pages/planner/DashboardPage.tsx`
- `/planner/inquiries` → `pages/planner/InquiriesPage.tsx`
- `/planner/saved` → `pages/planner/SavedArtistsPage.tsx`

## New files

- `frontend/src/pages/planner/DashboardPage.tsx`
- `frontend/src/pages/planner/InquiriesPage.tsx`
- `frontend/src/pages/planner/SavedArtistsPage.tsx`
- `frontend/src/pages/planner/PlannerPages.css` (shared styles for the three pages, sibling to `pages/artist/ArtistPages.css`)

## Layout & visual language

A `planner-layout` shell (sidebar + main), visually consistent with `artist-layout` in `ArtistPages.css` (same card/topbar/metric-grid classes and conventions), but with its own class names in `PlannerPages.css` to keep the two page groups independently stylable. Sidebar nav differs from the artist sidebar:

- Dashboard (`/planner/dashboard`)
- My Inquiries (`/planner/inquiries`)
- Saved Artists (`/planner/saved`)
- Browse Artists (`/search`)

No subscription/upgrade tier card in the planner sidebar — that concept is artist-specific (lead quotas, paid tiers). Instead, a simple promo card pointing at `/search` ("Looking for more artists?").

## Pages

### `/planner/dashboard`

- Header: greeting + "Browse Artists" quick action.
- 4 stat cards: Artists Contacted, Responses Received, Confirmed Bookings, Saved Artists.
- Upcoming event card: nearest event date among the planner's inquiries, shown with a countdown ("12 days to go").
- "Recent Inquiries" card: top 3 inquiries, each with artist name/photo, event, status badge; "View all" link to `/planner/inquiries`.
- "Saved Artists" card: top 3–4 saved artist cards (photo, name, type, rating); "View all" link to `/planner/saved`.

### `/planner/inquiries`

Mirrors `pages/artist/LeadsPage.tsx`'s filter-tabs + expandable-card pattern, flipped to the planner's perspective (list of artists *they* contacted, not leads contacting them).

- Status model: `pending` (request sent, artist hasn't responded) → `responded` (artist replied) → `confirmed` (booked) / `declined` (artist unavailable/declined).
- Filter tabs: All / Pending / Responded / Confirmed / Declined, each with a count badge.
- Each inquiry card shows: artist avatar/name/type, event type + date, budget range, status badge, time since contacted. Expandable detail area shows the notes submitted in the original contact form and a "View Profile" link to `/profile/:slug`.
- Mock data: a literal array of ~5 inquiries analogous to `LEADS` in `LeadsPage.tsx`, referencing a couple of slugs from `mockArtists.ts` for the "View Profile" links to resolve to real profile pages.

### `/planner/saved`

- Grid of favorited-artist cards, reusing the visual shape of `ArtistCard`/the search results card (photo, name, verified badge, rating, type, price range).
- Each card links to `/profile/:slug`.
- Empty-state and a "Browse more artists" CTA linking to `/search` below the grid.
- Mock data: a literal subset of `mockArtists` (3–5 entries) treated as "saved".

## Auth wiring

- `SignupPage` (`frontend/src/pages/SignupPage.tsx`): the `buyer` role branch currently redirects to `/` on both Google signup and OTP verify. Change both to redirect to `/planner/dashboard`. The `artist` branch (→ `/artist/onboarding`) is unchanged.
- `LoginPage` (`frontend/src/pages/LoginPage.tsx`): currently has no role concept and always redirects to `/artist/dashboard`. Add the same artist/buyer role-picker UI block used in `SignupPage` (`auth-role-grid` / `auth-role-card` styles already exist in `AuthPages.css`). Require a role selection before enabling the Google button / OTP send, same as signup. On successful Google login or OTP verify, redirect to `/artist/dashboard` if role is `artist`, `/planner/dashboard` if role is `buyer`.

## Out of scope

- No backend/API integration — all data is mock literals.
- No shared/global state connecting saved artists or inquiries across pages (e.g., a real favorites store, or actually recording contact-form submissions from `ArtistProfilePage` into the inquiries list). This is a UI scaffold matching the current mock-data stage of the app, not a data-layer change.
- No changes to `Navbar.tsx` — the planner dashboard is reached via login/signup redirect or direct URL, not a new top-level nav item, consistent with how `/artist/dashboard` is reached today.
