import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, ChevronDown, Key, Leaf, LockKeyhole, Mail } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";
import { listWorkspaces, signInWithEmail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { workspacePath } from "@/lib/routes";

export default function LoginPage() {
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
        setWorkspace(workspaces[0].workspace_id, workspaces[0].name, workspaces[0].slug);
        navigate(workspacePath(workspaces[0].slug));
      } else {
        setWorkspace(null, null, null);
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

  const handleEmailLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password.trim()) {
      toast.error("Enter your email and password to continue.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await signInWithEmail({
        email: email.trim(),
        password: password.trim(),
      });

      await signInWithApiKey(response.api_key);
      setWorkspace(response.workspace_id, response.workspace_name, response.workspace_slug);
      queryClient.invalidateQueries();
      navigate(workspacePath(response.workspace_slug));
      toast.success("Signed in to your workspace.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to sign in with email.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="flex flex-col justify-center px-8 md:px-16 lg:px-20 py-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-md w-full mx-auto lg:mx-0"
        >
          <div className="flex items-center justify-between mb-10">
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/10">
                <Leaf className="h-5 w-5 text-accent" />
              </div>
              <span className="text-lg font-semibold text-foreground">Grounded AI</span>
            </Link>
            <ThemeToggle />
          </div>

          <div className="rounded-[28px] border bg-card shadow-sm overflow-hidden">
            {!showEmailForm ? (
              <>
                <button
                  type="button"
                  disabled
                  className="w-full flex items-start gap-4 p-6 text-left border-b opacity-70 cursor-not-allowed"
                >
                  <div className="h-10 w-10 rounded-full bg-secondary flex items-center justify-center">
                    <LockKeyhole className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div>
                    <div className="text-xl font-medium text-foreground">Sign In with SSO</div>
                    <div className="text-sm text-muted-foreground">Find your workspace</div>
                  </div>
                  <Badge variant="coming" className="ml-auto text-[10px]">
                    Coming soon
                  </Badge>
                </button>

                <div className="grid md:grid-cols-2">
                  <button
                    type="button"
                    disabled
                    className="flex flex-col items-start gap-4 border-b md:border-b-0 md:border-r p-6 text-left opacity-70 cursor-not-allowed"
                  >
                    <svg className="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                    <div>
                      <div className="text-xl font-medium text-foreground">Sign In with Google</div>
                      <div className="text-sm text-muted-foreground">Coming soon</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowEmailForm(true)}
                    className="flex flex-col items-start gap-4 p-6 text-left transition-colors hover:bg-secondary/30"
                  >
                    <div className="h-10 w-10 rounded-full bg-secondary flex items-center justify-center">
                      <Mail className="h-5 w-5 text-foreground" />
                    </div>
                    <div>
                      <div className="text-xl font-medium text-foreground">Sign In with Email</div>
                      <div className="text-sm text-muted-foreground">Use your account password</div>
                    </div>
                  </button>
                </div>
              </>
            ) : (
              <form onSubmit={handleEmailLogin} className="p-6">
                <div className="mb-4">
                  <Label htmlFor="email" className="text-base font-medium text-foreground">
                    Email Address
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Enter your email and password to continue.
                  </p>
                </div>

                <div className="space-y-4">
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-12 rounded-2xl"
                  />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-12 rounded-2xl"
                  />
                </div>

                <div className="mt-6 flex items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    className="rounded-full"
                    onClick={() => setShowEmailForm(false)}
                  >
                    Back
                  </Button>
                  <Button
                    type="submit"
                    className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Signing in..." : "Continue"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>

                <div className="mt-6 text-sm text-muted-foreground">
                  Don&apos;t have an account?{" "}
                  <Link to="/sign-up" className="text-accent hover:underline">
                    Sign up
                  </Link>
                </div>
              </form>
            )}
          </div>

          <div className="rounded-[28px] border bg-card mt-5 overflow-hidden">
            <div className="px-6 py-5 text-center text-muted-foreground text-sm">
              Sign up with your work email to create your Grounded AI workspace
            </div>
            <Link
              to="/sign-up"
              className="flex items-center gap-3 px-6 py-5 border-t text-left transition-colors hover:bg-secondary/20"
            >
              <span className="text-2xl leading-none text-foreground">+</span>
              <span className="text-xl font-medium text-foreground">Sign Up for Free</span>
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setShowApiKey((current) => !current)}
            className="mt-5 flex w-full items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <Key className="h-3.5 w-3.5" />
            Developer access
            <ChevronDown className={`h-3.5 w-3.5 ml-auto transition-transform ${showApiKey ? "rotate-180" : ""}`} />
          </button>

          {showApiKey ? (
            <motion.form
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              onSubmit={handleApiLogin}
              className="mt-4 space-y-4 rounded-2xl border bg-card p-5"
            >
              <div>
                <Label htmlFor="apiKey" className="text-sm text-muted-foreground">
                  API Key
                </Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="grd_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                />
              </div>
              <Button
                className="w-full rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
                type="submit"
                disabled={isSubmitting}
              >
                Connect
              </Button>
            </motion.form>
          ) : null}
        </motion.div>
      </div>

      <div className="hidden lg:flex items-center justify-center relative overflow-hidden bg-secondary/50">
        <div className="absolute inset-0 gradient-hero" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full bg-accent/8 blur-[80px]" />
        <div className="absolute bottom-1/4 left-1/4 w-72 h-72 rounded-full bg-accent-teal/8 blur-[60px]" />
        <div className="relative z-10 text-center max-w-md px-8">
          <div className="flex items-center justify-center gap-3 mb-6 opacity-50">
            <Leaf className="h-5 w-5 text-accent" />
            <span className="text-sm text-muted-foreground">Grounded AI</span>
          </div>
          <h2 className="text-5xl font-semibold tracking-[-0.05em] text-foreground leading-tight mb-5">
            The grounded intelligence layer for enterprise AI
          </h2>
          <img
            src="/placeholder.svg"
            alt="Grounded AI visual"
            className="mt-10 w-full max-w-xl opacity-90"
          />
        </div>
      </div>
    </div>
  );
}
