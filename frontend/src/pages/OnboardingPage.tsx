import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Leaf } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createWorkspace } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { workspacePath } from "@/lib/routes";

const steps = [
  { title: "About you", subtitle: "Tell us who will use this workspace." },
  { title: "Organization", subtitle: "Create the workspace shell for your team." },
  { title: "Your use case", subtitle: "Help Grounded tailor the product language." },
  { title: "Get started", subtitle: "Create the workspace and enter your dashboard." },
];

const industries = [
  "Financial Services",
  "Healthcare",
  "Legal",
  "Government",
  "Technology",
  "Consulting",
  "Manufacturing",
  "Other",
];

const useCases = [
  "Policy & compliance",
  "Technical documentation",
  "Internal knowledge base",
  "Legal research",
  "Customer support",
  "Research & analysis",
  "Other",
];

const teamSizes = ["Just me", "2–10", "11–50", "51–200", "200+"];

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const { apiKey, setWorkspace } = useAuth();
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    company: "",
    workspaceName: "",
    industry: "",
    role: "",
    useCase: "",
    teamSize: "",
  });

  const createWorkspaceMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey) {
        throw new Error("Missing API key session. Sign in again to continue.");
      }

      return createWorkspace(apiKey, {
        name: form.workspaceName.trim(),
        slug: slugify(form.workspaceName),
        description: [
          form.company && `Organization: ${form.company}`,
          form.useCase && `Use case: ${form.useCase}`,
          form.industry && `Industry: ${form.industry}`,
        ]
          .filter(Boolean)
          .join(" • "),
      });
    },
    onSuccess: (workspace) => {
      setWorkspace(workspace.workspace_id, workspace.name, workspace.slug);
      toast.success("Workspace created.");
      navigate(workspacePath(workspace.slug));
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to create the workspace.";
      toast.error(message);
    },
  });

  const update = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const canProceed = () => {
    if (step === 0) return Boolean(form.fullName && form.email);
    if (step === 1) return Boolean(form.company && form.workspaceName);
    if (step === 2) return Boolean(form.industry && form.useCase);
    return true;
  };

  const next = () => {
    if (step < 3) {
      setStep((current) => current + 1);
      return;
    }
    createWorkspaceMutation.mutate();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg"
      >
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="h-8 w-8 rounded-lg gradient-accent flex items-center justify-center">
            <Leaf className="h-4 w-4 text-accent-foreground" />
          </div>
          <span className="text-lg font-bold text-foreground">Grounded AI</span>
        </div>

        <div className="flex gap-2 mb-8">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`h-1 flex-1 rounded-full transition-colors ${index <= step ? "bg-accent" : "bg-border"}`}
            />
          ))}
        </div>

        <div className="rounded-2xl border bg-card p-8 shadow-elevated">
          <h2 className="text-xl font-bold text-foreground mb-1">{steps[step].title}</h2>
          <p className="text-sm text-muted-foreground mb-6">{steps[step].subtitle}</p>

          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {step === 0 && (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="fullName">Full name</Label>
                    <Input
                      id="fullName"
                      value={form.fullName}
                      onChange={(event) => update("fullName", event.target.value)}
                      placeholder="Jane Smith"
                      className="mt-1.5 h-11 rounded-xl"
                    />
                  </div>
                  <div>
                    <Label htmlFor="email">Work email</Label>
                    <Input
                      id="email"
                      value={form.email}
                      onChange={(event) => update("email", event.target.value)}
                      placeholder="jane@company.com"
                      type="email"
                      className="mt-1.5 h-11 rounded-xl"
                    />
                  </div>
                  <div>
                    <Label htmlFor="role">Role / Title</Label>
                    <Input
                      id="role"
                      value={form.role}
                      onChange={(event) => update("role", event.target.value)}
                      placeholder="VP of Compliance"
                      className="mt-1.5 h-11 rounded-xl"
                    />
                  </div>
                </div>
              )}

              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="company">Company / Organization</Label>
                    <Input
                      id="company"
                      value={form.company}
                      onChange={(event) => update("company", event.target.value)}
                      placeholder="Acme Corp"
                      className="mt-1.5 h-11 rounded-xl"
                    />
                  </div>
                  <div>
                    <Label htmlFor="workspaceName">Workspace name</Label>
                    <Input
                      id="workspaceName"
                      value={form.workspaceName}
                      onChange={(event) => update("workspaceName", event.target.value)}
                      placeholder="Acme Compliance"
                      className="mt-1.5 h-11 rounded-xl"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      This becomes the main workspace label inside the product shell.
                    </p>
                  </div>
                  <div>
                    <Label>Team size</Label>
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      {teamSizes.map((size) => (
                        <button
                          key={size}
                          type="button"
                          onClick={() => update("teamSize", size)}
                          className={`rounded-full px-4 py-2 border text-sm transition-all ${
                            form.teamSize === size
                              ? "bg-accent text-accent-foreground border-accent"
                              : "bg-background border-border text-foreground hover:bg-secondary"
                          }`}
                        >
                          {size}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-4">
                  <div>
                    <Label>Industry</Label>
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      {industries.map((industry) => (
                        <button
                          key={industry}
                          type="button"
                          onClick={() => update("industry", industry)}
                          className={`rounded-full px-4 py-2 border text-sm transition-all ${
                            form.industry === industry
                              ? "bg-accent text-accent-foreground border-accent"
                              : "bg-background border-border text-foreground hover:bg-secondary"
                          }`}
                        >
                          {industry}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label>Primary use case</Label>
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      {useCases.map((useCase) => (
                        <button
                          key={useCase}
                          type="button"
                          onClick={() => update("useCase", useCase)}
                          className={`rounded-full px-4 py-2 border text-sm transition-all ${
                            form.useCase === useCase
                              ? "bg-accent text-accent-foreground border-accent"
                              : "bg-background border-border text-foreground hover:bg-secondary"
                          }`}
                        >
                          {useCase}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="text-center py-4">
                  <div className="h-16 w-16 rounded-2xl gradient-accent flex items-center justify-center mx-auto mb-4 shadow-glow">
                    <Leaf className="h-8 w-8 text-accent-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">Your workspace is ready to be created</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Grounded will create <span className="font-medium text-foreground">{form.workspaceName || "your workspace"}</span>
                    {" "}so you can start building datasets, agents, and runs backed by your own knowledge.
                  </p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>

          <div className="flex gap-3 mt-8">
            {step > 0 && (
              <Button variant="outline" onClick={() => setStep((current) => current - 1)} className="rounded-xl">
                <ArrowLeft className="h-4 w-4 mr-1" /> Back
              </Button>
            )}
            <Button
              className="flex-1 rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
              onClick={next}
              disabled={!canProceed() || createWorkspaceMutation.isPending}
            >
              {step === 3
                ? createWorkspaceMutation.isPending
                  ? "Creating workspace..."
                  : "Enter workspace"
                : "Continue"}
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
