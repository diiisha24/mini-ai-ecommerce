# System Design — Mini AI E-Commerce Application

## One-page overview

```
                                   ┌────────────────────┐
                                   │   Google OAuth 2.0   │
                                   │ (Identity provider)  │
                                   └──────────┬───────────┘
                                              │ ID token (JWT, verified
                                              │ server-side per request)
                                              ▼
┌───────────────┐   HTTPS/JSON    ┌──────────────────────┐        SQL         ┌───────────────┐
│   Frontend    │ ───────────────▶│    FastAPI Backend    │ ──────────────────▶│  PostgreSQL   │
│ React + TS    │◀─────────────── │  (Python, Uvicorn)    │◀────────────────────│  (SQLModel)   │
│ Tailwind      │  REST API +     │                        │   users, products,  │               │
│ shadcn/ui     │  session JWT    │  - Auth (Google verify │   orders, order_    │               │
└───────┬───────┘                 │    + issue own JWT)    │   items             └───────────────┘
        │                         │  - RBAC (customer/     │
        │ redirect to             │    admin dependencies) │
        │ Stripe-hosted           │  - Product/Order APIs  │
        │ checkout page           │  - Stripe checkout +   │        HTTPS
        ▼                         │    webhook handler     │ ───────────────────▶ ┌───────────────┐
┌───────────────┐   webhook       │  - AI chat endpoint     │                       │    Stripe     │
│    Stripe      │ ──────────────▶│    (LangGraph agent)   │◀───────────────────── │ Checkout +    │
│  Checkout      │  (payment      └───────────┬────────────┘   payment result/      │ Webhooks      │
│  (test mode)   │   confirmed/                │                signature verify    │ (test mode)   │
└───────────────┘   failed)                    │ tool calls (list_products,
                                               │ get_product_price,
                                               │ get_order_status - scoped
                                               │ to the authenticated user)
                                               ▼
                                  ┌────────────────────────┐
                                  │  Google Gemini (LLM)     │
                                  │  via langchain-google-   │
                                  │  genai + LangGraph        │
                                  │  react agent               │
                                  └────────────────────────┘
```

## Components

| Component | Responsibility |
|---|---|
| **Frontend** (React + TypeScript + Tailwind + shadcn/ui) | Product browsing, cart (client-side, `localStorage`), Google Sign-In, checkout redirect, order history, admin dashboard, AI chat widget. Holds the session JWT and attaches it as `Authorization: Bearer <token>` on every API call. |
| **FastAPI backend** | Single source of truth for authorization, business rules (stock, pricing, order state), and third-party integration (Google, Stripe, Gemini). All RBAC checks happen here — the frontend hides UI it shouldn't show, but every API route independently re-checks role and ownership. |
| **PostgreSQL** | `user`, `product`, `order`, `orderitem` tables (see `docs/db-schema.md`). Accessed via SQLModel (SQLAlchemy + Pydantic). |
| **Google OAuth** | Identity only. The frontend collects a Google ID token via Google Sign-In; the backend verifies its signature against Google's public keys and either creates or logs in the matching `user` row. The backend then issues its **own** short-lived JWT for session auth — Google's token is never reused after that first exchange. |
| **Stripe** (test mode) | Hosted Checkout Session for payment collection, plus a webhook that is the single source of truth for "did the customer actually pay." The backend never marks an order paid from the frontend redirect alone. |
| **AI Agent** (LangGraph `create_react_agent` + Gemini) | Built per-request with tools closed over the authenticated user and DB session, so it can only ever query that user's own orders. Tools: `list_products`, `get_product_price`, `get_order_status`. |

## Key flows

**Auth:** Frontend → Google Sign-In popup → ID token → `POST /api/auth/google` → backend verifies token with `google-auth`, upserts `User`, returns a backend-issued JWT → frontend stores it and sends it as a bearer token on every subsequent call.

**Checkout/payment:** Frontend sends cart lines → `POST /api/orders/checkout` → backend validates stock, **reserves stock immediately**, creates an `Order` (`pending_payment`) + `OrderItem`s, creates a Stripe Checkout Session, returns its URL → frontend redirects the browser to Stripe → Stripe redirects back to `/orders/:id?checkout=success|cancelled` (informational only) → Stripe also calls `POST /api/webhooks/stripe` asynchronously, which is what actually flips the order to `paid` (on `checkout.session.completed`) or `failed` + restores stock (on `checkout.session.expired`/`async_payment_failed`).

**AI support chat:** Frontend → `POST /api/ai/chat` (authenticated) → backend builds a fresh LangGraph agent scoped to that user and session → agent calls tools that hit the real database → reply is returned as plain text, never fabricated by the LLM alone.

## AWS deployment approach (not deployed in this exercise — see README for scope)

- **Frontend**: static build (`vite build`) served from **S3 + CloudFront**, or a small **Amplify Hosting** deployment for simplicity.
- **Backend**: containerized (Dockerfile already provided) on **ECS Fargate** (or App Runner for a quicker path) behind an **Application Load Balancer**, with the container reading secrets from **AWS Secrets Manager** / SSM Parameter Store rather than a committed `.env`.
- **Database**: **Amazon RDS for PostgreSQL** (single-AZ is enough for this scale; multi-AZ for production).
- **Stripe webhook**: ALB target must be publicly reachable over HTTPS (ACM certificate) since Stripe calls it directly.
- **Secrets**: `GOOGLE_CLIENT_ID`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `GOOGLE_API_KEY`, `JWT_SECRET` all come from Secrets Manager, injected as container env vars — never baked into the image.
- **CI/CD**: GitHub Actions building the Docker image → push to **ECR** → deploy to ECS on merge to `main`.

## Scaling considerations

**What the current setup can actually take, concretely, before any of this is needed:**
the backend container runs bare `uvicorn app.main:app` (`backend/Dockerfile`) — a single
process, single event loop, no `--workers`. The DB engine (`app/db.py`) uses SQLAlchemy's
default pool (5 connections + 10 overflow = **15 concurrent DB-bound requests** before the
pool starts queuing/timing out). That's the real ceiling of what's deployed today, not a
hypothetical — it's the point the steps below actually start to matter, not the immediate
next step.

If users and AI requests increased significantly past that:

- **Backend**: FastAPI/Uvicorn is stateless (JWT auth, no server-side sessions) so it scales
  horizontally trivially — add ECS Fargate tasks behind the ALB, autoscaled on CPU/request
  count. Before reaching for that: `uvicorn --workers N` (or Gunicorn with the Uvicorn
  worker class) on the existing single container is the cheaper first step, and bumping the
  SQLAlchemy pool size alongside it.
- **Database**: move read-heavy traffic (product listing) behind a read replica; indexes
  already in place cover the query patterns that exist today — `user.email`/`google_sub`
  (login lookups), `product.name` + `product.is_active` (storefront listing),
  `order.stripe_checkout_session_id` (webhook correlation), a composite
  `(order.user_id, order.created_at)` (order history, filter + sort in one index scan), and
  `order_item.product_id` (so "which orders contain product X" isn't a full table scan).
  List endpoints (`/api/products`, `/api/orders`, both admin list routes) are paginated
  (`limit`/`offset`, capped at 100) rather than returning an unbounded result set. Introduce
  Redis for product-catalog caching if read volume grows much larger than write volume.
- **AI agent**: this is the most expensive and latency-sensitive part. The Gemini model
  client is already a module-level singleton, reused across requests (only the per-request
  *tool set* is rebuilt, since that's what scopes each agent instance to the calling user -
  see `services/ai_agent.py`), so the remaining overhead is genuinely LLM latency/cost, not
  avoidable client construction.
  - Move chat calls off the request/response path onto a queue (SQS) + async worker if traffic gets bursty, returning a "thinking" state to the frontend and polling/websocket for the reply.
  - Cache tool outputs that don't change often (e.g., `list_products`) for a short TTL to cut redundant DB hits per chat turn.
  - Add per-user rate limiting on `/api/ai/chat` to control LLM cost, and consider a cheaper/faster Gemini model tier for simple lookups, reserving a larger model only if conversations get more complex.
  - Track token usage/cost per request (LangSmith or custom logging) to catch runaway costs early.
- **Stripe webhooks**: idempotent by checking `order.status == pending_payment` before
  transitioning it, **under a row lock** (`with_for_update=True` on the order fetch) so two
  genuinely concurrent deliveries of the same event can't both pass the check before either
  commits — Stripe's automatic retries under load never double-process an order.
- **Observability**: structured logging + request tracing (e.g., OpenTelemetry) becomes necessary once there's enough traffic that "check the logs by eye" stops working.
