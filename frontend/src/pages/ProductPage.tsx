import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Product } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCart } from "@/context/CartContext";

export function ProductPage() {
  const { id } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [notFound, setNotFound] = useState(false);
  const { addToCart } = useCart();

  useEffect(() => {
    api
      .get<Product>(`/api/products/${id}`)
      .then((res) => setProduct(res.data))
      .catch(() => setNotFound(true));
  }, [id]);

  if (notFound) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground mb-4">Product not found.</p>
        <Link to="/" className="underline">
          Back to store
        </Link>
      </div>
    );
  }

  if (!product) return <p className="text-center py-20 text-muted-foreground">Loading...</p>;

  const outOfStock = product.stock <= 0;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 grid md:grid-cols-2 gap-8">
      <img
        src={product.image_url ?? "https://placehold.co/600x400?text=Product"}
        alt={product.name}
        className="w-full rounded-lg object-cover"
      />
      <div>
        <h1 className="text-2xl font-semibold mb-2">{product.name}</h1>
        <p className="text-muted-foreground mb-4">{product.description}</p>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl font-bold">${Number(product.price).toFixed(2)}</span>
          {outOfStock ? (
            <Badge variant="destructive">Out of stock</Badge>
          ) : (
            <Badge variant="secondary">{product.stock} in stock</Badge>
          )}
        </div>

        {!outOfStock && (
          <div className="flex items-center gap-3 mb-4">
            <label htmlFor="qty" className="text-sm">
              Quantity
            </label>
            <input
              id="qty"
              type="number"
              min={1}
              max={product.stock}
              value={quantity}
              onChange={(e) => setQuantity(Math.min(Math.max(1, Number(e.target.value)), product.stock))}
              className="w-20 border rounded px-2 py-1"
            />
          </div>
        )}

        <Button
          disabled={outOfStock}
          onClick={() => {
            addToCart(product, quantity);
            toast.success(`${quantity} x ${product.name} added to cart`);
          }}
        >
          Add to cart
        </Button>
      </div>
    </div>
  );
}
