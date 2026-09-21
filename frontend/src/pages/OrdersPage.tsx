import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import type { Order } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const STATUS_VARIANT: Record<Order["status"], "default" | "secondary" | "destructive"> = {
  pending_payment: "secondary",
  paid: "default",
  failed: "destructive",
  cancelled: "destructive",
};

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Order[]>("/api/orders")
      .then((res) => setOrders(res.data))
      .catch(() => setError("Could not load your orders. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-center py-20 text-muted-foreground">Loading orders...</p>;
  if (error) return <p className="text-center py-20 text-destructive">{error}</p>;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">My Orders</h1>
      {orders.length === 0 && <p className="text-muted-foreground">You haven't placed any orders yet.</p>}
      <div className="space-y-3">
        {orders.map((order) => (
          <Link
            key={order.id}
            to={`/orders/${order.id}`}
            className="flex items-center justify-between border rounded-lg p-4 hover:bg-muted/50"
          >
            <div>
              <p className="font-medium">Order #{order.id}</p>
              <p className="text-sm text-muted-foreground">
                {new Date(order.created_at).toLocaleString()}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-medium">${Number(order.total_amount).toFixed(2)}</span>
              <Badge variant={STATUS_VARIANT[order.status]}>{order.status.replace("_", " ")}</Badge>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
