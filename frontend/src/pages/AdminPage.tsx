import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Order, Product } from "@/lib/types";
import { ProductRow } from "@/components/admin/ProductRow";

const STATUS_VARIANT: Record<Order["status"], "default" | "secondary" | "destructive"> = {
  pending_payment: "secondary",
  paid: "default",
  failed: "destructive",
  cancelled: "destructive",
};

function NewProductForm({ onCreated }: { onCreated: (p: Product) => void }) {
  const [form, setForm] = useState({ name: "", description: "", price: "", stock: "", image_url: "" });
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api.post<Product>("/api/admin/products", {
        name: form.name,
        description: form.description,
        price: Number(form.price),
        stock: Number(form.stock) || 0,
        image_url: form.image_url || null,
      });
      onCreated(res.data);
      setForm({ name: "", description: "", price: "", stock: "", image_url: "" });
      toast.success("Product created");
    } catch {
      toast.error("Failed to create product");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6 items-end">
      <div>
        <Label className="mb-1">Name</Label>
        <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div>
        <Label className="mb-1">Description</Label>
        <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div>
        <Label className="mb-1">Price</Label>
        <Input
          required
          type="number"
          step="0.01"
          value={form.price}
          onChange={(e) => setForm({ ...form, price: e.target.value })}
        />
      </div>
      <div>
        <Label className="mb-1">Stock</Label>
        <Input
          type="number"
          value={form.stock}
          onChange={(e) => setForm({ ...form, stock: e.target.value })}
        />
      </div>
      <Button type="submit" disabled={submitting}>
        Add product
      </Button>
    </form>
  );
}

function ProductsTab() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Product[]>("/api/admin/products")
      .then((res) => setProducts(res.data))
      .catch(() => setError("Could not load products."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted-foreground">Loading products...</p>;
  if (error) return <p className="text-destructive">{error}</p>;

  return (
    <div>
      <NewProductForm onCreated={(p) => setProducts((prev) => [p, ...prev])} />
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="p-2">Name</th>
            <th className="p-2">Price</th>
            <th className="p-2">Stock</th>
            <th className="p-2">Status</th>
            <th className="p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <ProductRow
              key={p.id}
              product={p}
              onChanged={(updated) =>
                setProducts((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
              }
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OrdersTab() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Order[]>("/api/admin/orders")
      .then((res) => setOrders(res.data))
      .catch(() => setError("Could not load orders."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted-foreground">Loading orders...</p>;
  if (error) return <p className="text-destructive">{error}</p>;

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left border-b">
          <th className="p-2">Order</th>
          <th className="p-2">Customer</th>
          <th className="p-2">Total</th>
          <th className="p-2">Status</th>
          <th className="p-2">Placed</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id} className="border-b">
            <td className="p-2">#{o.id}</td>
            <td className="p-2">{o.user_email}</td>
            <td className="p-2">${Number(o.total_amount).toFixed(2)}</td>
            <td className="p-2">
              <Badge variant={STATUS_VARIANT[o.status]}>{o.status.replace("_", " ")}</Badge>
            </td>
            <td className="p-2">{new Date(o.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function AdminPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Admin Dashboard</h1>
      <Tabs defaultValue="products">
        <TabsList className="mb-4">
          <TabsTrigger value="products">Products</TabsTrigger>
          <TabsTrigger value="orders">Orders</TabsTrigger>
        </TabsList>
        <TabsContent value="products">
          <ProductsTab />
        </TabsContent>
        <TabsContent value="orders">
          <OrdersTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
