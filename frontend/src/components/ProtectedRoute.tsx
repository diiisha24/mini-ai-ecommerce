import { type ReactNode } from "react";
import { useAuth } from "@/context/AuthContext";
import { GoogleLoginButton } from "@/components/GoogleLoginButton";

export function ProtectedRoute({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="text-center py-20 text-muted-foreground">Loading...</div>;
  }

  if (!user) {
    return (
      <div className="flex flex-col items-center gap-4 py-20">
        <p className="text-muted-foreground">Sign in to continue.</p>
        <GoogleLoginButton />
      </div>
    );
  }

  if (adminOnly && user.role !== "admin") {
    return <div className="text-center py-20 text-muted-foreground">Admins only.</div>;
  }

  return <>{children}</>;
}
