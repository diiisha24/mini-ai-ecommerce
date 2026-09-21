import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Product } from "@/lib/types";

export function ProductRow({
  product,
  onChanged,
}: {
  product: Product;
  onChanged: (updated: Product) => void;
}) {
  const [name, setName] = useState(product.name);
  const [price, setPrice] = useState(product.price);
  const [stock, setStock] = useState(product.stock);
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const res = await api.put<Product>(`/api/admin/products/${product.id}`, {
        name,
        price: Number(price),
        stock: Number(stock),
      });
      onChanged(res.data);
      toast.success(`${res.data.name} updated`);
    } catch {
      toast.error("Failed to update product");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    setSaving(true);
    try {
      if (product.is_active) {
        await api.delete(`/api/admin/products/${product.id}`);
        onChanged({ ...product, is_active: false });
      } else {
        const res = await api.put<Product>(`/api/admin/products/${product.id}`, { is_active: true });
        onChanged(res.data);
      }
    } catch {
      toast.error("Failed to update product");
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className="border-b">
      <td className="p-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} className="min-w-[160px]" />
      </td>
      <td className="p-2">
        <Input
          type="number"
          step="0.01"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          className="w-24"
        />
      </td>
      <td className="p-2">
        <Input
          type="number"
          value={stock}
          onChange={(e) => setStock(Number(e.target.value))}
          className="w-20"
        />
      </td>
      <td className="p-2">
        <Badge variant={product.is_active ? "secondary" : "destructive"}>
          {product.is_active ? "active" : "inactive"}
        </Badge>
      </td>
      <td className="p-2 flex gap-2">
        <Button size="sm" disabled={saving} onClick={save}>
          Save
        </Button>
        <Button size="sm" variant="outline" disabled={saving} onClick={toggleActive}>
          {product.is_active ? "Deactivate" : "Activate"}
        </Button>
      </td>
    </tr>
  );
}
