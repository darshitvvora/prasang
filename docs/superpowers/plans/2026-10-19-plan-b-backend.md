# Plan B — Backend: Postgres, SuperTokens, Temporal, Elasticsearch, full local stack

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docker compose up` runs the entire Prasang app locally — React frontend on :5173 backed by a real FastAPI API that satisfies the Plan A contract, with SuperTokens auth (phone OTP works with zero accounts), self-hosted Temporal on Postgres, Elasticsearch search, S3 uploads (when a bucket is configured) and social embeds.

> **Revision 2026-10-19 (user):** no MinIO — storage is Amazon S3 (dev bucket via AWS credentials; tests use `moto`); deployment target is AWS; React Native apps will consume the same API, so sessions must support header-token mode.

**Architecture:** One Postgres server (dbs `prasang`, `prasang_test`, `supertokens`, `temporal`, `temporal_visibility`). FastAPI app in `backend/app` organised by domain module; writes go to Postgres plus an `outbox_events` row in the same transaction; a projector process indexes artists into Elasticsearch; a Temporal worker runs lead-notification, subscription and trial workflows. External services (payments, notifications, storage) sit behind small interfaces with local implementations (`fake`, `console`, MinIO).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, Pydantic v2 + pydantic-settings, supertokens-python 0.31.x, temporalio (Python SDK), elasticsearch[async] 8.x, aioboto3 (S3/MinIO), httpx, pytest + pytest-asyncio, uv; Docker images postgres:16, elasticsearch:8.19.23, temporalio/server + admin-tools 1.32.1, temporalio/ui 2.49.1, supertokens-postgresql 12.3.1, minio/minio; frontend supertokens-web-js.

**Spec:** [docs/superpowers/specs/2026-09-29-backend-mvp-design.md](../specs/2026-09-29-backend-mvp-design.md) (v2) · **Contract:** [contracts/README.md](../../../contracts/README.md), [frontend/src/api/types.ts](../../../frontend/src/api/types.ts)

## Global Constraints

- The contract is authoritative: JSON camelCase, error body `{"error":{"code","message","details"}}`, lists `{items,total,page,size}`, dates `YYYY-MM-DD`, timestamps ISO-8601 UTC `Z`, money integer rupees, phones 10-digit national.
- All API routes under `/api/v1`; SuperTokens routes under `/api/v1/auth`.
- Locally nothing requires a third-party account: `PAYMENT_GATEWAY=fake`, `NOTIFIER=console`, MinIO, OTP printed to API logs. Google sign-in only when `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are set.
- Temporal only for `LeadNotificationWorkflow`, `SubscriptionWorkflow`, `TrialWorkflow`. Do not use the deprecated `temporalio/auto-setup` image.
- Pin every Docker image tag (no `latest`).
- Dev auth shortcut (`Authorization: Bearer mock-artist|mock-planner|mock-new`) only when `ENV=local` and `DEV_AUTH_HEADER=true`; app refuses to start with it when `ENV=production`.
- Verification without browsers: pytest, `npx tsc -b`, `npm test`, curl, `mockoon/smoke.sh <api-url>`.
- Plain commit messages; no co-author / AI attribution lines.
- Host ports: web 5173, api 8000, postgres 5433 (avoid clashing with a local Postgres), ES 9200, Temporal 7233, Temporal UI 8080, SuperTokens 3567, MinIO 9000/9001.

## Review Focus

1. Two planners contacting the same capped artist at the same moment → exactly `lead_limit` unlocked leads, the rest locked (Task 9: concurrent-create test; service locks the artist row).
2. Elasticsearch down when an artist saves their profile → the save succeeds; search catches up when ES returns (Task 8: projector retry test with failing indexer).
3. Temporal unreachable when a planner submits a lead → lead saved and contact details returned (Task 10: API test with a client that raises).
4. Hostile or unsupported embed URLs (`javascript:`, `https://instagram.com.evil.com/p/x`, plain websites) → 422 `validation_error` on `details.fields.url`, never stored (Task 6: embeds tests).
5. Valid SuperTokens session whose user has no `users` row calling artist/planner endpoints → 404 `profile_required`, not 500 (Task 5: dependency test).

---

## File Structure

```
docker-compose.yml                     full local stack
docker/postgres/init.sql               create databases
docker/temporal/setup-schema.sh        temporal-sql-tool create + schema for temporal, temporal_visibility
docker/temporal/create-namespace.sh    wait for health, create `default` namespace
docker/temporal/dynamicconfig.yaml
docker/minio/init.sh                   create bucket `prasang-media`, anonymous download policy
backend/pyproject.toml, uv.lock, Dockerfile, .env.example, alembic.ini, alembic/env.py, alembic/versions/0001_initial.py
backend/app/main.py config.py db.py errors.py schemas.py embeds.py cli.py seed.py
backend/app/auth/{supertokens_setup.py,deps.py,router.py,models.py}
backend/app/contract/{me.py,artists.py,media.py,search.py,leads.py,subscriptions.py,common.py,locations.py}   Pydantic mirrors of types.ts
backend/app/artists/{models.py,service.py,router.py,slugs.py,completeness.py,stats.py}
backend/app/media/{models.py,storage.py,service.py,router.py}
backend/app/locations/{models.py,router.py}
backend/app/reviews/{models.py,router.py}
backend/app/leads/{models.py,service.py,router.py,usage.py}
backend/app/subscriptions/{models.py,plans.py,gateway.py,service.py,router.py}
backend/app/search/{es.py,mapping.py,documents.py,query.py,router.py}
backend/app/outbox/{models.py,emit.py,projector.py}
backend/app/notifications/{notifier.py,console.py,msg91.py,resend.py}
backend/app/workflows/{client.py,worker.py,activities.py,lead_notification.py,subscription.py,trial.py}
backend/tests/{conftest.py, contract/, unit/, api/, workflows/}
frontend/src/auth/supertokens.ts       web-js init + adapter used by AuthProvider
frontend/src/pages/AuthCallbackPage.tsx /auth/callback/google
frontend/Dockerfile.dev
mockoon/build.mjs                      deterministic UUIDs
```

---

### Task 1: Infrastructure stack (Postgres, Elasticsearch, Temporal, SuperTokens, MinIO)

**Files:** Create `docker-compose.yml` (infra services only in this task), `docker/postgres/init.sql`, `docker/temporal/*`, `docker/minio/init.sh`, `.env.example` (root, compose variables), `scripts/stack-health.sh`.

**Interfaces — Produces:** service names on network `prasang`: `postgres:5432` (user `prasang`/pw `prasang`), `elasticsearch:9200`, `temporal:7233` (namespace `default`), `supertokens:3567` (API key `local-supertokens-key`), `minio:9000` (root `minio`/`minio-secret`, bucket `prasang-media` public-read).

`docker/postgres/init.sql`:
```sql
CREATE DATABASE prasang;
CREATE DATABASE prasang_test;
CREATE DATABASE supertokens;
-- temporal + temporal_visibility are created by temporal-sql-tool (setup-schema.sh)
```

`docker/temporal/setup-schema.sh` (run in `temporalio/admin-tools`):
```sh
#!/bin/sh
set -eu
TOOL="temporal-sql-tool --plugin postgres12 --ep ${POSTGRES_SEEDS} -p ${DB_PORT:-5432} -u ${POSTGRES_USER} --pw ${POSTGRES_PWD}"
SCHEMA_DIR=/etc/temporal/schema/postgresql/v12
for db in temporal temporal_visibility; do
  dir=$([ "$db" = temporal ] && echo temporal || echo visibility)
  $TOOL --db "$db" create-database || true          # idempotent on restart
  $TOOL --db "$db" setup-schema -v 0.0 || true      # no-op if already set up
  $TOOL --db "$db" update-schema -d "$SCHEMA_DIR/$dir/versioned"
done
echo "temporal schema ready"
```

`docker/temporal/create-namespace.sh`:
```sh
#!/bin/sh
set -eu
for i in $(seq 1 60); do temporal operator cluster health --address "$TEMPORAL_ADDRESS" >/dev/null 2>&1 && break; sleep 2; done
temporal operator namespace describe -n default --address "$TEMPORAL_ADDRESS" >/dev/null 2>&1 \
  || temporal operator namespace create -n default --retention 72h --address "$TEMPORAL_ADDRESS"
echo "namespace default ready"
```

Compose (infra part) — key settings: postgres healthcheck `pg_isready -U prasang`; ES `discovery.type=single-node`, `xpack.security.enabled=false`, `ES_JAVA_OPTS=-Xms1g -Xmx1g`, healthcheck on `_cluster/health`; `temporal-schema` (admin-tools, depends postgres healthy, `restart: on-failure:5`); `temporal` (server, `DB=postgres12`, `POSTGRES_SEEDS=postgres`, `POSTGRES_USER=prasang`, `POSTGRES_PWD=prasang`, `DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development-sql.yaml`, depends schema completed, healthcheck `nc -z localhost 7233` or `temporal operator cluster health`); `temporal-namespace` (admin-tools one-shot); `temporal-ui` (`TEMPORAL_ADDRESS=temporal:7233`, port 8080); `supertokens` (`POSTGRESQL_CONNECTION_URI=postgresql://prasang:prasang@postgres:5432/supertokens`, `API_KEYS=local-supertokens-key`, healthcheck `curl -f localhost:3567/hello`); `minio` (`server /data --console-address :9001`) + `minio-init` (mc alias, mb, `mc anonymous set download`).

- [ ] **Step 1 (failing check):** write `scripts/stack-health.sh` asserting: `psql` lists the 5 databases; ES health is green/yellow; `temporal operator namespace describe -n default --address localhost:7233` succeeds (Temporal CLI is installed natively); `curl localhost:3567/hello` → `Hello`; `curl -I localhost:9000/prasang-media/` responds; Temporal UI `curl -s localhost:8080` 200. Run it → FAIL (nothing up).
- [ ] **Step 2:** `docker pull` each pinned image to verify tags exist (adjust patch version only if a tag is missing; ledger it); `docker run --rm temporalio/admin-tools:1.32.1 ls /etc/temporal/schema/postgresql/v12` to confirm the schema path.
- [ ] **Step 3:** write compose + scripts; `docker compose up -d` and wait for health.
- [ ] **Step 4:** `bash scripts/stack-health.sh` → all OK. `docker compose down && docker compose up -d` again → still OK (idempotent init).
- [ ] **Step 5:** commit `feat(infra): local stack - postgres, elasticsearch, temporal, supertokens, minio`.

### Task 2: Backend scaffold — config, DB, errors, health, test harness

**Files:** `backend/pyproject.toml`, `backend/app/{main.py,config.py,db.py,errors.py,schemas.py}`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/tests/conftest.py`, `backend/tests/api/test_health.py`, `backend/tests/unit/test_errors.py`, `backend/.env.example`.

**Interfaces — Produces:**
```python
# config.py
class Settings(BaseSettings):
    env: Literal['local','test','production'] = 'local'
    database_url: str            # postgresql+asyncpg://prasang:prasang@localhost:5433/prasang
    elasticsearch_url: str = 'http://localhost:9200'; es_index_prefix: str = ''
    temporal_address: str = 'localhost:7233'; temporal_namespace: str = 'default'; temporal_task_queue: str = 'prasang'
    supertokens_uri: str = 'http://localhost:3567'; supertokens_api_key: str = 'local-supertokens-key'
    api_domain: str = 'http://localhost:5173'; website_domain: str = 'http://localhost:5173'   # Vite proxy = same origin
    google_client_id: str | None = None; google_client_secret: str | None = None
    dev_auth_header: bool = False
    s3_endpoint: str = 'http://localhost:9000'; s3_public_endpoint: str = 'http://localhost:9000'
    s3_access_key: str = 'minio'; s3_secret_key: str = 'minio-secret'; s3_bucket: str = 'prasang-media'
    public_media_base_url: str = 'http://localhost:9000/prasang-media'
    payment_gateway: Literal['fake','razorpay'] = 'fake'; razorpay_key_id: str | None = None; razorpay_key_secret: str | None = None; razorpay_webhook_secret: str | None = None
    notifier: Literal['console','msg91'] = 'console'
    cors_origins: list[str] = ['http://localhost:5173']
    def validate_for_env(self) -> None   # raises if production + dev_auth_header
def get_settings() -> Settings          # lru_cache
# db.py
class Base(DeclarativeBase)
engine, SessionLocal (async_sessionmaker); async def get_session() -> AsyncIterator[AsyncSession]
# errors.py
class AppError(Exception): (status: int, code: str, message: str, details: dict | None = None)
def not_found(code, message) / conflict(...) / forbidden(...) / validation(fields: dict[str,str]) -> AppError
def install_error_handlers(app) # AppError → contract body; RequestValidationError → 422 validation_error with details.fields (camelCase loc); unhandled → 500 internal_error
# schemas.py
class CamelModel(BaseModel)       # alias_generator=to_camel, populate_by_name=True, from_attributes=True
class RequestModel(CamelModel)    # extra='forbid'
class Page[T](CamelModel): items: list[T]; total: int; page: int; size: int
# main.py
def create_app(settings: Settings | None = None) -> FastAPI   # /healthz, /readyz
```

Test harness: `conftest.py` sets `ENV=test`, `DATABASE_URL=...prasang_test`, `ES_INDEX_PREFIX=test_`; session-scoped fixture runs `alembic upgrade head` on `prasang_test`; function-scoped fixture truncates all app tables; `client` fixture = `httpx.AsyncClient(transport=ASGITransport(create_app()))`.

- [ ] **Step 1: failing tests** — `test_health.py`: `/healthz` → 200 `{"status":"ok"}`; `/readyz` → 200 with `{"postgres":"ok","elasticsearch":"ok","temporal":"ok"}` when stack is up. `test_errors.py`: `AppError(404,'artist_not_found','x')` raised in a route → body `{"error":{"code":"artist_not_found","message":"x","details":{}}}`; posting `{"fullName": 5}` to a route with `RequestModel` body → 422 with `details.fields.fullName`; unknown field → 422; production settings with `dev_auth_header=True` → `validate_for_env` raises.
- [ ] **Step 2:** `uv run pytest` → FAIL (no app).
- [ ] **Step 3:** implement; `uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic-settings httpx`; dev deps `pytest pytest-asyncio ruff`.
- [ ] **Step 4:** `uv run pytest` → PASS; `uv run ruff check` clean.
- [ ] **Step 5:** commit `feat(api): FastAPI scaffold, config, error contract, health checks`.

### Task 3: Pydantic contract models + contract tests (incl. social embed contract change)

**Files:** `backend/app/contract/*.py`, `backend/tests/contract/test_examples.py`; modify `frontend/src/api/types.ts` (MediaKind `facebook`, `Media.embedUrl`, `ArtistProfileInput.facebookUrl`, `ArtistCard.facebookUrl`, `AuthProvidersResponse`), `contracts/README.md` (embed rules, `GET /auth/providers`), `contracts/examples/**` (add fields), `mockoon/data/artists.json` + generator fields, `mockoon/routes.mjs` (`GET auth/providers`).

**Interfaces — Produces:** one Pydantic class per TS type with identical names (`Me`, `CreateMeRequest`, `ArtistCard`, `ArtistDetail`, `ArtistProfile`, `ArtistProfileInput`, `ArtistDashboard`, `PlanUsage`, `Media`, `MediaListResponse`, `UploadUrlRequest`, `UploadUrlResponse`, `CreateMediaUploadRequest`, `CreateMediaLinkRequest`, `SearchResponse`, `Suggestion`, `Review`, `LocationsResponse`, `CreateLeadRequest`, `CreateLeadResponse`, `ArtistLead`, `ArtistLeadsResponse`, `UpdateLeadRequest`, `PlannerInquiry`, `PlannerInquiriesResponse`, `Plan`, `MySubscriptionResponse`, `CreateSubscriptionRequest`, `CreateSubscriptionResponse`, `VerifyPaymentRequest`, `VerifyPaymentResponse`, `StartTrialRequest`, `AuthProvidersResponse`, `ErrorBody`). Responses use `extra='forbid'` in tests via `Model.model_validate(json, strict=False)` with a forbid config subclass.

Contract additions (TS):
```ts
export type MediaKind = 'image' | 'video' | 'youtube' | 'instagram' | 'facebook';
export interface Media { id: string; kind: MediaKind; url: string; embedUrl: string | null; thumbnailUrl: string | null; caption: string | null; displayOrder: number }
// ArtistCard gains: facebookUrl: string | null   (ArtistProfileInput too)
export type CreateMediaRequest = { kind: 'image' | 'video'; storageKey: string; caption?: string } | { kind: 'youtube' | 'instagram' | 'facebook'; url: string; caption?: string };
export interface AuthProvidersResponse { google: boolean; phoneOtp: boolean }
```

- [ ] **Step 1: failing test** `test_examples.py`: parametrised over a table `(example path, model)` covering every file in `contracts/examples` (responses and requests); each must validate with `extra='forbid'`; plus `test_every_example_is_covered` (glob count == table size).
- [ ] **Step 2:** run → FAIL (no models). Update TS types first → `npx tsc -b` FAIL on examples → update examples/datasets/mock → tsc PASS; mock smoke PASS.
- [ ] **Step 3:** write Pydantic models → pytest PASS.
- [ ] **Step 4:** commit `feat(contract): Pydantic contract models; facebook embeds and auth providers in contract`.

### Task 4: Database models, initial migration, seed data

**Files:** models in each domain module, `backend/alembic/versions/0001_initial.py` (autogenerate then review), `backend/app/seed.py`, `backend/app/cli.py` (`seed`, `migrate`), `backend/tests/unit/test_seed.py`.

**Interfaces — Produces:** ORM classes `User, Locality, ArtistProfile, ArtistDailyStat, ArtistMedia, Review, Lead, SubscriptionPlan, Subscription, PaymentEvent, OutboxEvent` with columns per spec §4. Enums as Postgres enums `artist_type`, `event_type`, `subscription_tier`, `lead_status`, `media_kind`, `user_role`, `tier_source`, `subscription_status`, `billing_cycle`, `lead_source`, `budget_range`.
`seed.py`: `async def seed(session, *, demo: bool)` — always: localities (from `contracts`/mock locations), plans (from `contracts/examples/subscriptions/plans.response.json`). `demo=True` (local): dev users `dev-artist-arjun` (role artist), `dev-planner-neha`, the 12 artists from `mockoon/data/artists.json` (owned by generated users; art-001 owned by `dev-artist-arjun`), their media, reviews, Arjun's leads from `mockoon/data/artist-leads.json` (timestamps shifted to the current month), Neha's inquiries as leads. Idempotent (upserts by natural keys).

- [ ] **Step 1: failing test** `test_seed.py`: after `seed(demo=True)` twice → 12 artists, 4 plans, Arjun has 7 leads with 1 locked, Neha has 5 leads; `alembic downgrade base && upgrade head` round-trips.
- [ ] **Step 2–4:** implement, migrate, PASS.
- [ ] **Step 5:** commit `feat(db): schema, migration and seed data`.

### Task 5: Auth — SuperTokens, current_user, /me, /auth/providers

**Files:** `backend/app/auth/*`, `backend/tests/api/test_me.py`, `backend/tests/unit/test_auth_deps.py`.

**Interfaces — Produces:**
```python
# supertokens_setup.py
def init_supertokens(settings: Settings, sms_sender: Callable[[str, str], Awaitable[None]]) -> None
    # recipes: session.init(cookie_same_site='lax', cookie_secure=settings.env=='production', cookie_domain from settings),
    #          passwordless (contact phone, flow USER_INPUT_CODE, SMS delivery override → sms_sender(phone, code)),
    #          thirdparty (google) only if google creds set
# deps.py
@dataclass class AuthIdentity: user_id: str; email: str | None; phone: str | None
async def current_identity(request) -> AuthIdentity          # verify_session(); or dev header when enabled
async def current_user(identity=Depends(current_identity), session=Depends(get_session)) -> User   # 404 profile_required if no row
def require_role(*roles: Role) -> Callable                    # 403 forbidden
DEV_TOKENS = {'mock-artist': 'dev-artist-arjun', 'mock-planner': 'dev-planner-neha', 'mock-new': 'dev-new-user'}
# router.py: GET/POST/PATCH /me, GET /auth/providers
```
Verify the passwordless/SMS-override API against the installed `supertokens_python` source before coding (`uv run python -c "import supertokens_python.recipe.passwordless as p, inspect; print(inspect.signature(p.init))"`; inspect `smsdelivery` service classes); ledger any deviation.

- [ ] **Step 1: failing tests** — `test_me.py`: no auth → 401 `unauthenticated`; `mock-new` → 404 `profile_required`; `POST /me {role:'artist', fullName:'Tanvi'}` → 201 Me with `artistSlug: null`; second POST → 409 `profile_exists`; `mock-planner` GET → Neha; PATCH fullName → updated; `GET /auth/providers` → `{google:false, phoneOtp:true}` without creds. `test_auth_deps.py` (Review Focus 5): identity with no users row hitting `require_role('artist')` route → 404 `profile_required`; planner hitting artist route → 403 `forbidden`; dev header ignored when `dev_auth_header=False` → 401.
- [ ] **Step 2:** FAIL. **Step 3:** implement (`uv add supertokens-python`). **Step 4:** PASS + manual: with compose SuperTokens up and API running, `curl -X POST localhost:8000/api/v1/auth/signinup/code -H 'rid: passwordless' -d '{"phoneNumber":"+919820011099"}'` → 200 and API log shows `OTP for +919820011099: ######`.
- [ ] **Step 5:** commit `feat(auth): SuperTokens (phone OTP, Google), current user and /me`.

### Task 6: Artists — profile CRUD, public profile, embeds, stats, dashboard

**Files:** `backend/app/embeds.py`, `backend/app/artists/*`, `backend/app/reviews/*`, `backend/app/locations/router.py`, `backend/app/outbox/{models.py,emit.py}`, tests `unit/test_embeds.py`, `unit/test_completeness.py`, `api/test_artists.py`, `api/test_public_artist.py`, `api/test_locations_reviews.py`.

**Interfaces — Produces:**
```python
# embeds.py
@dataclass(frozen=True) class Embed: kind: Literal['youtube','instagram','facebook']; url: str; embed_url: str
def parse_embed(url: str) -> Embed     # raises AppError 422 validation_error {fields:{url: msg}}
# outbox/emit.py
async def emit(session, aggregate_type: str, aggregate_id: str, event_type: str, payload: dict | None = None) -> None
# artists/service.py
async def create_profile(session, user: User, data: ArtistProfileInput) -> ArtistProfileModel
async def update_profile(session, user: User, changes: dict) -> ArtistProfileModel
async def get_own_profile(session, user) -> ArtistProfileModel        # 404 artist_profile_not_found
async def get_public(session, slug) -> ArtistProfileModel             # published only, else 404 artist_not_found
async def record_view(session, artist_id) / record_contact_click(session, artist_id)
async def dashboard(session, user, today: date) -> ArtistDashboard
def to_card(p) / to_detail(p) / to_profile(p) -> contract models
```
Embed rules exactly per spec §5.4. Accept only `https?` scheme and hosts in {`youtube.com`,`www.youtube.com`,`m.youtube.com`,`youtu.be`,`instagram.com`,`www.instagram.com`,`facebook.com`,`www.facebook.com`,`m.facebook.com`,`fb.watch`}.

- [ ] **Step 1: failing tests** — `test_embeds.py`: youtube watch/short/shorts → nocookie embed; instagram p/reel/tv → embed; facebook post/video/fb.watch → plugin URLs with urlencoded href; **Review Focus 4**: `javascript:alert(1)`, `https://instagram.com.evil.com/p/x`, `https://example.com/v`, `ftp://youtube.com/watch?v=x`, youtube without id → `AppError` 422 with `fields.url`. `test_completeness.py`: percent/items per spec. `test_artists.py`: create (201, slug derived, outbox row written), 409 second create, planner → 403, PATCH partial updates + outbox, validation (rateMax < rateMin → 422 `fields.perEventRateMax`; phone invalid → `fields.contactPhone`), facebookUrl must be facebook.com. `test_public_artist.py`: unpublished → 404; published → ArtistDetail without contact fields; view increments today's stat; contact-click 204 increments; dashboard metrics change% vs last month (null when last month 0). `test_locations_reviews.py`: locations from seed; reviews page.
- [ ] **Step 2–4:** implement, PASS.
- [ ] **Step 5:** commit `feat(api): artist profiles, public profile, social embeds, dashboard`.

### Task 7: Media — MinIO storage, presigned uploads, social links, quotas

**Files:** `backend/app/media/*`, tests `api/test_media.py` (against compose MinIO).

**Interfaces — Produces:**
```python
# storage.py
class Storage(Protocol):
    async def presign_put(self, key: str, content_type: str, expires_s: int = 300) -> str
    async def exists(self, key: str) -> bool
    def public_url(self, key: str) -> str
class S3Storage(Storage)   # aioboto3; presign with s3_public_endpoint so browsers can reach it
```
Keys: `artists/<artist_id>/<uuid>.<ext>`; avatar `artists/<artist_id>/avatar-<uuid>.<ext>`. Quotas from plan (`-1` unlimited) → 409 `media_quota_exceeded {limit, used}`. Size limits → 422 `fields.sizeBytes`.

- [ ] **Step 1: failing tests**: upload-url returns URL on public endpoint; PUT bytes with httpx to that URL → 200; confirm creates Media with `url=public_url`, `embedUrl=None`; confirm unknown key → 422 `fields.storageKey`; social link creates `embedUrl` via `parse_embed`; quota exceeded (free: 5 images) → 409; delete own → 204, other artist's id → 404; order reorders; avatar sets `profileImageUrl` + outbox.
- [ ] **Step 2–4:** implement (`uv add aioboto3`), PASS.
- [ ] **Step 5:** commit `feat(api): media uploads to S3/MinIO and social links`.

### Task 8: Search — Elasticsearch read model, projector, endpoints

**Files:** `backend/app/search/*`, `backend/app/outbox/projector.py`, `backend/app/cli.py` (`create-index`, `reindex`, `project` loop), tests `unit/test_query.py`, `api/test_search.py`, `unit/test_projector.py`.

**Interfaces — Produces:**
```python
# es.py: def get_es() -> AsyncElasticsearch; ALIAS = f"{prefix}artists"
# documents.py: def artist_document(p: ArtistProfileModel) -> dict   # card fields + suggest fields + boost
# query.py: def build_search(params: SearchQuery) -> dict; def build_similar(doc) -> dict; def build_suggest(q) -> dict
# projector.py
class Indexer(Protocol): async def upsert(self, doc_id: str, doc: dict) -> None; async def delete(self, doc_id: str) -> None
async def project_batch(session_factory, indexer: Indexer, batch_size: int = 100) -> int   # returns processed count
async def run_projector(poll_seconds: float = 1.0) -> None
async def reindex_all(session_factory, es) -> int    # new index + alias swap
```

- [ ] **Step 1: failing tests** — `test_query.py`: filters map to ES terms/range; price overlap uses `rate_min <= maxPrice` and `rate_max >= minPrice`; sorts; page/size → from/size, size capped at 50. `test_projector.py` (**Review Focus 2**): failing indexer → events keep `processed_at NULL`, `attempts=1`, `last_error` set; next batch with working indexer processes them; unpublished artist → delete. `test_search.py` (real ES, `test_` prefix): after seed + reindex: total 12; `artistType=dj` → 2; `city=Pune` → 2; `q=magic` finds magician; `featuredOnly`; `minRating=4.8`; `sort=price_low` order; facets counts; suggestions for `dj`; featured; similar excludes self; saving a profile then `project_batch` makes the change searchable.
- [ ] **Step 2–4:** implement (`uv add "elasticsearch[async]>=8.19,<9"`), PASS.
- [ ] **Step 5:** commit `feat(search): Elasticsearch read model with outbox projector`.

### Task 9: Leads — create with quota locking, artist & planner views, plan usage

**Files:** `backend/app/leads/*`, tests `unit/test_usage.py`, `api/test_leads.py`.

**Interfaces — Produces:**
```python
# usage.py
def plan_usage(profile, plan: SubscriptionPlan, leads_this_month: int, now: datetime) -> PlanUsage
def month_bounds_ist(now: datetime) -> tuple[datetime, datetime]
BUDGETS = {'5k_10k': (5000, 10000), '10k_15k': (10000, 15000), '15k_25k': (15000, 25000), '25k_50k': (25000, 50000), '50k_plus': (50000, None)}
# service.py
async def create_lead(session, planner: User, data: CreateLeadRequest, now) -> tuple[Lead, bool]   # (lead, created)
async def artist_leads(session, user, status, page, size) -> ArtistLeadsResponse
async def update_status(session, user, lead_id, status) -> ArtistLead      # transitions: new→contacted|converted|declined, contacted→converted|declined
async def planner_inquiries(session, user, status, page, size, today) -> PlannerInquiriesResponse
async def unlock_month(session, artist_id, now) -> int
```
Quota: `SELECT ... FROM artist_profiles WHERE id=:id FOR UPDATE` then count this month's leads → `is_locked = limit >= 0 and count >= limit`.

- [ ] **Step 1: failing tests** — usage: IST month boundary (2026-10-31T19:00Z is Nov 1 IST); unlimited → `leadsRemaining None`. leads API: 401 anonymous; artist → 403; unpublished/unknown artist → 404 `artist_not_found`; created 201 with contact; duplicate same date → 200 same `leadId`; 11th in a day → 429 `lead_rate_limited`; free artist 4th lead locked (masked in artist view, planner still gets contact); **Review Focus 1**: 6 concurrent creates (`asyncio.gather`, separate sessions) for a free artist with 0 leads → exactly 3 unlocked; status transitions incl. 409 `invalid_transition`; planner view maps statuses, `daysToEvent`, summary + upcoming; `expire-leads` CLI marks past `new` leads expired.
- [ ] **Step 2–4:** implement, PASS.
- [ ] **Step 5:** commit `feat(api): leads with quota locking, artist leads and planner inquiries`.

### Task 10: Temporal — worker, notifier, LeadNotificationWorkflow

**Files:** `backend/app/notifications/*`, `backend/app/workflows/{client.py,worker.py,activities.py,lead_notification.py}`, tests `workflows/test_lead_notification.py`, `api/test_leads_temporal.py`.

**Interfaces — Produces:**
```python
class Notifier(Protocol):
    async def send_sms(self, phone: str, text: str) -> None
    async def send_whatsapp(self, phone: str, text: str) -> None
    async def send_email(self, to: str, subject: str, text: str) -> None
def get_notifier(settings) -> Notifier          # ConsoleNotifier logs "SMS to …: …"
# client.py
async def get_temporal_client() -> Client       # cached
class WorkflowStarter(Protocol): async def start_lead_notification(self, lead_id: str) -> None
# lead_notification.py
@workflow.defn class LeadNotificationWorkflow: run(lead_id: str) -> dict  # activities: load_lead_context, send_email, send_whatsapp, send_sms
```
Retry policy: 3 attempts, initial 2 s, backoff 2; non-retryable `NotificationRejected`. Locked lead → message without planner details.

- [ ] **Step 1: failing tests** — workflow (time-skipping env, fake activities): sends email + WhatsApp for basic tier; free tier → email + SMS (no WhatsApp); WhatsApp failure → SMS fallback; locked lead text excludes planner phone. API (**Review Focus 3**): `WorkflowStarter` that raises → POST /leads still 201 with contact; starter called with lead id on success.
- [ ] **Step 2–4:** implement (`uv add temporalio`), PASS; with compose: create a lead via curl → workflow `lead-<id>` completes in Temporal UI / `temporal workflow describe -w lead-<id>`; worker logs console notifications.
- [ ] **Step 5:** commit `feat(workflows): Temporal worker and lead notification workflow`.

### Task 11: Subscriptions, trials, payment gateway, workflows

**Files:** `backend/app/subscriptions/*`, `backend/app/workflows/{subscription.py,trial.py}` (+ activities), tests `unit/test_gateway.py`, `workflows/test_subscription.py`, `workflows/test_trial.py`, `api/test_subscriptions.py`.

**Interfaces — Produces:**
```python
class PaymentGateway(Protocol):
    key_id: str
    async def create_subscription(self, plan_id: str, total_count: int, notes: dict) -> str     # gateway subscription id
    async def cancel_subscription(self, gateway_subscription_id: str, at_cycle_end: bool) -> None
    def verify_payment_signature(self, payment_id: str, subscription_id: str, signature: str) -> bool
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool
class FakeGateway(PaymentGateway)        # key_id 'rzp_test_mock', ids 'sub_mock…', accepts 'mock-signature'
class RazorpayGateway(PaymentGateway)    # httpx to api.razorpay.com/v1, HMAC-SHA256
# subscription.py: SubscriptionWorkflow(subscription_id) with @workflow.update get_checkout, signals activated/charged(period_end)/halted/cancelled
# trial.py: TrialWorkflow(artist_id, tier) sleeps 7 days → activity end_trial(artist_id)
```

- [ ] **Step 1: failing tests** — gateway HMAC: known vector (`hmac_sha256(secret, f"{payment_id}|{subscription_id}")`); fake accepts only `mock-signature`. Workflows (time-skipping): no activation in 24 h → cancel + `expired`; activation → `apply_tier` called; `charged` extends; `halted` → `downgrade_to_free`; no charge past period end + 3 days → downgrade; trial expires after 7 days → `end_trial`. API: plans 4 items matching contract example; trial once (second → 409 `trial_used`), PlanUsage `status:'trial'`; subscribe (fake) → checkout `keyId:'rzp_test_mock'`; verify → active, profile tier pro, boost, locked leads unlocked; retry subscribe while `created` cancels previous `created`; cancel → `cancelAtPeriodEnd:true`; webhook bad signature → 400 `invalid_signature`; duplicate webhook event id → 200 no-op.
- [ ] **Step 2–4:** implement, PASS.
- [ ] **Step 5:** commit `feat(subscriptions): plans, trials, fake/Razorpay gateway, subscription workflows`.

### Task 12: Frontend — SuperTokens auth mode, OTP, Google callback, embeds

**Files:** `frontend/src/auth/supertokens.ts`, modify `frontend/src/auth/AuthProvider.tsx`, `frontend/src/pages/AuthScreen.tsx`, create `frontend/src/pages/AuthCallbackPage.tsx`, modify `frontend/src/App.tsx`, `frontend/src/components/MediaUploader.tsx` (facebook links), `frontend/src/pages/ArtistProfilePage.tsx` (iframes), `frontend/src/pages/artist/OnboardingPage.tsx` + `profileForm.ts` (facebookUrl), `frontend/vite.config.ts` (no change needed: `/api` proxy covers `/api/v1/auth`), tests `src/auth/supertokens.test.ts`, `src/pages/artist/profileForm.test.ts` (facebook), `src/components/embed.test.ts`.

**Interfaces — Produces:**
```ts
// supertokens.ts
export function initSupertokens(): void                       // SuperTokens.init({appInfo:{appName:'Prasang', apiDomain: window.location.origin, apiBasePath:'/api/v1/auth'}, recipeList:[Session.init(), Passwordless.init(), ThirdParty.init()]})
export async function hasSession(): Promise<boolean>
export async function sendOtp(phone10: string): Promise<void>                 // createCode({phoneNumber:'+91'+phone10}); maps SIGN_IN_UP_NOT_ALLOWED → ApiError
export async function verifyOtp(code: string): Promise<'ok'|'incorrect'|'expired'|'restart'>
export async function resendOtp(): Promise<void>
export async function startGoogle(): Promise<void>                           // redirect to auth URL (frontendRedirectURI = origin + '/auth/callback/google')
export async function finishGoogle(): Promise<'ok'|'no_email'|'not_allowed'>
export async function endSession(): Promise<void>
```
AuthProvider in supertokens mode: `hasToken` = session exists (checked on mount and after sign-in); `signInWithGoogle` → `startGoogle()` (page navigates away; role chosen is kept in `sessionStorage['prasang.intendedRole']` for the profile step); new `signInWithOtp(phone, code)` path via AuthScreen OTP tab (send → verify → `/me`); `signOut` → `endSession()` + clear cache. `useAuthProviders()` query on `/auth/providers` disables the Google button with "Google sign-in isn't configured yet" when false. Profile page: social media items render `<iframe src={embedUrl} sandbox="allow-scripts allow-same-origin allow-popups allow-presentation" allow="encrypted-media; picture-in-picture; fullscreen" loading="lazy">`.

- [ ] **Step 1: failing tests** — `supertokens.test.ts` with `vi.mock('supertokens-web-js/recipe/passwordless')`: `sendOtp('9820011001')` calls createCode with `+919820011001`; `verifyOtp` maps statuses; `profileForm` facebookUrl round-trip + validation (must be facebook.com); `embed.test.ts`: `mediaIsEmbed(m)` true for youtube/instagram/facebook with embedUrl.
- [ ] **Step 2–4:** implement (`npm i supertokens-web-js`), `npm test && npm run build` PASS.
- [ ] **Step 5:** commit `feat(frontend): SuperTokens auth (phone OTP, Google) and social embeds`.

### Task 13: Full stack in compose, end-to-end smoke, runbook

**Files:** `backend/Dockerfile`, `frontend/Dockerfile.dev`, `docker-compose.yml` (+ `migrate`, `api`, `worker`, `projector`, `web` services), `mockoon/build.mjs` (deterministic UUIDs: `uuidv5`-style from route method+path+index), `mockoon/smoke.sh` (base-url arg already supported; add expectations tolerant of real data), root `README.md` runbook, `docs/backlog.md` update.

Services: `migrate` (one-shot: `alembic upgrade head && python -m app.cli seed --demo && python -m app.cli reindex`), `api` (`uvicorn app.main:app --host 0.0.0.0 --reload`, volume-mount `backend/app`, `ENV=local`, `DEV_AUTH_HEADER=true`), `worker` (`python -m app.workflows.worker`), `projector` (`python -m app.cli project`), `web` (node:22 image, `npm ci && npm run dev -- --host`, `VITE_AUTH_MODE=supertokens`, `VITE_API_PROXY_TARGET=http://api:8000`).

- [ ] **Step 1 (failing check):** `bash mockoon/smoke.sh http://localhost:8000/api/v1` → FAIL (api not in compose).
- [ ] **Step 2:** write Dockerfiles + compose services; `docker compose up -d --build`; wait for `migrate` to complete.
- [ ] **Step 3:** `bash scripts/stack-health.sh` OK; `bash mockoon/smoke.sh http://localhost:8000/api/v1` → SMOKE PASS (adjust only expectations that depend on mock-only data, e.g. totals that change after seeded writes — ledger each); OTP journey via curl against `/api/v1/auth/signinup/code` + `/code/consume` using the OTP from `docker compose logs api` → session cookies → `GET /api/v1/me` 404 `profile_required` → `POST /me` 201; `curl localhost:5173` → 200 HTML; `curl localhost:5173/api/v1/locations` → 200 (proxy through web container).
- [ ] **Step 4:** README runbook (one command up, URLs, OTP-from-logs, Temporal UI, MinIO console, how to enable Google/Razorpay/MSG91, reset `docker compose down -v`).
- [ ] **Step 5:** commit `feat: whole application runs with docker compose`.

---

## Self-review notes
- Spec coverage: §1 decisions → Tasks 1, 5, 10, 11, 7; §2 architecture → 1, 13; §4 data model → 4; §5.1 auth → 5, 12; §5.2 → 6, 8; §5.3 → 8; §5.4 embeds → 3, 6, 7, 12; §5.5 → 9, 10; §5.6 → 11; §5.7 → 7; §6 errors/CORS/readiness → 2, 5; §7 testing → every task + 3 (contract) + 13 (smoke); §8 deployment → **not in this plan** (next plan: production compose, Caddy, CI/CD on Oracle) — the user asked to get the whole app running locally first.
- Review Focus items each have a named test in their owning task (Tasks 9, 8, 10, 6, 5).
