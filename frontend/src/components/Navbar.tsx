import { Link } from "react-router-dom";
import { ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";
import { GoogleLoginButton } from "@/components/GoogleLoginButton";

export function Navbar() {
  const { user, logout } = useAuth();
  const { totalItems } = useCart();

  return (
    <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-10">
      <div className="mx-auto max-w-6xl flex items-center justify-between px-4 h-16">
        <Link to="/" className="font-semibold text-lg">
          Mini AI Store
        </Link>

        <nav className="flex items-center gap-4">
          <Link to="/orders" className="text-sm hover:underline">
            My Orders
          </Link>
          {user?.role === "admin" && (
            <Link to="/admin" className="text-sm hover:underline">
              Admin
            </Link>
          )}
          <Link to="/cart" className="relative">
            <ShoppingCart className="size-5" />
            {totalItems > 0 && (
              <span className="absolute -top-2 -right-2 bg-primary text-primary-foreground text-xs rounded-full size-5 flex items-center justify-center">
                {totalItems}
              </span>
            )}
          </Link>

          {user ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground hidden sm:inline">{user.name}</span>
              <Button variant="outline" size="sm" onClick={logout}>
                Log out
              </Button>
            </div>
          ) : (
            <GoogleLoginButton />
          )}
        </nav>
      </div>
    </header>
  );
}
