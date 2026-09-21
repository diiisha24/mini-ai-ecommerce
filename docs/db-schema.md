# Database Schema

PostgreSQL, managed via SQLModel (`app/models.py`). Tables are created on backend startup via
`SQLModel.metadata.create_all()` — no Alembic migrations for this exercise's scope (see README
"Scope notes").

## `user`

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER` | Primary key |
| `google_sub` | `VARCHAR` | Unique. Google's stable subject identifier — the real identity anchor, not the email. |
| `email` | `VARCHAR` | Unique, indexed |
| `name` | `VARCHAR` | From Google profile, refreshed on every login |
| `picture` | `VARCHAR`, nullable | Google avatar URL |
| `role` | `VARCHAR` enum (`customer`, `admin`) | Default `customer`. Granted `admin` at signup time only if the email is in the `ADMIN_EMAILS` env allow-list. |
| `created_at` | `TIMESTAMP` | |

## `product`

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER` | Primary key |
| `name` | `VARCHAR` | Indexed |
| `description` | `TEXT` | |
| `price` | `DECIMAL(10,2)` | |
| `image_url` | `VARCHAR`, nullable | |
| `stock` | `INTEGER` | Decremented at checkout time (reserved), restored on payment failure/expiry |
| `is_active` | `BOOLEAN` | Indexed — every storefront listing query filters on it. Soft-delete flag: admin "delete" sets this false instead of removing the row, so historical `order_item` snapshots stay valid |
| `created_at` / `updated_at` | `TIMESTAMP` | |

## `order`

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER` | Primary key |
| `user_id` | `INTEGER` FK → `user.id` | Part of a composite index with `created_at` (see below). Ownership check for every customer-facing read. |
| `status` | `VARCHAR` enum (`pending_payment`, `paid`, `failed`, `cancelled`) | `pending_payment` → `paid` only via the Stripe webhook |
| `total_amount` | `DECIMAL(10,2)` | Computed server-side from product prices at checkout time, never trusted from the client |
| `stripe_checkout_session_id` | `VARCHAR`, nullable | Indexed. Used by the webhook to locate the order (via `metadata.order_id`, session id kept for audit) |
| `stripe_payment_intent_id` | `VARCHAR`, nullable | Set once payment is confirmed |
| `created_at` / `updated_at` | `TIMESTAMP` | |

## `orderitem`

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER` | Primary key |
| `order_id` | `INTEGER` FK → `order.id` | Indexed |
| `product_id` | `INTEGER` FK → `product.id` | Indexed — Postgres does not auto-index FK columns the way it does primary keys; without this, "which orders contain product X" is a full table scan |
| `product_name` | `VARCHAR` | **Snapshot** at purchase time — survives later product renames/price changes |
| `unit_price` | `DECIMAL(10,2)` | Snapshot, not a live lookup |
| `quantity` | `INTEGER` | |

## Indexes

Besides the primary keys, unique constraints (`user.email`, `user.google_sub`), and
single-column indexes noted in the tables above:

- **`ix_order_user_id_created_at`** — composite index on `order(user_id, created_at)`.
  Serves both "all orders for this user" (leftmost-prefix) and, more importantly, the
  actual query pattern used everywhere order history is listed — `WHERE user_id = ? ORDER
  BY created_at DESC` — in a single index scan instead of an index lookup plus a separate
  sort step. Replaces what would otherwise be a single-column index on `user_id` alone.

All list endpoints (`GET /api/products`, `GET /api/orders`, both admin list routes) are
paginated with `limit`/`offset` query params (default and max 100) rather than returning
an unbounded result set — fine to omit at 5 seed products, a real problem at any
production catalog size.

## Design notes

- **No server-side `cart` table.** The cart is client-side (`localStorage`) until checkout, when the
  full cart is submitted in one `POST /api/orders/checkout` call. This matches the assignment's
  "basic checkout flow" scope without building a redundant persistence layer for something that's
  inherently ephemeral, per-browser state.
- **Order/line-item snapshotting** (`product_name`, `unit_price` on `OrderItem`) means a price change
  or product edit after purchase never rewrites history — order totals stay accurate to what the
  customer actually paid.
- **Stock is reserved at order creation**, not at payment confirmation, to prevent overselling while a
  customer is on the Stripe payment page. If payment fails or the session expires, the webhook
  restores the reserved stock.
