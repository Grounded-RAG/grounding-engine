import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function RequireAuth() {
  const { apiKey, auth, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="rounded-2xl border bg-card px-6 py-5 text-sm text-muted-foreground">
          Connecting to your workspace...
        </div>
      </div>
    );
  }

  if (!apiKey || !auth) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
