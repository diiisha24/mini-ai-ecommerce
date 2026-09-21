# Mini AI E-Commerce Application

A small e-commerce app with Google Sign-In, customer/admin roles, Stripe checkout, and an
AI support agent that answers questions using real product/order data — built for the
"AI Full Stack Developer" technical assignment (Assignment 2).

Full flow: **UI → API → Database → Authentication → Business Logic → AI → Integration**

- [System design (one-pager)](docs/system-design.md)
- [Database schema](docs/db-schema.md)
- [API reference](docs/api.md)

## Tech stack

- **Frontend**: React + TypeScript, Tailwind CSS v4, shadcn/ui, React Router, `@react-oauth/google`
- **Backend**: Python, FastAPI, SQLModel (SQLAlchemy + Pydantic), PostgreSQL
- **Auth**: Google OAuth (identity) → backend-issued JWT (session)
- **Payments**: Stripe Checkout (test mode) + webhook
- **AI agent**: LangGraph `create_react_agent` + Google Gemini (`langchain-google-genai`), with tools
  that query the real database, scoped to the authenticated user

## Scope notes (read this first)

- **Cart is client-side** (`localStorage`), submitted as a whole at checkout — there's no persisted
  server-side cart table. See `docs/db-schema.md` for the reasoning.
- **No Alembic migrations** — tables are created via `SQLModel.metadata.create_all()` on startup.
  Fine for this exercise's scope; a production version would add migrations before the first
  schema change.
- **Admin accounts** aren't self-service. Add an email to `ADMIN_EMAILS` in the backend `.env`
  *before* that person's first Google sign-in — the role is assigned at account-creation time.
- **Not deployed live** for this submission (see "Deployment" below) — built and documented to run
  locally via Docker Compose; `docs/system-design.md` covers the intended AWS deployment and how
  the app would scale.

## Prerequisites

- Docker + Docker Compose (for Postgres + backend)
- Node.js 20+ (for the frontend)
- Accounts for the three integrations below (all free — see "Getting API keys")

## Getting API keys (all free, no credit card required)

| Key | Where to get it |
|---|---|
| `GOOGLE_CLIENT_ID` | [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → **Create OAuth client ID** (type: Web application). Add `http://localhost:5173` under "Authorized JavaScript origins". |
| `STRIPE_SECRET_KEY` | [Stripe Dashboard](https://dashboard.stripe.com/) → Developers → API keys → use the **test mode** secret key (`sk_test_...`). |
| `STRIPE_WEBHOOK_SECRET` | Either the Stripe Dashboard webhook endpoint's signing secret, or run the Stripe CLI locally: `stripe listen --forward-to localhost:8000/api/webhooks/stripe` (prints a `whsec_...` for that session). |
| `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) → **Create API key** (Gemini free tier). |

## Setup

### 1. Backend + database (Docker Compose)

```bash
cd backend
cp .env.example .env
# edit .env: fill in GOOGLE_CLIENT_ID, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, GOOGLE_API_KEY,
# ADMIN_EMAILS (your own Google account email, so you get the admin role on first login), and
# generate a random JWT_SECRET.
cd ..
docker compose up -d --build
docker compose exec backend python -m app.seed   # adds 5 sample products
```

The API is now at `http://localhost:8000` (`/docs` for interactive Swagger UI).

### 2. Frontend

```bash
cd frontend
cp .env.example .env
# edit .env: VITE_GOOGLE_CLIENT_ID must match the backend's GOOGLE_CLIENT_ID
npm install
npm run dev
```

The app is now at `http://localhost:5173`.

### 3. Stripe webhook (local dev)

Stripe needs to reach your webhook endpoint. Easiest local option — the [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

Copy the `whsec_...` it prints into `backend/.env` as `STRIPE_WEBHOOK_SECRET`, then restart the
backend container (`docker compose restart backend`).

### 4. Becoming an admin

Add your Google account's email to `ADMIN_EMAILS` in `backend/.env` **before** signing in with it
for the first time (the role is set once, at account creation). Sign in via the frontend's
Google button, and you'll see an "Admin" link in the nav bar for product/order management.

## Running the backend tests

```bash
cd backend
.venv/Scripts/pip install -r requirements-dev.txt   # or: pip install -r requirements-dev.txt
python -m pytest tests -v
```

The suite (`backend/tests/`) uses an in-memory SQLite database and monkeypatches Stripe/Google
calls, so it needs no external services or credentials. It covers RBAC (401/403 on every
protected and admin route), order ownership isolation, the Google-login/admin-allow-list flow,
and the checkout/webhook state machine: stock reservation, insufficient-stock rejection,
rollback on a Stripe failure, payment confirmation, idempotency against Stripe's webhook
retries, and stock restoration on an expired/failed session.

## Known limitations

Called out explicitly rather than left for a reviewer to discover:

- **The AI chat endpoint has no conversation memory** — each message is a fresh call to the
  agent with no prior turns, so multi-turn follow-ups ("what about its stock?" after asking
  about a product) won't resolve the pronoun. Adding memory would mean threading a
  conversation/session id through `ChatRequest` and either replaying prior turns or using
  LangGraph's checkpointing — straightforward, but a deliberate scope cut here.
- **No rate limiting on `/api/ai/chat`** — an authenticated user can call it in a tight loop
  and drive up Gemini API cost. Fine for a demo; would need a per-user limiter before real
  traffic.
- **Session JWTs live in `localStorage` for up to 7 days with no server-side revocation** —
  acceptable for this exercise, but there's no way to force-invalidate a token (e.g. on
  logout-everywhere or a compromised device) short of rotating `JWT_SECRET` for everyone.
- **Admin order management is read-only** — admins can see all orders but there's no manual
  status override/refund action for a case where a webhook is missed entirely (rare, but
  possible if Stripe and the backend are both unreachable for the full retry window).
- **`GET /api/health` checks DB connectivity but nothing else** — no check on Stripe/Gemini
  reachability.

## AI development tools used

The chat endpoint (`POST /api/ai/chat`) calls Gemini directly — no extra setup beyond
`GOOGLE_API_KEY` being present in `backend/.env`. Ask it things like:

- "What products are available?"
- "What's the price of the mechanical keyboard?"
- "What's the status of order 3?" (only works for your own orders)

## Business logic & security highlights

- **RBAC is enforced server-side**, not just hidden in the UI — every admin route has a
  `require_admin` dependency, and `GET /api/orders/{id}` checks `order.user_id == current_user.id`
  (unless the caller is an admin) before returning anything.
- **Stock is reserved at checkout, not at payment confirmation**, and restored automatically if the
  Stripe session expires or payment fails — see `app/routers/orders.py` and
  `app/routers/webhooks.py`.
- **Order totals are computed server-side** from the database's current product prices — the
  frontend never sends a price the backend trusts.
- **The AI agent can't leak other customers' data**: its tools are built per-request, closed over
  the authenticated user's session, so `get_order_status` can only ever resolve orders owned by
  the caller.

## AI development tools used

- **Claude Code** — used to scaffold and implement the full backend (FastAPI routers, SQLModel
  schema, JWT/RBAC, Stripe integration, LangGraph AI agent) and frontend (React/TS pages,
  shadcn/ui components, contexts), plus this documentation and the `backend/tests/` suite.
- **Smoke-tested against a real, containerized Postgres instance** (not mocked) before and after
  the review pass below: health check, RBAC 401/403 on every protected route, stock
  reservation/rollback on a simulated Stripe failure, order-ownership isolation between two
  customers, and admin-vs-customer order visibility — all via manually-minted JWTs (bypassing
  Google, since no real OAuth credentials were available in the build environment).
- **Reviewed by three independent Claude Code subagents**, each briefed with a different lens
  and pointed at the actual source (not a description of it): a PM checking requirement/deliverable
  coverage against the assignment brief, a QA reviewer hunting for concurrency bugs and unhandled
  edge cases, and a senior engineer reviewing security/correctness/code quality. Real findings that
  came out of that pass and were fixed as a result: a stock-oversell race condition under concurrent
  checkouts (fixed with row-level locking - `SELECT ... FOR UPDATE`), a non-atomic checkout
  transaction, an N+1 query on order listings, an unmaintained JWT library (`python-jose` → `pyjwt`),
  a 24-hour stock-reservation window on abandoned checkouts (cut to 30 minutes), a missing
  "list all my orders" tool on the AI agent, no global 401/session-expiry handling on the frontend,
  a stale-cart-price bug (cart now re-syncs against live product data), silently swallowed frontend
  API errors, and the admin allow-list only applying at first registration instead of on every
  login. The zero-test-coverage gap that review also surfaced is what `backend/tests/` addresses.
- Real end-to-end testing of Google Sign-In, live Stripe Checkout, and the Gemini-backed chat agent
  requires real API credentials that weren't available in the build environment — those flows are
  implemented and reviewed but should be exercised with real keys per the setup steps above.

## Total development time

`[Fill in: total hours spent, per assignment instructions]`
