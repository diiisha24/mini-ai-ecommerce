import { type ReactNode } from "react";
import { useAuth } from "@/context/AuthContext";
import { AuthScreen } from "@/components/AuthScreen";

export function ProtectedRoute({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="text-center py-20 text-muted-foreground">Loading...</div>;
  }

  if (!user) {
    return <AuthScreen message="Sign in to continue." />;
  }

  if (adminOnly && user.role !== "admin") {
    return <div className="text-center py-20 text-muted-foreground">Admins only.</div>;
  }

  return <>{children}</>;
}
