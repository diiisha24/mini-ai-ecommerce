import { Link } from "react-router-dom";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useCart } from "@/context/CartContext";
import type { Product } from "@/lib/types";
import { toast } from "sonner";

export function ProductCard({ product }: { product: Product }) {
  const { addToCart } = useCart();
  const outOfStock = product.stock <= 0;

  return (
    <Card className="flex flex-col overflow-hidden">
      <Link to={`/products/${product.id}`}>
        <img
          src={product.image_url ?? "https://placehold.co/400x300?text=Product"}
          alt={product.name}
          className="w-full h-40 object-cover"
        />
      </Link>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          <Link to={`/products/${product.id}`} className="hover:underline">
            {product.name}
          </Link>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex items-center justify-between">
        <span className="text-lg font-semibold">${Number(product.price).toFixed(2)}</span>
        {outOfStock ? (
          <Badge variant="destructive">Out of stock</Badge>
        ) : (
          <Badge variant="secondary">{product.stock} in stock</Badge>
        )}
      </CardContent>
      <CardFooter>
        <Button
          className="w-full"
          disabled={outOfStock}
          onClick={() => {
            addToCart(product, 1);
            toast.success(`${product.name} added to cart`);
          }}
        >
          Add to cart
        </Button>
      </CardFooter>
    </Card>
  );
}
