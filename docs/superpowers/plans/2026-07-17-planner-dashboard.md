# Planner Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a planner-facing dashboard area (`/planner/dashboard`, `/planner/inquiries`, `/planner/saved`) mirroring the existing artist dashboard, so event planners can track artists they've contacted and artists they've saved, and wire login/signup to route planners there.

**Architecture:** Three new page components under `frontend/src/pages/planner/`, sharing one `PlannerPages.css` stylesheet visually consistent with (but class-name-independent from) `pages/artist/ArtistPages.css`. A new mock-data module `frontend/src/data/mockPlannerActivity.ts` holds inquiry and saved-artist data, cross-referenced against the existing `mockArtists` array by `artistId` (DRY — no duplicated artist name/photo/rating fields). Three routes added to `App.tsx`. `LoginPage.tsx` gains the same artist/buyer role picker `SignupPage.tsx` already has, and both pages' buyer path now redirects to `/planner/dashboard`.

**Tech Stack:** React 19 + TypeScript, react-router-dom v7, lucide-react icons, plain CSS (no CSS modules — class names must not collide with existing global stylesheets), Vite. No test framework is configured in this project (see Global Constraints).

## Global Constraints

- Frontend-only. No backend/API calls, no new global state or context. All data is literal mock arrays, matching the existing pattern in `pages/artist/LeadsPage.tsx` and `data/mockArtists.ts`.
- Do not wire this feature to the real favorite-toggle state in `SearchPage.tsx`/`ArtistProfilePage.tsx` — those are page-local `useState`, not shared, and stay that way.
- Do not modify `Navbar.tsx` or add a new top-level nav item — the planner dashboard is reached via login/signup redirect or direct URL, same as `/artist/dashboard` today.
- CSS is loaded globally by Vite (no CSS Modules in this project) — every new class name in `PlannerPages.css` must be prefixed `planner-` so it cannot collide with `ArtistPages.css` classes of the same visual intent (e.g. `.metric-card` → `.planner-metric-card`).
- This project has **no test framework** (`frontend/package.json` has no `vitest`/`jest`; only `tsc -b`, `vite build`, `oxlint`). Verification for every task is: (1) TypeScript typecheck via `npx tsc --noEmit -p tsconfig.app.json` run from `frontend/`, and (2) a manual check in the running dev server (`npm run dev` in `frontend/`, then load the route in a browser) confirming the page renders with no console errors. Do not introduce a new test framework as part of this plan.
- Follow the existing dark-theme visual language: background `#0f0f0f`/`#1a1a1a`, borders `rgba(255,255,255,0.07)`, accent `var(--color-accent)`, heading font `var(--font-heading)`, body font `var(--font-body)` (all defined in `frontend/src/index.css`).

---

### Task 1: Mock planner-activity data module

**Files:**
- Create: `frontend/src/data/mockPlannerActivity.ts`

**Interfaces:**
- Produces: `InquiryStatus` (`'pending' | 'responded' | 'confirmed' | 'declined'`), `Inquiry` interface (`id`, `artistId`, `event`, `eventDate`, `daysToEvent`, `budgetMin`, `budgetMax`, `notes`, `status`, `contactedAt`), `INQUIRIES: Inquiry[]`, `STATUS_COLORS: Record<InquiryStatus, string>`, `SAVED_ARTIST_IDS: string[]` — all consumed by Tasks 3–5.
- Consumes: nothing (referenced `artistId` values must match entries in `frontend/src/data/mockArtists.ts`, which has ids `art-001` through `art-008`).

- [ ] **Step 1: Create the file**

```ts
// frontend/src/data/mockPlannerActivity.ts
export type InquiryStatus = 'pending' | 'responded' | 'confirmed' | 'declined';

export interface Inquiry {
  id: string;
  artistId: string;
  event: string;
  eventDate: string;
  daysToEvent: number;
  budgetMin: number;
  budgetMax: number;
  notes: string;
  status: InquiryStatus;
  contactedAt: string;
}

export const INQUIRIES: Inquiry[] = [
  {
    id: 'inq-1',
    artistId: 'art-001',
    event: 'Wedding Reception',
    eventDate: 'Jan 5, 2026',
    daysToEvent: 12,
    budgetMin: 15000,
    budgetMax: 25000,
    notes: 'Close-up magic for cocktail hour, ~150 guests.',
    status: 'confirmed',
    contactedAt: '3 days ago',
  },
  {
    id: 'inq-2',
    artistId: 'art-002',
    event: 'Sangeet Night',
    eventDate: 'Jan 18, 2026',
    daysToEvent: 25,
    budgetMin: 20000,
    budgetMax: 35000,
    notes: 'Need a Bollywood + EDM mix, 4-hour set.',
    status: 'responded',
    contactedAt: '1 day ago',
  },
  {
    id: 'inq-3',
    artistId: 'art-003',
    event: 'Anniversary Party',
    eventDate: 'Feb 2, 2026',
    daysToEvent: 40,
    budgetMin: 10000,
    budgetMax: 18000,
    notes: 'Live acoustic set for an intimate 40-guest dinner.',
    status: 'pending',
    contactedAt: '5 hours ago',
  },
  {
    id: 'inq-4',
    artistId: 'art-004',
    event: 'Corporate Offsite',
    eventDate: 'Dec 28, 2025',
    daysToEvent: -2,
    budgetMin: 25000,
    budgetMax: 40000,
    notes: '30-minute stand-up set to open the evening.',
    status: 'declined',
    contactedAt: '10 days ago',
  },
  {
    id: 'inq-5',
    artistId: 'art-005',
    event: 'Birthday Party',
    eventDate: 'Jan 10, 2026',
    daysToEvent: 17,
    budgetMin: 30000,
    budgetMax: 50000,
    notes: 'Live band, 2-hour set, outdoor lawn setup.',
    status: 'pending',
    contactedAt: '2 hours ago',
  },
];

export const STATUS_COLORS: Record<InquiryStatus, string> = {
  pending: '#f59e0b',
  responded: '#60a5fa',
  confirmed: '#4ade80',
  declined: '#666',
};

export const SAVED_ARTIST_IDS = ['art-002', 'art-006', 'art-007', 'art-008'];
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: exits with no output (success).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/mockPlannerActivity.ts
git commit -m "feat: add mock planner-activity data (inquiries, saved artists)"
```

---

### Task 2: Planner pages shared stylesheet

**Files:**
- Create: `frontend/src/pages/planner/PlannerPages.css`

**Interfaces:**
- Produces: all `.planner-*` CSS classes referenced by Tasks 3–5's JSX (`planner-layout`, `planner-sidebar*`, `planner-promo-*`, `planner-main`, `planner-topbar*`, `planner-page-*`, `planner-metrics-grid`, `planner-metric-*`, `planner-upcoming-*`, `planner-dashboard-row`, `planner-dashboard-card`, `planner-card-*`, `planner-inquiry-preview-*`, `planner-inquiry-avatar`, `planner-inquiry-info`, `planner-inquiry-name`, `planner-inquiry-event`, `planner-status-badge`, `planner-empty-note`, `planner-saved-preview-*`, `planner-filter-tabs`, `planner-filter-tab`, `planner-tab-count`, `planner-inquiry-cards`, `planner-inquiries-empty`, `planner-inquiry-card*`, `planner-inquiry-time`, `planner-inquiry-notes`, `planner-inquiry-view-profile-btn`, `planner-inquiry-expand-btn`, `planner-saved-grid`, `planner-saved-card*`, `planner-saved-empty`, `planner-saved-browse-cta`).
- Consumes: CSS custom properties `--color-accent`, `--color-accent-hover`, `--font-heading`, `--font-body` defined in `frontend/src/index.css`.

- [ ] **Step 1: Create the file**

```css
/* frontend/src/pages/planner/PlannerPages.css */

/* ─── Shared layout ─── */
.planner-layout {
  display: flex;
  min-height: 100vh;
  background: #0f0f0f;
  color: #ffffff;
  font-family: var(--font-body);
}

/* ─── Sidebar ─── */
.planner-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #141414;
  border-right: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  gap: 8px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.planner-sidebar-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 800;
  color: var(--color-accent);
  margin-bottom: 32px;
  padding: 0 8px;
}

.planner-sidebar-logo-hindi {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  font-family: var(--font-body);
  font-weight: 400;
}

.planner-sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.planner-sidebar-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
  text-decoration: none;
  transition: all 0.2s;
}

.planner-sidebar-link:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.85);
}

.planner-sidebar-link.active {
  background: rgba(212, 245, 63, 0.1);
  color: var(--color-accent);
}

/* Promo card (planner sidebar has no subscription tier, unlike artist sidebar) */
.planner-promo-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
}

.planner-promo-title {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 4px;
}

.planner-promo-note {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 12px;
  line-height: 1.4;
}

.planner-promo-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 12px;
  border-radius: 9px;
  background: var(--color-accent);
  color: #0f0f0f;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s;
}

.planner-promo-btn:hover { background: var(--color-accent-hover); }

/* ─── Main area ─── */
.planner-main {
  flex: 1;
  padding: 32px 40px;
  overflow-y: auto;
  max-width: 1100px;
}

.planner-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
}

.planner-page-title {
  font-family: var(--font-heading);
  font-size: 28px;
  font-weight: 800;
  color: #ffffff;
  margin: 0 0 4px;
}

.planner-page-sub {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

.planner-topbar-cta {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: all 0.2s;
}

.planner-topbar-cta:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

/* ─── Metrics ─── */
.planner-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.planner-metric-card {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 20px;
}

.planner-metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.planner-metric-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.planner-metric-icon { color: rgba(255, 255, 255, 0.2); }

.planner-metric-value {
  font-family: var(--font-heading);
  font-size: 32px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1;
}

/* ─── Upcoming event card ─── */
.planner-upcoming-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(212, 245, 63, 0.06);
  border: 1px solid rgba(212, 245, 63, 0.2);
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 24px;
}

.planner-upcoming-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(212, 245, 63, 0.15);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.planner-upcoming-info { flex: 1; }

.planner-upcoming-title {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 2px;
}

.planner-upcoming-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.planner-upcoming-days {
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 800;
  color: var(--color-accent);
  white-space: nowrap;
}

.planner-upcoming-empty {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
}

/* ─── Dashboard cards row ─── */
.planner-dashboard-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.planner-dashboard-card {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 16px;
  padding: 24px;
}

.planner-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.planner-card-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.planner-card-action {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 500;
}

/* Inquiry preview list (dashboard) */
.planner-inquiry-preview-list { display: flex; flex-direction: column; gap: 14px; }

.planner-inquiry-preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.planner-inquiry-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.planner-inquiry-avatar img { width: 100%; height: 100%; object-fit: cover; }

.planner-inquiry-info { flex: 1; }
.planner-inquiry-name { font-size: 14px; font-weight: 600; color: #ffffff; }
.planner-inquiry-event { font-size: 12px; color: rgba(255, 255, 255, 0.4); }

.planner-status-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 8px;
  text-transform: capitalize;
}

.planner-empty-note {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
  padding: 20px 0;
}

/* Saved artists preview (dashboard) */
.planner-saved-preview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.planner-saved-preview-card {
  text-decoration: none;
  display: block;
}

.planner-saved-preview-img {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 10px;
  object-fit: cover;
  margin-bottom: 8px;
}

.planner-saved-preview-name {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 2px;
}

.planner-saved-preview-type {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

/* ─── Inquiries page ─── */
.planner-filter-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.planner-filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.planner-filter-tab:hover { color: rgba(255, 255, 255, 0.8); }

.planner-filter-tab.active {
  background: rgba(212, 245, 63, 0.1);
  border-color: rgba(212, 245, 63, 0.3);
  color: var(--color-accent);
}

.planner-tab-count {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 700;
}

.planner-filter-tab.active .planner-tab-count {
  background: rgba(212, 245, 63, 0.15);
  color: var(--color-accent);
}

.planner-inquiry-cards { display: flex; flex-direction: column; gap: 14px; }

.planner-inquiries-empty {
  text-align: center;
  padding: 60px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 15px;
}

.planner-inquiry-card {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 20px;
  transition: border-color 0.2s;
}

.planner-inquiry-card:hover { border-color: rgba(255, 255, 255, 0.14); }

.planner-inquiry-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.planner-inquiry-card-left { display: flex; align-items: center; gap: 12px; }

.planner-inquiry-card-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.planner-inquiry-card-name { font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 4px; }

.planner-inquiry-card-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.planner-inquiry-card-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.planner-inquiry-card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }

.planner-inquiry-time { font-size: 11px; color: rgba(255, 255, 255, 0.3); }

.planner-inquiry-card-event {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 12px;
}

.planner-inquiry-event-type { font-size: 14px; font-weight: 600; color: rgba(255, 255, 255, 0.8); }

.planner-inquiry-budget {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-accent);
}

.planner-inquiry-card-expanded {
  padding: 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 8px;
}

.planner-inquiry-notes {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.6;
  margin-bottom: 14px;
}

.planner-inquiry-view-profile-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  transition: all 0.2s;
}

.planner-inquiry-view-profile-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

.planner-inquiry-expand-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
  cursor: pointer;
  transition: color 0.2s;
  padding: 0;
}

.planner-inquiry-expand-btn:hover { color: rgba(255, 255, 255, 0.65); }

/* ─── Saved artists page ─── */
.planner-saved-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.planner-saved-card {
  display: block;
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 16px;
  overflow: hidden;
  text-decoration: none;
  transition: border-color 0.2s;
}

.planner-saved-card:hover { border-color: rgba(255, 255, 255, 0.16); }

.planner-saved-card-img-wrap { position: relative; }

.planner-saved-card-img {
  width: 100%;
  height: 180px;
  object-fit: cover;
  display: block;
}

.planner-saved-card-verified {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  padding: 4px;
  color: var(--color-accent);
  display: flex;
}

.planner-saved-card-body { padding: 16px; }

.planner-saved-card-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.planner-saved-card-name { font-size: 15px; font-weight: 700; color: #ffffff; }

.planner-saved-card-rating {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
}

.planner-saved-card-location {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 10px;
}

.planner-saved-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.planner-saved-card-type {
  font-size: 11px;
  font-weight: 700;
  color: #0f0f0f;
  padding: 3px 9px;
  border-radius: 7px;
}

.planner-saved-card-price {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-accent);
}

.planner-saved-empty {
  text-align: center;
  padding: 60px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 15px;
}

.planner-saved-browse-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 24px;
  padding: 11px 22px;
  border-radius: 10px;
  background: var(--color-accent);
  color: #0f0f0f;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s;
}

.planner-saved-browse-cta:hover { background: var(--color-accent-hover); }

/* ─── Responsive ─── */
@media (max-width: 900px) {
  .planner-sidebar { display: none; }
  .planner-main { padding: 24px 20px; }
  .planner-metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .planner-dashboard-row { grid-template-columns: 1fr; }
  .planner-saved-preview-grid { grid-template-columns: repeat(2, 1fr); }
  .planner-saved-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .planner-metrics-grid { grid-template-columns: 1fr 1fr; }
  .planner-saved-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/planner/PlannerPages.css
git commit -m "feat: add shared stylesheet for planner dashboard pages"
```

(No typecheck applies to a CSS-only file; Task 3 will confirm this file loads correctly once a page imports it.)

---

### Task 3: Planner Dashboard page + route

**Files:**
- Create: `frontend/src/pages/planner/DashboardPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `mockArtists` from `frontend/src/data/mockArtists.ts`; `INQUIRIES`, `STATUS_COLORS`, `SAVED_ARTIST_IDS` from Task 1's `frontend/src/data/mockPlannerActivity.ts`; `ARTIST_TYPE_LABELS` from `frontend/src/types/artist.ts`; all `.planner-*` classes from Task 2's `PlannerPages.css`.
- Produces: default export `DashboardPage` component, mounted at route `/planner/dashboard`.

- [ ] **Step 1: Create the page component**

```tsx
// frontend/src/pages/planner/DashboardPage.tsx
import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Heart, CheckCircle2, Calendar, ChevronRight, Search, Star } from 'lucide-react';
import { mockArtists } from '../../data/mockArtists';
import { INQUIRIES, STATUS_COLORS, SAVED_ARTIST_IDS } from '../../data/mockPlannerActivity';
import { ARTIST_TYPE_LABELS } from '../../types/artist';
import './PlannerPages.css';

export default function DashboardPage() {
  const respondedCount = INQUIRIES.filter((i) => i.status === 'responded' || i.status === 'confirmed').length;
  const confirmedCount = INQUIRIES.filter((i) => i.status === 'confirmed').length;
  const savedArtists = mockArtists.filter((a) => SAVED_ARTIST_IDS.includes(a.artistId));

  const upcoming = INQUIRIES
    .filter((i) => i.status !== 'declined' && i.daysToEvent >= 0)
    .sort((a, b) => a.daysToEvent - b.daysToEvent)[0];
  const upcomingArtist = upcoming ? mockArtists.find((a) => a.artistId === upcoming.artistId) : undefined;

  const recentInquiries = [...INQUIRIES].sort((a, b) => a.daysToEvent - b.daysToEvent).slice(0, 3);

  return (
    <div className="planner-layout">
      <aside className="planner-sidebar">
        <Link to="/" className="planner-sidebar-logo">
          <span>prasang</span>
          <span className="planner-sidebar-logo-hindi">प्रसंग</span>
        </Link>

        <nav className="planner-sidebar-nav">
          <Link to="/planner/dashboard" className="planner-sidebar-link active">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link to="/planner/inquiries" className="planner-sidebar-link">
            <MessageCircle size={18} /> My Inquiries
          </Link>
          <Link to="/planner/saved" className="planner-sidebar-link">
            <Heart size={18} /> Saved Artists
          </Link>
          <Link to="/search" className="planner-sidebar-link">
            <Search size={18} /> Browse Artists
          </Link>
        </nav>

        <div className="planner-promo-card">
          <div className="planner-promo-title">Looking for more artists?</div>
          <div className="planner-promo-note">Search magicians, DJs, singers and more near you.</div>
          <Link to="/search" className="planner-promo-btn">
            Browse Artists <ChevronRight size={14} />
          </Link>
        </div>
      </aside>

      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">Dashboard</h1>
            <p className="planner-page-sub">Track the artists you've reached out to</p>
          </div>
          <Link to="/search" className="planner-topbar-cta">
            <Search size={16} /> Browse Artists
          </Link>
        </header>

        <div className="planner-metrics-grid">
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Artists Contacted</span>
              <span className="planner-metric-icon"><MessageCircle size={20} /></span>
            </div>
            <div className="planner-metric-value">{INQUIRIES.length}</div>
          </div>
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Responses Received</span>
              <span className="planner-metric-icon"><Star size={20} /></span>
            </div>
            <div className="planner-metric-value">{respondedCount}</div>
          </div>
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Confirmed Bookings</span>
              <span className="planner-metric-icon"><CheckCircle2 size={20} /></span>
            </div>
            <div className="planner-metric-value">{confirmedCount}</div>
          </div>
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Saved Artists</span>
              <span className="planner-metric-icon"><Heart size={20} /></span>
            </div>
            <div className="planner-metric-value">{savedArtists.length}</div>
          </div>
        </div>

        {upcoming && upcomingArtist ? (
          <div className="planner-upcoming-card">
            <div className="planner-upcoming-icon"><Calendar size={20} /></div>
            <div className="planner-upcoming-info">
              <div className="planner-upcoming-title">{upcoming.event} with {upcomingArtist.name}</div>
              <div className="planner-upcoming-sub">{upcoming.eventDate}</div>
            </div>
            <div className="planner-upcoming-days">{upcoming.daysToEvent}d to go</div>
          </div>
        ) : (
          <div className="planner-upcoming-card">
            <div className="planner-upcoming-icon"><Calendar size={20} /></div>
            <div className="planner-upcoming-empty">No upcoming events yet — browse artists to plan your next one.</div>
          </div>
        )}

        <div className="planner-dashboard-row">
          <div className="planner-dashboard-card">
            <div className="planner-card-header">
              <h2 className="planner-card-title">Recent Inquiries</h2>
              <Link to="/planner/inquiries" className="planner-card-action">View all <ChevronRight size={14} /></Link>
            </div>
            {recentInquiries.length === 0 ? (
              <p className="planner-empty-note">You haven't contacted any artists yet.</p>
            ) : (
              <div className="planner-inquiry-preview-list">
                {recentInquiries.map((inquiry) => {
                  const artist = mockArtists.find((a) => a.artistId === inquiry.artistId);
                  if (!artist) return null;
                  return (
                    <div key={inquiry.id} className="planner-inquiry-preview-item">
                      <div className="planner-inquiry-avatar">
                        <img src={artist.profileImageUrl} alt={artist.name} />
                      </div>
                      <div className="planner-inquiry-info">
                        <div className="planner-inquiry-name">{artist.name}</div>
                        <div className="planner-inquiry-event">{inquiry.event} · {inquiry.eventDate}</div>
                      </div>
                      <span
                        className="planner-status-badge"
                        style={{ background: `${STATUS_COLORS[inquiry.status]}20`, color: STATUS_COLORS[inquiry.status] }}
                      >
                        {inquiry.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="planner-dashboard-card">
            <div className="planner-card-header">
              <h2 className="planner-card-title">Saved Artists</h2>
              <Link to="/planner/saved" className="planner-card-action">View all <ChevronRight size={14} /></Link>
            </div>
            {savedArtists.length === 0 ? (
              <p className="planner-empty-note">You haven't saved any artists yet.</p>
            ) : (
              <div className="planner-saved-preview-grid">
                {savedArtists.slice(0, 4).map((artist) => (
                  <Link to={`/profile/${artist.slug}`} key={artist.artistId} className="planner-saved-preview-card">
                    <img src={artist.profileImageUrl} alt={artist.name} className="planner-saved-preview-img" />
                    <div className="planner-saved-preview-name">{artist.name}</div>
                    <div className="planner-saved-preview-type">{ARTIST_TYPE_LABELS[artist.artistType]}</div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Wire the route in `App.tsx`**

In `frontend/src/App.tsx`, add the import (after the existing `LeadsPage` import):

```tsx
import PlannerDashboardPage from './pages/planner/DashboardPage';
```

Add the route (after the `/artist/leads` route):

```tsx
        <Route path="/planner/dashboard" element={<PlannerDashboardPage />} />
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: exits with no output (success).

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`
Open `http://localhost:5173/planner/dashboard` in a browser. Expected: sidebar with Dashboard/My Inquiries/Saved Artists/Browse Artists links, 4 metric cards (Artists Contacted: 5, Responses Received: 2, Confirmed Bookings: 1, Saved Artists: 4), an upcoming-event banner, and Recent Inquiries + Saved Artists cards with artist photos loaded — no errors in the browser console. Stop the dev server after checking.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/planner/DashboardPage.tsx frontend/src/App.tsx
git commit -m "feat: add planner dashboard page and route"
```

---

### Task 4: Planner Inquiries page + route

**Files:**
- Create: `frontend/src/pages/planner/InquiriesPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: same data sources as Task 3 (`mockArtists`, `INQUIRIES`, `STATUS_COLORS`, `InquiryStatus` type from `mockPlannerActivity.ts`, `ARTIST_TYPE_LABELS`), plus `.planner-*` classes from Task 2.
- Produces: default export `InquiriesPage` component, mounted at route `/planner/inquiries`.

- [ ] **Step 1: Create the page component**

```tsx
// frontend/src/pages/planner/InquiriesPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Heart, Search, Calendar, MapPin, IndianRupee, ChevronDown, ExternalLink, ChevronRight } from 'lucide-react';
import { mockArtists } from '../../data/mockArtists';
import { INQUIRIES, STATUS_COLORS } from '../../data/mockPlannerActivity';
import type { InquiryStatus } from '../../data/mockPlannerActivity';
import { ARTIST_TYPE_LABELS } from '../../types/artist';
import './PlannerPages.css';

type FilterStatus = 'all' | InquiryStatus;

export default function InquiriesPage() {
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = filter === 'all' ? INQUIRIES : INQUIRIES.filter((i) => i.status === filter);
  const counts = {
    all: INQUIRIES.length,
    pending: INQUIRIES.filter((i) => i.status === 'pending').length,
    responded: INQUIRIES.filter((i) => i.status === 'responded').length,
    confirmed: INQUIRIES.filter((i) => i.status === 'confirmed').length,
    declined: INQUIRIES.filter((i) => i.status === 'declined').length,
  };

  return (
    <div className="planner-layout">
      <aside className="planner-sidebar">
        <Link to="/" className="planner-sidebar-logo">
          <span>prasang</span>
          <span className="planner-sidebar-logo-hindi">प्रसंग</span>
        </Link>
        <nav className="planner-sidebar-nav">
          <Link to="/planner/dashboard" className="planner-sidebar-link">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link to="/planner/inquiries" className="planner-sidebar-link active">
            <MessageCircle size={18} /> My Inquiries
          </Link>
          <Link to="/planner/saved" className="planner-sidebar-link">
            <Heart size={18} /> Saved Artists
          </Link>
          <Link to="/search" className="planner-sidebar-link">
            <Search size={18} /> Browse Artists
          </Link>
        </nav>
        <div className="planner-promo-card">
          <div className="planner-promo-title">Looking for more artists?</div>
          <div className="planner-promo-note">Search magicians, DJs, singers and more near you.</div>
          <Link to="/search" className="planner-promo-btn">
            Browse Artists <ChevronRight size={14} />
          </Link>
        </div>
      </aside>

      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">My Inquiries</h1>
            <p className="planner-page-sub">Artists you've reached out to for your events</p>
          </div>
        </header>

        <div className="planner-filter-tabs">
          {(['all', 'pending', 'responded', 'confirmed', 'declined'] as FilterStatus[]).map((s) => (
            <button
              key={s}
              className={`planner-filter-tab${filter === s ? ' active' : ''}`}
              onClick={() => setFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
              <span className="planner-tab-count">{counts[s]}</span>
            </button>
          ))}
        </div>

        <div className="planner-inquiry-cards">
          {filtered.length === 0 && (
            <div className="planner-inquiries-empty">No inquiries in this category yet.</div>
          )}
          {filtered.map((inquiry) => {
            const artist = mockArtists.find((a) => a.artistId === inquiry.artistId);
            if (!artist) return null;
            return (
              <div key={inquiry.id} className="planner-inquiry-card">
                <div className="planner-inquiry-card-top">
                  <div className="planner-inquiry-card-left">
                    <img src={artist.profileImageUrl} alt={artist.name} className="planner-inquiry-card-avatar" />
                    <div>
                      <div className="planner-inquiry-card-name">{artist.name}</div>
                      <div className="planner-inquiry-card-meta">
                        <span><Calendar size={12} /> {inquiry.eventDate}</span>
                        <span><MapPin size={12} /> {artist.locationArea}, {artist.locationCity}</span>
                      </div>
                    </div>
                  </div>
                  <div className="planner-inquiry-card-right">
                    <span
                      className="planner-status-badge"
                      style={{ background: `${STATUS_COLORS[inquiry.status]}20`, color: STATUS_COLORS[inquiry.status] }}
                    >
                      {inquiry.status}
                    </span>
                    <span className="planner-inquiry-time">{inquiry.contactedAt}</span>
                  </div>
                </div>

                <div className="planner-inquiry-card-event">
                  <span className="planner-inquiry-event-type">{inquiry.event} · {ARTIST_TYPE_LABELS[artist.artistType]}</span>
                  <span className="planner-inquiry-budget">
                    <IndianRupee size={12} />
                    {(inquiry.budgetMin / 1000).toFixed(0)}k – {(inquiry.budgetMax / 1000).toFixed(0)}k
                  </span>
                </div>

                {expanded === inquiry.id && (
                  <div className="planner-inquiry-card-expanded">
                    <div className="planner-inquiry-notes">{inquiry.notes}</div>
                    <Link to={`/profile/${artist.slug}`} className="planner-inquiry-view-profile-btn">
                      <ExternalLink size={15} /> View Profile
                    </Link>
                  </div>
                )}

                <button
                  className="planner-inquiry-expand-btn"
                  onClick={() => setExpanded(expanded === inquiry.id ? null : inquiry.id)}
                >
                  {expanded === inquiry.id ? 'Hide details' : 'View details'}
                  <ChevronDown
                    size={14}
                    style={{ transform: expanded === inquiry.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Wire the route in `App.tsx`**

Add the import (after `PlannerDashboardPage`):

```tsx
import PlannerInquiriesPage from './pages/planner/InquiriesPage';
```

Add the route (after `/planner/dashboard`):

```tsx
        <Route path="/planner/inquiries" element={<PlannerInquiriesPage />} />
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: exits with no output (success).

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`
Open `http://localhost:5173/planner/inquiries`. Expected: filter tabs show counts All 5 / Pending 2 / Responded 1 / Confirmed 1 / Declined 1; clicking each tab filters the card list; clicking "View details" on a card expands it to show notes and a working "View Profile" link that navigates to `/profile/<slug>`. No console errors. Stop the dev server after checking.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/planner/InquiriesPage.tsx frontend/src/App.tsx
git commit -m "feat: add planner inquiries page and route"
```

---

### Task 5: Planner Saved Artists page + route

**Files:**
- Create: `frontend/src/pages/planner/SavedArtistsPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `mockArtists`, `SAVED_ARTIST_IDS` (from Task 1), `ARTIST_TYPE_LABELS`, `ARTIST_TYPE_COLORS` from `frontend/src/types/artist.ts`, `.planner-*` classes from Task 2.
- Produces: default export `SavedArtistsPage` component, mounted at route `/planner/saved`.

- [ ] **Step 1: Create the page component**

```tsx
// frontend/src/pages/planner/SavedArtistsPage.tsx
import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Heart, Search, MapPin, Star, BadgeCheck, ChevronRight } from 'lucide-react';
import { mockArtists } from '../../data/mockArtists';
import { SAVED_ARTIST_IDS } from '../../data/mockPlannerActivity';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS } from '../../types/artist';
import './PlannerPages.css';

function formatPrice(n: number) {
  return n >= 1000 ? `₹${(n / 1000).toFixed(0)}K` : `₹${n}`;
}

export default function SavedArtistsPage() {
  const savedArtists = mockArtists.filter((a) => SAVED_ARTIST_IDS.includes(a.artistId));

  return (
    <div className="planner-layout">
      <aside className="planner-sidebar">
        <Link to="/" className="planner-sidebar-logo">
          <span>prasang</span>
          <span className="planner-sidebar-logo-hindi">प्रसंग</span>
        </Link>
        <nav className="planner-sidebar-nav">
          <Link to="/planner/dashboard" className="planner-sidebar-link">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link to="/planner/inquiries" className="planner-sidebar-link">
            <MessageCircle size={18} /> My Inquiries
          </Link>
          <Link to="/planner/saved" className="planner-sidebar-link active">
            <Heart size={18} /> Saved Artists
          </Link>
          <Link to="/search" className="planner-sidebar-link">
            <Search size={18} /> Browse Artists
          </Link>
        </nav>
        <div className="planner-promo-card">
          <div className="planner-promo-title">Looking for more artists?</div>
          <div className="planner-promo-note">Search magicians, DJs, singers and more near you.</div>
          <Link to="/search" className="planner-promo-btn">
            Browse Artists <ChevronRight size={14} />
          </Link>
        </div>
      </aside>

      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">Saved Artists</h1>
            <p className="planner-page-sub">Artists you've favorited while browsing</p>
          </div>
        </header>

        {savedArtists.length === 0 ? (
          <div className="planner-saved-empty">
            You haven't saved any artists yet.
            <div>
              <Link to="/search" className="planner-saved-browse-cta">
                <Search size={16} /> Browse Artists
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="planner-saved-grid">
              {savedArtists.map((artist) => (
                <Link to={`/profile/${artist.slug}`} key={artist.artistId} className="planner-saved-card">
                  <div className="planner-saved-card-img-wrap">
                    <img src={artist.profileImageUrl} alt={artist.name} className="planner-saved-card-img" />
                    {artist.isVerified && (
                      <span className="planner-saved-card-verified">
                        <BadgeCheck size={16} />
                      </span>
                    )}
                  </div>
                  <div className="planner-saved-card-body">
                    <div className="planner-saved-card-name-row">
                      <span className="planner-saved-card-name">{artist.name}</span>
                      <span className="planner-saved-card-rating">
                        <Star size={13} fill="currentColor" /> {artist.averageRating}
                      </span>
                    </div>
                    <div className="planner-saved-card-location">
                      <MapPin size={12} /> {artist.locationArea}, {artist.locationCity}
                    </div>
                    <div className="planner-saved-card-footer">
                      <span
                        className="planner-saved-card-type"
                        style={{ background: ARTIST_TYPE_COLORS[artist.artistType] }}
                      >
                        {ARTIST_TYPE_LABELS[artist.artistType]}
                      </span>
                      <span className="planner-saved-card-price">
                        {formatPrice(artist.perEventRateMin)}–{formatPrice(artist.perEventRateMax)}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
            <Link to="/search" className="planner-saved-browse-cta">
              <Search size={16} /> Browse more artists
            </Link>
          </>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Wire the route in `App.tsx`**

Add the import (after `PlannerInquiriesPage`):

```tsx
import PlannerSavedArtistsPage from './pages/planner/SavedArtistsPage';
```

Add the route (after `/planner/inquiries`):

```tsx
        <Route path="/planner/saved" element={<PlannerSavedArtistsPage />} />
```

After this step, `frontend/src/App.tsx` should read in full:

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import SearchPage from './pages/SearchPage';
import ArtistProfilePage from './pages/ArtistProfilePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import PricingPage from './pages/PricingPage';
import DashboardPage from './pages/artist/DashboardPage';
import OnboardingPage from './pages/artist/OnboardingPage';
import LeadsPage from './pages/artist/LeadsPage';
import PlannerDashboardPage from './pages/planner/DashboardPage';
import PlannerInquiriesPage from './pages/planner/InquiriesPage';
import PlannerSavedArtistsPage from './pages/planner/SavedArtistsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/profile/:slug" element={<ArtistProfilePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/artist/dashboard" element={<DashboardPage />} />
        <Route path="/artist/onboarding" element={<OnboardingPage />} />
        <Route path="/artist/leads" element={<LeadsPage />} />
        <Route path="/planner/dashboard" element={<PlannerDashboardPage />} />
        <Route path="/planner/inquiries" element={<PlannerInquiriesPage />} />
        <Route path="/planner/saved" element={<PlannerSavedArtistsPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: exits with no output (success).

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`
Open `http://localhost:5173/planner/saved`. Expected: a 3-column grid of 4 saved-artist cards (DJ Krish, Meera Kapoor, Vikram Bubbles, Aditya Naik), each showing photo, name, rating, location, type badge, and price range, each linking to its `/profile/:slug`. A "Browse more artists" button below the grid links to `/search`. No console errors. Stop the dev server after checking.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/planner/SavedArtistsPage.tsx frontend/src/App.tsx
git commit -m "feat: add planner saved artists page and route"
```

---

### Task 6: Signup buyer redirect → planner dashboard

**Files:**
- Modify: `frontend/src/pages/SignupPage.tsx:42` and `frontend/src/pages/SignupPage.tsx:49`

**Interfaces:**
- Consumes: route `/planner/dashboard` (produced by Task 3).
- Produces: nothing new — changes existing redirect behavior only.

- [ ] **Step 1: Update both buyer redirects**

In `frontend/src/pages/SignupPage.tsx`, both `handleSendOTP`'s companion `handleVerifyOTP` (line 42) and `handleGoogleSignup` (line 49) currently contain the identical line:

```tsx
    window.location.href = role === 'artist' ? '/artist/onboarding' : '/';
```

Replace **both** occurrences with:

```tsx
    window.location.href = role === 'artist' ? '/artist/onboarding' : '/planner/dashboard';
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: exits with no output (success).

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev`
Open `http://localhost:5173/signup`, select "I'm Planning", switch to the Google tab, and click "Continue with Google". Expected: after the simulated delay, the browser navigates to `/planner/dashboard`. Repeat selecting "I'm an Artist" and confirm it still navigates to `/artist/onboarding`. Stop the dev server after checking.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SignupPage.tsx
git commit -m "fix: route planner signups to /planner/dashboard instead of home"
```

---

### Task 7: Login role picker + role-based redirect

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx` (full-file replacement below)

**Interfaces:**
- Consumes: routes `/artist/dashboard` (existing) and `/planner/dashboard` (Task 3); `.auth-role-grid`/`.auth-role-card`/`.auth-role-icon`/`.auth-role-label`/`.auth-role-desc`/`.auth-role-select-hint` classes, already defined in `frontend/src/pages/AuthPages.css` (used today by `SignupPage.tsx`) — no CSS changes needed.
- Produces: nothing consumed elsewhere — this is a leaf page.

- [ ] **Step 1: Replace the full file content**

Replace the entire content of `frontend/src/pages/LoginPage.tsx` with:

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Phone, ArrowLeft, RefreshCw } from 'lucide-react';
import './AuthPages.css';

type Role = 'artist' | 'buyer';
type AuthTab = 'google' | 'otp';
type OtpStep = 'phone' | 'verify';

export default function LoginPage() {
  const [role, setRole] = useState<Role | null>(null);
  const [tab, setTab] = useState<AuthTab>('google');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [otpStep, setOtpStep] = useState<OtpStep>('phone');
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);

  function startCountdown() {
    setCountdown(60);
    const t = setInterval(() => {
      setCountdown((c) => { if (c <= 1) { clearInterval(t); return 0; } return c - 1; });
    }, 1000);
  }

  async function handleSendOTP(e: React.FormEvent) {
    e.preventDefault();
    if (!role || !/^[6-9]\d{9}$/.test(phone)) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    setOtpStep('verify');
    startCountdown();
  }

  async function handleVerifyOTP(e: React.FormEvent) {
    e.preventDefault();
    if (otp.length < 6) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    window.location.href = role === 'artist' ? '/artist/dashboard' : '/planner/dashboard';
  }

  async function handleGoogleLogin() {
    if (!role) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 600));
    window.location.href = role === 'artist' ? '/artist/dashboard' : '/planner/dashboard';
  }

  return (
    <div className="auth-page">
      <div className="auth-bg" aria-hidden="true" />

      <div className="auth-card">
        {/* Logo */}
        <Link to="/" className="auth-logo">
          <span className="auth-logo-text">prasang</span>
          <span className="auth-logo-hindi">प्रसंग</span>
        </Link>

        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">Sign in to your Prasang account</p>

        {/* Role selection */}
        <div className="auth-role-grid">
          <button
            className={`auth-role-card${role === 'artist' ? ' selected' : ''}`}
            onClick={() => setRole('artist')}
          >
            <span className="auth-role-icon">🎤</span>
            <span className="auth-role-label">I'm an Artist</span>
            <span className="auth-role-desc">List my services & get discovered</span>
          </button>
          <button
            className={`auth-role-card${role === 'buyer' ? ' selected' : ''}`}
            onClick={() => setRole('buyer')}
          >
            <span className="auth-role-icon">🎉</span>
            <span className="auth-role-label">I'm Planning</span>
            <span className="auth-role-desc">Find artists for my event</span>
          </button>
        </div>

        {!role && (
          <p className="auth-role-select-hint">Select your role to continue</p>
        )}

        {/* Tab switch */}
        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'google'}
            className={`auth-tab${tab === 'google' ? ' active' : ''}`}
            onClick={() => setTab('google')}
          >
            Google
          </button>
          <button
            role="tab"
            aria-selected={tab === 'otp'}
            className={`auth-tab${tab === 'otp' ? ' active' : ''}`}
            onClick={() => setTab('otp')}
          >
            <Phone size={16} /> Mobile OTP
          </button>
        </div>

        {/* Google Login */}
        {tab === 'google' && (
          <div className="auth-google-section">
            <button className="auth-google-btn" onClick={handleGoogleLogin} disabled={loading || !role}>
              <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                <path fill="none" d="M0 0h48v48H0z"/>
              </svg>
              {loading ? 'Signing in...' : 'Continue with Google'}
            </button>
            <p className="auth-google-note">
              90%+ of artists use Google sign-in. Fast, secure, and free.
            </p>
          </div>
        )}

        {/* Mobile OTP */}
        {tab === 'otp' && (
          <>
            {otpStep === 'phone' ? (
              <form onSubmit={handleSendOTP} className="auth-form">
                <div className="auth-form-group">
                  <label className="auth-label">Mobile Number</label>
                  <div className="auth-phone-input">
                    <span className="auth-phone-code">+91</span>
                    <input
                      type="tel"
                      className="auth-input phone-field"
                      placeholder="9876543210"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      maxLength={10}
                      required
                      autoFocus
                    />
                  </div>
                  <p className="auth-field-hint">We'll send a 6-digit OTP to this number</p>
                </div>
                <button type="submit" className="auth-submit-btn" disabled={loading || phone.length !== 10 || !role}>
                  {loading ? 'Sending...' : 'Send OTP'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOTP} className="auth-form">
                <div className="auth-otp-back">
                  <button type="button" className="auth-otp-back-btn" onClick={() => { setOtpStep('phone'); setOtp(''); }}>
                    <ArrowLeft size={16} /> +91 {phone}
                  </button>
                </div>
                <div className="auth-form-group">
                  <label className="auth-label">Enter OTP</label>
                  <input
                    type="text"
                    className="auth-input otp-input"
                    placeholder="000000"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    maxLength={6}
                    autoFocus
                    required
                  />
                  <div className="auth-otp-actions">
                    <button
                      type="button"
                      className="auth-resend-btn"
                      disabled={countdown > 0}
                      onClick={() => { setOtp(''); startCountdown(); }}
                    >
                      <RefreshCw size={14} />
                      {countdown > 0 ? `Resend in ${countdown}s` : 'Resend OTP'}
                    </button>
                  </div>
                </div>
                <button type="submit" className="auth-submit-btn" disabled={loading || otp.length < 6}>
                  {loading ? 'Verifying...' : 'Verify & Login'}
                </button>
              </form>
            )}
          </>
        )}

        <div className="auth-divider">
          <span>New to Prasang?</span>
        </div>

        <Link to="/signup" className="auth-switch-btn">Create an account</Link>

        <p className="auth-terms">
          By signing in, you agree to our{' '}
          <Link to="/terms" className="auth-terms-link">Terms of Service</Link> and{' '}
          <Link to="/privacy" className="auth-terms-link">Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.app.json`
Expected: exits with no output (success).

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev`
Open `http://localhost:5173/login`. Expected: a role picker identical in style to the signup page appears below the subtitle; both the Google button and OTP "Send OTP" button are disabled until a role is picked; picking "I'm Planning" then clicking "Continue with Google" navigates to `/planner/dashboard`; picking "I'm an Artist" instead navigates to `/artist/dashboard`. No console errors. Stop the dev server after checking.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat: add artist/buyer role picker to login, route by role"
```

---

### Task 8: Final integration check

**Files:** none (verification-only task)

- [ ] **Step 1: Full project build**

Run: `cd frontend && npm run build`
Expected: completes with no TypeScript errors and no Vite build errors (produces a `dist/` output).

- [ ] **Step 2: Full manual smoke test**

Run: `cd frontend && npm run dev`
Walk through: `/signup` → pick "I'm Planning" → Google login → lands on `/planner/dashboard` → click "View all" under Recent Inquiries → lands on `/planner/inquiries` with working filters → expand a card → click "View Profile" → lands on the correct `/profile/:slug` → back to `/planner/saved` via sidebar → grid renders → click a saved artist → correct profile loads. Then repeat via `/login` picking "I'm an Artist" to confirm the existing artist flow (`/artist/dashboard`) still works unchanged. No console errors at any step. Stop the dev server after checking.

- [ ] **Step 3: Final commit (if any cleanup was needed)**

Only if Steps 1–2 required fixes:

```bash
git add -A
git commit -m "fix: address issues found in planner dashboard integration check"
```

If no fixes were needed, skip this step — Task 7's commit is the last one.
