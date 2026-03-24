import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Mail, ArrowRight, Key, ChevronDown, LockKeyhole } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { listWorkspaces, signInWithEmail } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const [showApiKey, setShowApiKey] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { signInWithApiKey, setWorkspace } = useAuth();

  const handleApiLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      toast.error("Enter a valid API key to continue.");
      return;
    }

    setIsSubmitting(true);
    try {
      await signInWithApiKey(apiKey);
      const workspaces = await listWorkspaces(apiKey.trim());
      queryClient.invalidateQueries();

      if (workspaces.length > 0) {
        setWorkspace(workspaces[0].workspace_id, workspaces[0].name);
        navigate("/app");
      } else {
        setWorkspace(null, null);
        navigate("/onboarding");
      }
      toast.success("Workspace connected.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to connect with that API key.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      toast.error("Enter your work email to continue.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await signInWithEmail({
        email: email.trim(),
        full_name: fullName.trim() || undefined,
        organization_name: organizationName.trim() || undefined,
        workspace_name: workspaceName.trim() || undefined,
      });

      await signInWithApiKey(response.api_key);
      setWorkspace(response.workspace_id, response.workspace_name);
      queryClient.invalidateQueries();
      navigate("/app");

      toast.success(
        response.created_tenant
          ? "Workspace created and you are signed in."
          : "Signed in to your workspace.",
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to sign in with email.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* Left: Login form */}
      <div className="flex flex-col justify-center px-8 md:px-16 lg:px-20 py-12">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="max-w-sm w-full mx-auto lg:mx-0">
          <div className="flex items-center justify-between mb-10">
            <Link to="/" className="flex items-center gap-2">
              <img src="/grounded-mark.svg" alt="Grounded AI" className="h-8 w-8" />
              <span className="text-lg font-bold text-foreground">Grounded AI</span>
            </Link>
            <ThemeToggle />
          </div>

          <h1 className="font-display text-3xl font-semibold tracking-[-0.03em] text-foreground mb-2">
            Sign in to Grounded
          </h1>
          <p className="text-muted-foreground mb-8">
            Use your work email to open or provision your workspace.
          </p>

          <form onSubmit={handleEmailLogin} className="space-y-4 mb-6">
            <div>
              <Label htmlFor="email" className="text-sm text-muted-foreground">Work email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1.5 h-11 rounded-xl"
              />
            </div>
            <div>
              <Label htmlFor="fullName" className="text-sm text-muted-foreground">Full name</Label>
              <Input
                id="fullName"
                type="text"
                placeholder="Samrawit A."
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="mt-1.5 h-11 rounded-xl"
              />
            </div>
            <div>
              <Label htmlFor="organizationName" className="text-sm text-muted-foreground">Organization</Label>
              <Input
                id="organizationName"
                type="text"
                placeholder="iCog Labs"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                className="mt-1.5 h-11 rounded-xl"
              />
            </div>
            <div>
              <Label htmlFor="workspaceName" className="text-sm text-muted-foreground">Workspace name</Label>
              <Input
                id="workspaceName"
                type="text"
                placeholder="Research Ops"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="mt-1.5 h-11 rounded-xl"
              />
              <p className="text-xs text-muted-foreground mt-1.5">
                If this is your first sign-in, Grounded will create the workspace for you.
              </p>
            </div>
            <Button
              className="w-full rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
              type="submit"
              disabled={isSubmitting}
            >
              <Mail className="h-4 w-4 mr-2" />
              {isSubmitting ? "Signing in..." : "Sign in with email"}
            </Button>
          </form>

          <div className="space-y-3 mb-6">
            <Button variant="outline" className="w-full justify-start gap-3 h-11 rounded-xl" disabled>
              <svg className="h-4 w-4" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
              Sign in with Google
              <Badge variant="coming" className="ml-auto text-[10px]">Coming soon</Badge>
            </Button>
            <Button variant="outline" className="w-full justify-start gap-3 h-11 rounded-xl" disabled>
              <LockKeyhole className="h-4 w-4" />
              Sign in with SSO
              <Badge variant="coming" className="ml-auto text-[10px]">Coming soon</Badge>
            </Button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            Google and SSO are still coming soon. Email sign-in works today by provisioning a
            workspace session on the backend and issuing the secure API key behind the scenes.
          </p>

          {/* Developer access */}
          <button
            onClick={() => setShowApiKey(!showApiKey)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4 w-full"
          >
            <Key className="h-3.5 w-3.5" />
            Developer access
            <ChevronDown className={`h-3.5 w-3.5 ml-auto transition-transform ${showApiKey ? 'rotate-180' : ''}`} />
          </button>

          {showApiKey && (
            <motion.form
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              onSubmit={handleApiLogin}
              className="space-y-4"
            >
              <div>
                <Label htmlFor="apiKey" className="text-sm text-muted-foreground">API Key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="grd_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                />
                <p className="text-xs text-muted-foreground mt-1.5">For programmatic access and integrations</p>
              </div>
              <Button
                className="w-full rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
                type="submit"
                disabled={isSubmitting}
              >
                Connect <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </motion.form>
          )}
        </motion.div>
      </div>

      {/* Right: Visual */}
      <div className="hidden lg:flex items-center justify-center relative overflow-hidden bg-secondary/50">
        <div className="absolute inset-0 gradient-hero" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full bg-accent/8 blur-[80px]" />
        <div className="absolute bottom-1/4 left-1/4 w-72 h-72 rounded-full bg-accent-teal/8 blur-[60px]" />
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="relative z-10 text-center max-w-sm"
        >
          <img src="/grounded-mark.svg" alt="Grounded AI" className="h-16 w-16 mx-auto mb-6" />
          <h2 className="font-display text-3xl font-semibold tracking-[-0.03em] text-foreground mb-3">
            Grounded intelligence
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Evidence-first AI that reduces hallucination and resolves ambiguity for expert work.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
