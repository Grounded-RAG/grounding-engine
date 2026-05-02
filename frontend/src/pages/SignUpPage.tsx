import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Leaf } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/ThemeToggle";
import { signUpWithEmail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { workspacePath } from "@/lib/routes";
import heroVisual from "@/assets/hero-visual.png";

export default function SignUpPage() {
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    organizationName: "",
    workspaceName: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { signInWithApiKey, setWorkspace } = useAuth();

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.email.trim() || !form.password.trim() || !form.organizationName.trim()) {
      toast.error("Enter your email, password, and organization to continue.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await signUpWithEmail({
        email: form.email.trim(),
        password: form.password.trim(),
        full_name: form.fullName.trim() || undefined,
        organization_name: form.organizationName.trim(),
        workspace_name: form.workspaceName.trim() || undefined,
      });

      await signInWithApiKey(response.api_key);
      setWorkspace(response.workspace_id, response.workspace_name, response.workspace_slug);
      queryClient.invalidateQueries();
      navigate(workspacePath(response.workspace_slug));
      toast.success("Account created. Welcome to Grounded AI.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create your account.";
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

          <div className="rounded-[28px] border bg-card p-6 shadow-sm">
            <h1 className="text-3xl font-semibold tracking-[-0.04em] text-foreground mb-2">
              Create your account
            </h1>
            <p className="text-sm text-muted-foreground mb-6">
              Set up your workspace and start building grounded agents over your organization&apos;s knowledge.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="full-name">Full name</Label>
                <Input
                  id="full-name"
                  value={form.fullName}
                  onChange={(event) => update("fullName", event.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                  placeholder="Samrawit A."
                />
              </div>
              <div>
                <Label htmlFor="email">Work email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(event) => update("email", event.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                  placeholder="you@company.com"
                />
              </div>
              <div>
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(event) => update("password", event.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                  placeholder="At least 8 characters"
                />
              </div>
              <div>
                <Label htmlFor="organization">Organization</Label>
                <Input
                  id="organization"
                  value={form.organizationName}
                  onChange={(event) => update("organizationName", event.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                  placeholder="iCog Labs"
                />
              </div>
              <div>
                <Label htmlFor="workspace">Workspace name</Label>
                <Input
                  id="workspace"
                  value={form.workspaceName}
                  onChange={(event) => update("workspaceName", event.target.value)}
                  className="mt-1.5 h-11 rounded-xl"
                  placeholder="Research Ops"
                />
              </div>
              <Button
                type="submit"
                className="w-full rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Creating account..." : "Create account"}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>

            <div className="mt-6 text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="text-accent hover:underline">
                Sign in
              </Link>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="relative hidden min-h-screen overflow-hidden bg-white lg:flex lg:items-center lg:justify-center">
        <div className="absolute inset-0 bg-gradient-to-br from-white via-white to-emerald-50/70" />
        <div className="relative flex h-full w-full items-center justify-center p-12">
          <img
            src={heroVisual}
            alt="Grounded AI visual"
            className="h-full max-h-[760px] w-full max-w-[760px] object-contain"
          />
        </div>
      </div>
    </div>
  );
}
