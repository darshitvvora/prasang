# Prasang frontend

React 19 + TypeScript + Vite. Talks to the API described in [`../contracts`](../contracts/README.md), served locally by the [Mockoon mock](../mockoon/README.md) until the FastAPI backend is running.

## Run locally (mock API)

```bash
npm install -g @mockoon/cli   # once
cd frontend
npm install
cp .env.example .env.local    # defaults: mock auth, proxy to Mockoon on :3001
npm run mock                  # terminal 1 — mock API on http://localhost:3001
npm run dev                   # terminal 2 — app on http://localhost:5173
```

Sign in with **Continue with Google** — in mock mode no Google popup opens:

| Where | Pick | You become |
|---|---|---|
| `/login` | I'm an Artist | Arjun Malhotra (Basic plan, 1 locked lead) |
| `/login` | I'm Planning | Neha Kulkarni (5 inquiries) |
| `/signup` | either | A brand-new user: profile step → onboarding (artist) or planner dashboard |

The new-user journey is stateful inside Mockoon; restart `npm run mock` (or `POST /api/v1/_mock/reset`) to start over.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server; `/api` is proxied to `VITE_API_PROXY_TARGET` |
| `npm run build` | Type-check (includes the contract example shape check) + production build |
| `npm test` | Vitest unit tests (API client, formatters, auth routing, forms, search URL, pricing) |
| `npm run lint` | oxlint |
| `npm run mock` | Build and start the Mockoon mock API |
| `npm run mock:smoke` | Curl every mock endpoint and the main journeys |

## Environment

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Absolute URL in production, e.g. `https://api.prasang.in/api/v1` |
| `VITE_API_PROXY_TARGET` | `http://localhost:3001` | Dev only: Mockoon (3001) or FastAPI (8000) |
| `VITE_AUTH_MODE` | `mock` | `supabase` once Google sign-in via Supabase is wired (backend plan) |

## Code map

| Path | Purpose |
|---|---|
| `src/api/types.ts` | Contract types — the single TS source of truth |
| `src/api/client.ts`, `endpoints.ts`, `queries.ts` | fetch wrapper (`ApiError` with contract `code`), one function per endpoint, TanStack Query hooks |
| `src/api/__contract__/` | Compile-time check that `contracts/examples/**` match the types |
| `src/auth/` | `AuthProvider` (session + `GET /me`), `RequireRole` guard, pure routing rules |
| `src/components/` | Shared UI incl. `ContactModal` (lead capture), `MediaUploader`, sidebars, `QueryState` |
| `src/payments/razorpay.ts` | Razorpay Checkout (mocked when key id is `rzp_test_mock`) |
