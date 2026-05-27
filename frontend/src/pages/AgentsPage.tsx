import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Bot, Database, Plus, Search, Zap } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { createAgent, getCapabilities, listAgents, listDatasets } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { workspacePath } from "@/lib/routes";
import type { ModeCapabilityResponse, UserFacingMode } from "@/lib/types";

const FALLBACK_MODE_OPTIONS: ModeCapabilityResponse[] = [
  {
    mode: "auto",
    label: "Auto",
    enabled: true,
    backing_tier: null,
    description: "Recommended mode that follows the current Standard path.",
    availability_reason: null,
  },
  {
    mode: "instant",
    label: "Instant",
    enabled: true,
    backing_tier: "standard",
    description: "Fast grounded answers for everyday document questions.",
    availability_reason: null,
  },
  {
    mode: "thinking",
    label: "Thinking",
    enabled: true,
    backing_tier: "enterprise",
    description: "Deeper retrieval for harder questions.",
    availability_reason: null,
  },
  {
    mode: "verified",
    label: "Verified",
    enabled: true,
    backing_tier: "critical",
    description: "Highest-assurance path for sensitive work.",
    availability_reason: null,
  },
];

export default function AgentsPage() {
  const { apiKey, workspaceId, workspaceSlug } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    systemInstructions: "",
    defaultMode: "auto" as UserFacingMode,
  });

  const agentsQuery = useQuery({
    queryKey: ["agents", workspaceId],
    queryFn: () => listAgents(apiKey!, workspaceId),
    enabled: Boolean(apiKey && workspaceId),
  });

  const datasetsQuery = useQuery({
    queryKey: ["datasets", workspaceId],
    queryFn: () => listDatasets(apiKey!, workspaceId),
    enabled: Boolean(apiKey && workspaceId),
  });

  const capabilitiesQuery = useQuery({
    queryKey: ["capabilities"],
    queryFn: () => getCapabilities(apiKey!),
    enabled: Boolean(apiKey),
  });

  const createModeOptions = useMemo(
    () => capabilitiesQuery.data?.modes ?? FALLBACK_MODE_OPTIONS,
    [capabilitiesQuery.data?.modes],
  );

  const enabledCreateModes = useMemo(
    () => createModeOptions.filter((mode) => mode.enabled).map((mode) => mode.mode),
    [createModeOptions],
  );

  useEffect(() => {
    if (
      enabledCreateModes.length > 0 &&
      !enabledCreateModes.includes(form.defaultMode)
    ) {
      setForm((current) => ({ ...current, defaultMode: enabledCreateModes[0] }));
    }
  }, [enabledCreateModes, form.defaultMode]);

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey || !workspaceId) {
        throw new Error("Create a workspace before creating agents.");
      }

      return createAgent(apiKey, {
        workspace_id: workspaceId,
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        system_instructions: form.systemInstructions.trim() || undefined,
        default_mode: form.defaultMode,
        allowed_modes: enabledCreateModes,
      });
    },
    onSuccess: (agent) => {
      toast.success("Agent created.");
      setForm({
        name: "",
        description: "",
        systemInstructions: "",
        defaultMode: "auto",
      });
      setShowCreateForm(false);
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(workspacePath(workspaceSlug, `/agents/${agent.agent_id}`));
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to create the agent.";
      toast.error(message);
    },
  });

  const datasetsById = useMemo(
    () =>
      new Map((datasetsQuery.data ?? []).map((dataset) => [dataset.dataset_id, dataset.name])),
    [datasetsQuery.data],
  );

  const filteredAgents = useMemo(() => {
    const agents = agentsQuery.data ?? [];
    const value = search.trim().toLowerCase();
    if (!value) return agents;
    return agents.filter((agent) =>
      [agent.name, agent.description ?? ""].some((field) => field.toLowerCase().includes(value)),
    );
  }, [agentsQuery.data, search]);

  if (!workspaceId) {
    return (
      <div className="max-w-3xl">
        <div className="rounded-2xl border bg-card p-10 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <Bot className="h-7 w-7 text-muted-foreground" />
          </div>
          <h1 className="text-xl font-semibold text-foreground mb-2">Create a workspace first</h1>
          <p className="text-sm text-muted-foreground mb-6">
            Agents belong to a workspace and depend on datasets inside that workspace.
          </p>
          <Link to="/onboarding">
            <Button className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
              Continue onboarding
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Build agents that reason over your datasets with grounded answers and inspectable runs.
          </p>
        </div>
        <Button variant="pill-accent" size="sm" onClick={() => setShowCreateForm((current) => !current)}>
          <Plus className="h-3.5 w-3.5 mr-1" /> {showCreateForm ? "Hide form" : "Create agent"}
        </Button>
      </div>

      {showCreateForm && (
        <div className="rounded-2xl border bg-card p-6 mb-6">
          <h2 className="text-sm font-semibold text-foreground mb-4">Create an agent</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="agent-name">Name</Label>
              <Input
                id="agent-name"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Policy Analyst"
                className="mt-1.5 h-11 rounded-xl"
              />
            </div>
            <div>
              <Label htmlFor="agent-mode">Default mode</Label>
              <div className="flex items-center gap-2 mt-1.5">
                {createModeOptions.map((mode) => (
                  <Button
                    key={mode.mode}
                    type="button"
                    variant={form.defaultMode === mode.mode ? "pill-accent" : "outline"}
                    size="sm"
                    className="rounded-full"
                    onClick={() => mode.enabled && setForm((current) => ({ ...current, defaultMode: mode.mode }))}
                    disabled={!mode.enabled}
                    title={mode.description}
                  >
                    {mode.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <div>
              <Label htmlFor="agent-description">Description</Label>
              <Textarea
                id="agent-description"
                value={form.description}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Answers questions about policy with citations."
                className="mt-1.5 min-h-28 rounded-xl"
              />
            </div>
            <div>
              <Label htmlFor="agent-system">System instructions</Label>
              <Textarea
                id="agent-system"
                value={form.systemInstructions}
                onChange={(event) => setForm((current) => ({ ...current, systemInstructions: event.target.value }))}
                placeholder="Prefer concise grounded answers and cite evidence."
                className="mt-1.5 min-h-28 rounded-xl"
              />
            </div>
          </div>
          {(datasetsQuery.data?.length ?? 0) === 0 ? (
            <div className="mt-4 rounded-xl border bg-secondary/40 px-4 py-3 text-sm text-muted-foreground">
              Create a dataset first, then attach it from the agent detail page.
            </div>
          ) : null}
          <div className="flex justify-end mt-4">
            <Button
              variant="pill-accent"
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={!form.name.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create agent"}
            </Button>
          </div>
        </div>
      )}

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="pl-10 h-10 rounded-xl"
        />
      </div>

      {agentsQuery.isLoading ? (
        <div className="grid md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-52 rounded-2xl border bg-card animate-pulse" />
          ))}
        </div>
      ) : filteredAgents.length === 0 ? (
        <div className="rounded-2xl border bg-card p-12 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <Bot className="h-7 w-7 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No agents yet</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
            Create an agent and attach datasets to start grounded conversations backed by your own data.
          </p>
          <Button variant="pill-accent" onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-1" /> Create your first agent
          </Button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {filteredAgents.map((agent, index) => {
            const datasetNames = agent.dataset_ids
              .map((datasetId) => datasetsById.get(datasetId))
              .filter(Boolean) as string[];

            return (
              <motion.div
                key={agent.agent_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Link to={workspacePath(workspaceSlug, `/agents/${agent.agent_id}`)} className="block rounded-2xl border bg-card p-5 hover-lift group">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center">
                        <Bot className="h-5 w-5 text-accent" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-foreground group-hover:text-accent transition-colors">
                          {agent.name}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          {agent.description || "Grounded agent ready for workspace questions."}
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
                  </div>
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <Badge variant="accent" className="text-[10px]">
                      <Zap className="h-2.5 w-2.5 mr-0.5" /> {agent.default_mode}
                    </Badge>
                    {(datasetNames.length > 0 ? datasetNames : ["No datasets attached"]).map((datasetName) => (
                      <Badge key={datasetName} variant="outline" className="text-[10px]">
                        <Database className="h-2.5 w-2.5 mr-0.5" /> {datasetName}
                      </Badge>
                    ))}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Updated {formatDateTime(agent.updated_at)}
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
