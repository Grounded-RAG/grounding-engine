import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Leaf } from "lucide-react";
import { toast } from "sonner";
import { completeGoogleOAuth } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { workspacePath } from "@/lib/routes";

export default function GoogleOAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { signInWithApiKey, setWorkspace } = useAuth();

  useEffect(() => {
    const code = searchParams.get("code")?.trim();
    const error = searchParams.get("error")?.trim();
    const redirectUri = `${window.location.origin}/auth/google/callback`;

    if (error) {
      toast.error(`Google sign-in was cancelled: ${error}`);
      navigate("/login", { replace: true });
      return;
    }

    if (!code) {
      toast.error("Google sign-in did not return an authorization code.");
      navigate("/login", { replace: true });
      return;
    }

    void (async () => {
      try {
        const response = await completeGoogleOAuth(code, redirectUri);
        await signInWithApiKey(response.api_key);
        if (response.workspace_id && response.workspace_name && response.workspace_slug) {
          setWorkspace(response.workspace_id, response.workspace_name, response.workspace_slug);
        } else {
          setWorkspace(null, null, null);
        }
        queryClient.invalidateQueries();

        if (response.created_tenant || response.created_workspace) {
          navigate("/onboarding", { replace: true });
          toast.success("Google account connected. Finish setting up your workspace.");
          return;
        }

        navigate(workspacePath(response.workspace_slug), { replace: true });
        toast.success("Signed in with Google.");
      } catch (authError) {
        const message = authError instanceof Error ? authError.message : "Unable to complete Google sign-in.";
        toast.error(message);
        navigate("/login", { replace: true });
      }
    })();
  }, [navigate, queryClient, searchParams, setWorkspace, signInWithApiKey]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md rounded-3xl border bg-card p-8 shadow-sm text-center"
      >
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/10">
          <Leaf className="h-6 w-6 text-accent" />
        </div>
        <h1 className="text-2xl font-semibold tracking-[-0.04em] text-foreground mb-2">
          Finishing Google sign-in
        </h1>
        <p className="text-sm text-muted-foreground">
          We&apos;re verifying your Google account and preparing your Grounded workspace.
        </p>
      </motion.div>
    </div>
  );
}
