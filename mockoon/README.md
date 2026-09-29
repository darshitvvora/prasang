# Prasang mock API (Mockoon)

Serves the [API contract](../contracts/README.md) on `http://localhost:3001/api/v1` so the frontend runs end to end without the backend.

## Run

```bash
cd frontend
npm run mock        # builds mockoon/prasang.json and starts mockoon-cli on :3001
npm run mock:smoke  # in another terminal: curls every route, prints SMOKE PASS/FAIL
npm run dev         # Vite on :5173 proxies /api to :3001
```

Requires the Mockoon CLI (`npm i -g @mockoon/cli`). `prasang.json` can also be opened in the Mockoon desktop app, but edit `routes.mjs` / `data/` instead — the JSON is generated.

## Files

| File | Purpose |
|---|---|
| `data/*.json` | Datasets (12 artists, reviews, plans, locations, the mock artist's leads, the mock planner's inquiries). Each becomes a data bucket named after the file. |
| `routes.mjs` | Route table: status, body/template or `file:` (a `contracts/examples` path), and matching rules. The last response of a route is its default. |
| `build.mjs` | Assembles `prasang.json`; also derives `artistCards`, `artistDetails` (no contact numbers) and `artistContacts` buckets. |
| `smoke.sh` | Contract smoke test, including the stateful new-user journey. |

## Mock users

Send `Authorization: Bearer <token>`:

| Token | User |
|---|---|
| `mock-artist` | Arjun Malhotra, Basic plan, 16 leads this month (1 locked) |
| `mock-planner` | Neha Kulkarni, 5 inquiries |
| `mock-new` | Signed in, no profile. `POST /me`, then `POST /artists`, move it through onboarding; state lives in Mockoon global vars until `POST /_mock/reset` or restart. |

## Known mock simplifications

- `GET /search/artists` filters only `artistType`, `city`, `area`, `featuredOnly`, `verifiedOnly` (exact match); `q`, price, rating, language, event type and sort are accepted but ignored. `facets` are empty.
- `GET /artists/{slug}/similar` returns every artist of the same type, which can include the artist itself (the UI filters it out).
- Writes other than the new-user journey are not persisted (e.g. `PATCH /leads/{id}` echoes the change).
