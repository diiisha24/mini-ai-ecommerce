import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import type { Order } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 30000;

export function OrderDetailPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const checkoutResult = searchParams.get("checkout");
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    api
      .get<Order>(`/api/orders/${id}`)
      .then((res) => {
        setOrder(res.data);
        setError(null);
      })
      .catch(() => setError("Could not load this order. Please try refreshing."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Right after a successful Stripe redirect the order is often still "pending_payment"
  // until the webhook lands - poll briefly instead of leaving the customer stuck looking
  // at a stale status with only a manual refresh button.
  useEffect(() => {
    if (checkoutResult !== "success" || order?.status !== "pending_payment") return;

    const start = Date.now();
    const interval = setInterval(() => {
      if (Date.now() - start > POLL_TIMEOUT_MS) {
        clearInterval(interval);
        return;
      }
      api
        .get<Order>(`/api/orders/${id}`)
        .then((res) => {
          setOrder(res.data);
          if (res.data.status !== "pending_payment") clearInterval(interval);
        })
        .catch(() => {
          /* keep polling silently; the manual refresh button covers persistent failures */
        });
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [checkoutResult, order?.status, id]);

  if (loading) return <p className="text-center py-20 text-muted-foreground">Loading order...</p>;
  if (error) return <p className="text-center py-20 text-destructive">{error}</p>;
  if (!order) return <p className="text-center py-20 text-muted-foreground">Order not found.</p>;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {checkoutResult === "success" && order.status === "pending_payment" && (
        <div className="mb-6 rounded-lg border bg-muted p-4 text-sm">
          Payment received by Stripe - waiting for the webhook to confirm the order. This
          updates automatically for a bit; refresh manually if it takes longer.
        </div>
      )}
      {checkoutResult === "cancelled" && (
        <div className="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm">
          Checkout was cancelled. Your items were not charged and stock has been released.
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Order #{order.id}</h1>
        <div className="flex items-center gap-3">
          <Badge>{order.status.replace("_", " ")}</Badge>
          <Button variant="outline" size="sm" onClick={load}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="space-y-3 mb-6">
        {order.items.map((item, i) => (
          <div key={i} className="flex justify-between border-b pb-2">
            <span>
              {item.quantity} x {item.product_name}
            </span>
            <span>${(Number(item.unit_price) * item.quantity).toFixed(2)}</span>
          </div>
        ))}
      </div>

      <div className="flex justify-between text-lg font-semibold mb-6">
        <span>Total</span>
        <span>${Number(order.total_amount).toFixed(2)}</span>
      </div>

      <Link to="/orders" className="text-sm underline">
        Back to my orders
      </Link>
    </div>
  );
}
