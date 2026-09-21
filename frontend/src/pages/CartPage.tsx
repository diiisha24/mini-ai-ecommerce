import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { GoogleLoginButton } from "@/components/GoogleLoginButton";
import { api } from "@/lib/api";
import type { Product } from "@/lib/types";

export function CartPage() {
  const { lines, updateQuantity, removeFromCart, totalPrice, clearCart, syncProduct } = useCart();
  const { user } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const syncedRef = useRef(false);

  // Cart lines cache a snapshot of each product (price/stock) from whenever it was added.
  // Re-fetch the latest data on every visit so the totals shown here match what checkout
  // will actually charge, instead of trusting a possibly stale localStorage snapshot.
  useEffect(() => {
    if (syncedRef.current || lines.length === 0) return;
    syncedRef.current = true;

    let anyChanged = false;
    Promise.all(
      lines.map((l) =>
        api
          .get<Product>(`/api/products/${l.product.id}`)
          .then((res) => {
            if (syncProduct(res.data)) anyChanged = true;
          })
          .catch(() => {
            // Product no longer exists/is inactive - leave it; the checkout call will
            // surface a clear error if the customer tries to buy it.
          })
      )
    ).then(() => {
      if (anyChanged) {
        toast.info("Your cart was updated to reflect the latest prices/stock.");
      }
    });
  }, [lines, syncProduct]);

  async function handleCheckout() {
    setSubmitting(true);
    try {
      const res = await api.post<{ order_id: number; checkout_url: string }>("/api/orders/checkout", {
        items: lines.map((l) => ({ product_id: l.product.id, quantity: l.quantity })),
      });
      clearCart();
      window.location.href = res.data.checkout_url;
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        "Checkout failed. Please try again.";
      toast.error(message);
      setSubmitting(false);
    }
  }

  if (lines.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground mb-4">Your cart is empty.</p>
        <Link to="/" className="underline">
          Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Your Cart</h1>

      <div className="space-y-4 mb-6">
        {lines.map((line) => (
          <div key={line.product.id} className="flex items-center gap-4 border-b pb-4">
            <img
              src={line.product.image_url ?? "https://placehold.co/80x80"}
              alt={line.product.name}
              className="size-16 object-cover rounded"
            />
            <div className="flex-1">
              <p className="font-medium">{line.product.name}</p>
              <p className="text-sm text-muted-foreground">${Number(line.product.price).toFixed(2)} each</p>
            </div>
            <input
              type="number"
              min={1}
              max={line.product.stock}
              value={line.quantity}
              onChange={(e) => updateQuantity(line.product.id, Number(e.target.value))}
              className="w-16 border rounded px-2 py-1"
            />
            <span className="w-20 text-right">${(Number(line.product.price) * line.quantity).toFixed(2)}</span>
            <button
              className="text-sm text-destructive hover:underline"
              onClick={() => removeFromCart(line.product.id)}
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between mb-6">
        <span className="text-lg font-semibold">Total</span>
        <span className="text-lg font-semibold">${totalPrice.toFixed(2)}</span>
      </div>

      {user ? (
        <Button className="w-full" disabled={submitting} onClick={handleCheckout}>
          {submitting ? "Starting checkout..." : "Checkout with Stripe"}
        </Button>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <p className="text-sm text-muted-foreground">Sign in to check out.</p>
          <GoogleLoginButton />
        </div>
      )}

      <button
        className="mt-4 text-sm text-muted-foreground hover:underline"
        onClick={() => navigate("/")}
      >
        Continue shopping
      </button>
    </div>
  );
}
