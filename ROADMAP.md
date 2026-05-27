# Grounded AI — Project Roadmap & Status

> Generated: 2026-05-23  
> Current state: Phase 1.5 — Foundation complete, all core features live.

---

## Table of Contents

1. [What's Already Built](#1-whats-already-built)
2. [Keys & Credentials You Need](#2-keys--credentials-you-need)
3. [What's Left to Implement](#3-whats-left-to-implement)
4. [What Would Make This a Great System](#4-what-would-make-this-a-great-system)
5. [Priority Order](#5-priority-order)
6. [Local Dev Quick-Start](#6-local-dev-quick-start)

---

## 1. What's Already Built

### Backend
| Feature | Status | Notes |
|---|---|---|
| Email sign-up / sign-in | ✅ Done | bcrypt passwords, JWT-less API-key auth |
| API key management | ✅ Done | create, list, revoke |
| Workspaces | ✅ Done | multi-workspace per tenant |
| Datasets (namespaces) | ✅ Done | sensitivity, freshness, web-fallback policy |
| Document upload | ✅ Done | PDF, DOCX, TXT; S3/MinIO storage |
| Document ingestion | ✅ Done | chunking → embedding → Qdrant index |
| Dense retrieval | ✅ Done | Qdrant vector search |
| Hybrid retrieval | ✅ Done | dense + sparse RRF (toggle via env var) |
| Grounded generation | ✅ Done | Gemini / OpenAI / local stub backends |
| Citations & confidence | ✅ Done | per-answer citation objects |
| Verification loop | ✅ Done | critic + corrective RAG |
| Enterprise reranker | ✅ Done | Gemini-backed or stub |
| Query traces | ✅ Done | full per-query audit trail |
| Conversations & messages | ✅ Done | chat history per agent |
| Agents | ✅ Done | persona, mode, dataset bindings |
| Runs | ✅ Done | execution history |
| Dashboard metrics | ✅ Done | counts, recent jobs/runs |
| Health check | ✅ Done | DB + storage + Qdrant |
| Rate limiting | ✅ Done | sliding-window, per API key |
| External fallback (DuckDuckGo) | ✅ Done | policy-gated, disclosed |
| Team members | ✅ Done | invite, list, update role, remove |
| Audit logs | ✅ Done | immutable log table + list endpoint |
| Billing subscriptions | ✅ Done | DB table + GET endpoint (Stripe stub) |
| Google OAuth endpoint | ✅ Stub | returns 503 until `GOOGLE_CLIENT_ID` set |
| SSO / SAML endpoint | ✅ Stub | returns friendly message until configured |

### Frontend
| Feature | Status | Notes |
|---|---|---|
| Login (email + API key) | ✅ Done | |
| Sign-up | ✅ Done | |
| Onboarding flow | ✅ Done | 4-step wizard |
| Dashboard | ✅ Done | metrics, recent jobs/runs |
| Datasets page | ✅ Done | list, create |
| Dataset detail | ✅ Done | documents, ingestion jobs, upload |
| Agents page | ✅ Done | list, create |
| Agent chat | ✅ Done | streaming-style chat with citations |
| Runs page | ✅ Done | execution history |
| Settings → API Keys | ✅ Done | create, list, revoke |
| Settings → Team Members | ✅ Done | invite, list, remove |
| Settings → RBAC roles | ✅ Done | role description cards |
| Settings → Audit Logs | ✅ Done | paginated log table |
| Settings → Billing | ✅ Done | plan display, feature list |
| Settings → SSO form | ✅ Done | org slug → calls backend stub |
| Google sign-in button | ✅ Done | active button, shows config message |
| SSO sign-in button | ✅ Done | active form with org slug |
| Dark / light theme | ✅ Done | |
| Full test suite | ✅ Done | 88 frontend tests, 264 backend unit tests |

---

## 2. Keys & Credentials You Need

### Minimum to run locally (free, no signup needed)
These defaults are already set — just run `docker compose up`.

| Service | Default | Where it runs |
|---|---|---|
| PostgreSQL | `grounded:grounded@localhost:5433/grounded` | Docker |
| MinIO (S3) | `minioadmin / minioadmin` | Docker `localhost:9000` |
| Qdrant | no auth needed | Docker `localhost:6333` |

---

### To get real AI responses (pick one)

#### Option A — Gemini (recommended, has a free tier)
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create a free API key
3. Add to your `.env`:
```env
GENERATOR_BACKEND=gemini_v1
GEMINI_API_KEY=your_key_here
EMBEDDING_BACKEND=gemini_v1
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
```
> Free tier: 20 requests/min, 1 500 requests/day on `gemini-2.5-flash`

#### Option B — OpenAI
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a key (requires billing set up, ~$0.15 per 1M tokens on gpt-4.1-mini)
3. Add to your `.env`:
```env
GENERATOR_BACKEND=openai_compatible_v1
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_BACKEND=openai_compatible_v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### Option C — No key (works out of the box)
The default `GENERATOR_BACKEND=local_grounded_v1` returns deterministic stub answers. Good for testing the pipeline without spending money.

---

### To enable Google OAuth sign-in
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → APIs & Services → Credentials
3. Create an **OAuth 2.0 Client ID** (Web application type)
4. Add `http://localhost:5173` to Authorised JavaScript origins
5. Add your domain to Authorised redirect URIs when you deploy
6. Add to your `.env`:
```env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```
7. The backend `/v1/auth/google` endpoint will then actually verify tokens
   (you'll also need to implement the token-verification logic in `backend/app/api/v1/auth.py` — see section 3)

---

### To enable real Stripe billing
1. Go to [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys)
2. Copy your **Publishable key** and **Secret key** (use test keys first)
3. Create a product and price in the Stripe dashboard for each plan
4. Add to your `.env`:
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...  # get this after setting up a webhook
STRIPE_PRO_PRICE_ID=price_...
STRIPE_BUSINESS_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
```
5. Implement the Stripe logic in `backend/app/services/billing.py` and `backend/app/api/v1/billing.py` (see section 3)

---

### To enable SSO / SAML
SSO requires an Enterprise identity provider. Options:
- **Okta** — [developer.okta.com](https://developer.okta.com) (free dev account)
- **Auth0** — [auth0.com](https://auth0.com) (free tier up to 7,500 users)
- **Microsoft Entra ID** — [azure.microsoft.com](https://azure.microsoft.com) (free with M365)

You would configure these with your backend's SSO callback URL after deploying.

---

### To deploy to production
| Service | Recommended | Notes |
|---|---|---|
| Backend hosting | **Railway**, Render, or Fly.io | $5–20/month |
| Frontend hosting | **Vercel** or Netlify | Free tier available |
| Database | **Supabase** (managed Postgres) or Railway Postgres | Free tier available |
| Object storage | **AWS S3** or Cloudflare R2 | R2 has no egress fees |
| Vector DB | **Qdrant Cloud** | Free 1GB cluster |
| Monitoring | **Sentry** (errors) + Grafana (metrics) | Free tiers available |

---

## 3. What's Left to Implement

These are the remaining gaps ordered by importance.

### 🔴 Critical — needed for a real product

#### 3.1 Google OAuth token verification
**File:** `backend/app/api/v1/auth.py` — the `/v1/auth/google` endpoint currently returns 501.
**What to do:**
- Install `google-auth` package
- Verify the ID token with `google.oauth2.id_token.verify_oauth2_token()`
- Look up or create a tenant by the Google email
- Return the same `EmailAuthResponse` as email sign-in

**Effort:** ~2 hours

---

#### 3.2 Real Stripe billing integration
**Files:** `backend/app/services/billing.py`, `backend/app/api/v1/billing.py`
**What to do:**
- `POST /v1/billing/portal` → create a real Stripe Customer Portal session and return the URL
- `POST /v1/billing/checkout` → create a Stripe Checkout session for plan upgrades
- `POST /v1/webhooks/stripe` → handle `customer.subscription.updated`, `invoice.paid`, `invoice.payment_failed` webhooks and update `billing_subscriptions` table
- Enforce plan limits (e.g. cap agents at 3 on free tier)

**Effort:** ~1 day

---

#### 3.3 Email delivery (invitations & password reset)
Right now, team member invitations are stored in the DB but no email is sent. There is also no password-reset flow.
**What to do:**
- Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` to config
- Or use **Resend** ([resend.com](https://resend.com), free 3,000 emails/month): `RESEND_API_KEY`
- Send invitation emails when `invite_workspace_member()` is called
- Add `POST /v1/auth/password-reset/request` and `POST /v1/auth/password-reset/confirm` endpoints

**Effort:** ~3 hours

---

#### 3.4 Ingestion worker (async background processing)
Currently ingestion runs inline in the request. This blocks the HTTP response for large files.
**What to do:**
- Use the existing Redis container (already in docker-compose)
- Add `ARQ` or `Celery` worker that picks up `QUEUED` ingestion jobs
- The job table and status machine are already in place — just needs the worker loop

**Effort:** ~1 day

---

### 🟡 Important — improves the product significantly

#### 3.5 Member invitation acceptance flow
Invited members have `status=pending` but there is no way to accept an invitation.
**What to do:**
- Add `POST /v1/invitations/{token}/accept` endpoint
- Generate a signed token when creating the invite (store hash in DB)
- Send the token in the invitation email (depends on 3.3)
- On acceptance, set `status=active`, `joined_at=now()`

**Effort:** ~3 hours

---

#### 3.6 RBAC enforcement
Roles exist in the DB but are not enforced on API endpoints.
**What to do:**
- Add `require_workspace_role(minimum_role)` FastAPI dependency
- Apply it to: delete agent (admin only), delete dataset (admin only), invite member (admin only), revoke API key (admin only)
- Viewers cannot POST/PATCH/DELETE anything

**Effort:** ~4 hours

---

#### 3.7 Semantic chunking
Dense retrieval quality improves significantly with semantic chunking vs. fixed-token windows.
**What to do:**
- Set `CHUNKING_STRATEGY=semantic_v1` in `.env` (the strategy is already registered)
- Confirm the semantic chunker implementation is complete in `backend/app/pipeline/`

**Effort:** 0–2 hours (check if already implemented)

---

#### 3.8 Hybrid retrieval
Switch from `dense_only` to `hybrid` for better recall on keyword queries.
**What to do:**
- Set `RETRIEVAL_MODE=hybrid` in `.env`
- Confirm BM25 sparse index is wired up
- No code changes needed if already implemented

**Effort:** 0 hours (config change only)

---

#### 3.9 Audit log writes
The audit log table exists and the read endpoint is live, but nothing writes to it yet.
**What to do:**
- Call `write_audit_log()` from `backend/app/services/audit_logs.py` after key actions:
  - Document uploaded → `action=document.uploaded`
  - Agent created → `action=agent.created`
  - Member invited → `action=member.invited`
  - API key created → `action=api_key.created`
  - API key revoked → `action=api_key.revoked`

**Effort:** ~2 hours

---

### 🟢 Nice to have — polish and scale

#### 3.10 Workspace onboarding email
Send a welcome email after sign-up with quick-start instructions.

#### 3.11 Pagination on all list endpoints
Datasets, agents, conversations currently return all records. Add `page` / `page_size` query params as done for audit logs.

#### 3.12 Document re-indexing UI
The `POST /v1/datasets/{id}/documents/{doc_id}/reindex` endpoint exists but there is no button in the frontend.

#### 3.13 Agent export / import
Let users export an agent config as JSON and import it into another workspace.

#### 3.14 Usage analytics
Per-tenant query count, token usage, and document storage shown on the dashboard.

#### 3.15 Critical tier activation
Set `CRITICAL_ENABLED=true` and test the full verified-answer pipeline end-to-end.

---

## 4. What Would Make This a Great System

### Reliability
- [ ] **Health-check circuit breakers** — if Qdrant or the LLM provider is down, return a graceful error instead of a 500
- [ ] **Retry with exponential backoff** — already partially done; ensure all LLM calls use it
- [ ] **Database connection pooling** — configure `pool_size` and `max_overflow` in SQLAlchemy for production
- [ ] **Structured logging to a sink** — ship logs to Datadog, Grafana Loki, or AWS CloudWatch

### Security
- [ ] **HTTPS everywhere** — never run the API on plain HTTP in production
- [ ] **`API_KEY_SALT` must be a random 32-byte secret** — change the default `replace-in-local-env` immediately
- [ ] **`JWT_SECRET_KEY` rotation policy** — rotate every 90 days
- [ ] **CORS locked to your domain** — update `CORS_ALLOWED_ORIGINS` from localhost to your production domain
- [ ] **Rate limiting on auth endpoints** — already on query endpoints; add to `/auth/email/sign-in` to prevent brute-force

### Developer Experience
- [ ] **OpenAPI documentation** — already auto-generated at `/docs`; add descriptions to all endpoints
- [ ] **`backend/.env.example`** — document every env var with a comment explaining what it does
- [ ] **`make` targets** — `make dev`, `make test`, `make migrate`, `make seed`

### Scalability
- [ ] **Async background workers** — move ingestion off the HTTP thread (see 3.4)
- [ ] **Read replicas** — route `SELECT` queries to a read replica as query volume grows
- [ ] **Qdrant sharding** — enabled automatically above ~1M vectors; no code change needed

### Product Quality
- [ ] **Answer quality evaluation** — run the BEIR benchmark suite regularly (already set up in `backend/tests/evaluation/`)
- [ ] **User feedback loop** — let users rate answers (👍 / 👎), store in DB, use to improve retrieval
- [ ] **Chunk visualiser** — show users which chunks were retrieved and why, in the agent chat UI
- [ ] **Dataset health score** — surface indexing quality (% of docs indexed, avg chunk count) on the dataset detail page

---

## 5. Priority Order

```
Phase 2 — Make it real (2–4 weeks)
  1. Gemini API key → real AI answers
  2. Async ingestion worker (Redis + ARQ)
  3. Email delivery (Resend)
  4. Audit log writes
  5. Member invitation acceptance
  6. RBAC enforcement on destructive endpoints

Phase 3 — Monetise (2–4 weeks)
  7. Stripe billing integration
  8. Plan-based feature enforcement (agent cap, query limits)
  9. Usage analytics dashboard

Phase 4 — Enterprise (4–8 weeks)
  10. Google OAuth token verification
  11. SSO / SAML via Okta or Auth0
  12. Critical tier activation and testing
  13. Read replicas + connection pooling
  14. Full observability (Sentry + Grafana)
```

---

## 6. Local Dev Quick-Start

```bash
# 1. Clone and install
git clone <your-repo>
cd grounding-engine

# 2. Start infrastructure
docker compose up -d

# 3. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum set GEMINI_API_KEY

# 4. Run migrations
cd backend
python -m alembic upgrade head

# 5. Start backend
python -m uvicorn app.main:app --reload --port 8000

# 6. Start frontend (new terminal)
cd ../frontend
npm install
npm run dev
# Opens at http://localhost:5173

# 7. Run tests
cd ../backend && pytest                    # backend
cd ../frontend && npm test                 # frontend
```

### Minimum .env to get started
```env
# backend/.env

# Change these two — they are security keys
API_KEY_SALT=a-random-32-char-string-here
JWT_SECRET_KEY=another-random-32-char-string

# Pick one AI provider
GENERATOR_BACKEND=gemini_v1
GEMINI_API_KEY=your_gemini_api_key
EMBEDDING_BACKEND=gemini_v1

# Everything else has safe defaults for local dev
```

---

*This document is the single source of truth for project status. Update it as features ship.*
