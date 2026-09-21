import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { CartLine, Product } from "@/lib/types";

interface CartContextValue {
  lines: CartLine[];
  addToCart: (product: Product, quantity?: number) => void;
  updateQuantity: (productId: number, quantity: number) => void;
  removeFromCart: (productId: number) => void;
  clearCart: () => void;
  /** Replaces a stale cached product snapshot with the latest server data, clamping
   * quantity to the current stock. Returns true if anything actually changed, so the
   * caller can tell the user their cart was adjusted. */
  syncProduct: (product: Product) => boolean;
  totalItems: number;
  totalPrice: number;
}

const CartContext = createContext<CartContextValue | undefined>(undefined);
const STORAGE_KEY = "cart_lines";

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as CartLine[]) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
  }, [lines]);

  function addToCart(product: Product, quantity = 1) {
    setLines((prev) => {
      const existing = prev.find((l) => l.product.id === product.id);
      if (existing) {
        return prev.map((l) =>
          l.product.id === product.id
            ? { ...l, quantity: Math.min(l.quantity + quantity, product.stock) }
            : l
        );
      }
      return [...prev, { product, quantity: Math.min(quantity, product.stock) }];
    });
  }

  function updateQuantity(productId: number, quantity: number) {
    setLines((prev) =>
      prev
        .map((l) => (l.product.id === productId ? { ...l, quantity } : l))
        .filter((l) => l.quantity > 0)
    );
  }

  function removeFromCart(productId: number) {
    setLines((prev) => prev.filter((l) => l.product.id !== productId));
  }

  function clearCart() {
    setLines([]);
  }

  function syncProduct(product: Product): boolean {
    let changed = false;
    setLines((prev) =>
      prev
        .map((l) => {
          if (l.product.id !== product.id) return l;
          const clampedQuantity = Math.min(l.quantity, product.stock);
          if (
            l.product.price !== product.price ||
            l.product.stock !== product.stock ||
            l.product.is_active !== product.is_active ||
            clampedQuantity !== l.quantity
          ) {
            changed = true;
          }
          return { product, quantity: clampedQuantity };
        })
        .filter((l) => l.product.is_active && l.quantity > 0)
    );
    return changed;
  }

  const totalItems = lines.reduce((sum, l) => sum + l.quantity, 0);
  const totalPrice = lines.reduce((sum, l) => sum + Number(l.product.price) * l.quantity, 0);

  return (
    <CartContext.Provider
      value={{
        lines,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        syncProduct,
        totalItems,
        totalPrice,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
