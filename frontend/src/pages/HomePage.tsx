import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Product } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";

export function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Product[]>("/api/products")
      .then((res) => setProducts(res.data))
      .catch(() => setError("Could not load products."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-center py-20 text-muted-foreground">Loading products...</p>;
  if (error) return <p className="text-center py-20 text-destructive">{error}</p>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Products</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
      {products.length === 0 && <p className="text-muted-foreground">No products available yet.</p>}
    </div>
  );
}
