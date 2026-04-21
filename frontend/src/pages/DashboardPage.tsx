import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock,
  Database,
  FileSearch,
  Leaf,
  Upload,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getCapabilities,
  getDashboardRecentJobs,
  getDashboardRecentRuns,
  getDashboardSummary,
  listAgents,
  listDatasets,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatRelativeOrDate, sentenceCase } from "@/lib/format";
import { workspacePath } from "@/lib/routes";
import { confidenceBadgeVariant, confidenceLabelText } from "@/lib/trust";
import type { ModeCapabilityResponse } from "@/lib/types";

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
    enabled: false,
    backing_tier: "enterprise",
    description: "Deeper retrieval for harder questions.",
    availability_reason: "coming_soon",
  },
  {
    mode: "verified",
    label: "Verified",
    enabled: false,
    backing_tier: "critical",
    description: "Highest-assurance path for sensitive work.",
    availability_reason: "coming_soon",
  },
];

function WelcomeHero({
  workspaceName,
  workspaceSlug,
}: {
  workspaceName: string | null;
  workspaceSlug: string | null;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border bg-card p-8 mb-8 relative overflow-hidden"
    >
      <div className="absolute top-0 right-0 h-64 w-64 rounded-full bg-accent/5 blur-[80px]" />
      <div className="relative">
        <Badge variant="accent" className="mb-4">
          Grounded Workspace
        </Badge>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-3">
          Ground your agents in real evidence.
        </h1>
        <p className="text-muted-foreground max-w-2xl mb-6 leading-relaxed">
          {workspaceName ? `${workspaceName} is ready for grounded work.` : "Your workspace is ready."} Build
          agents on top of your datasets, reduce hallucination through evidence and citations, and resolve
          ambiguity with tiered execution.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to={workspacePath(workspaceSlug, "/datasets")}>
            <Button className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90 shadow-glow" size="sm">
              <Database className="h-3.5 w-3.5 mr-1" /> Create dataset
            </Button>
          </Link>
          <Link to={workspacePath(workspaceSlug, "/agents")}>
            <Button variant="outline" className="rounded-full" size="sm">
              <Bot className="h-3.5 w-3.5 mr-1" /> Create agent
            </Button>
          </Link>
          <Link to={workspacePath(workspaceSlug, "/datasets")}>
            <Button variant="outline" className="rounded-full" size="sm">
              <Upload className="h-3.5 w-3.5 mr-1" /> Upload documents
            </Button>
          </Link>
        </div>
      </div>
    </motion.div>
  );
}

function ModeStatusCard({ modes }: { modes: ModeCapabilityResponse[] }) {
  const liveTier = modes.some((mode) => mode.mode === "thinking" && mode.enabled)
    ? "Enterprise"
    : "Standard";

  return (
    <div className="rounded-2xl border bg-card p-6">
      <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
        <Zap className="h-4 w-4 text-accent" /> Product Status
      </h3>
      <div className="space-y-3">
        <div className="rounded-xl border bg-secondary/30 px-3 py-2">
          <div className="text-xs text-muted-foreground">Live tier</div>
          <div className="text-sm font-medium text-foreground">{liveTier}</div>
        </div>
        {modes.map((mode) => (
          <div key={mode.mode} className="flex items-center justify-between gap-3">
            <div>
              <span className="text-sm font-medium text-foreground">{mode.label}</span>
              <p className="text-xs text-muted-foreground">{mode.description}</p>
            </div>
            {mode.enabled ? (
              <Badge variant="success" className="text-[10px]">
                <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" /> Live
              </Badge>
            ) : (
              <Badge variant="coming" className="text-[10px]">
                Coming soon
              </Badge>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function StatsCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  sub: string;
}) {
  return (
    <div className="rounded-2xl border bg-card p-5 hover-lift">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-9 w-9 rounded-xl bg-accent/10 flex items-center justify-center">
          <Icon className="h-4 w-4 text-accent" />
        </div>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      <p className="text-xs text-muted-foreground mt-1">{sub}</p>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  desc,
  actionLabel,
  to,
}: {
  icon: LucideIcon;
  title: string;
  desc: string;
  actionLabel: string;
  to: string;
}) {
  return (
    <div className="rounded-2xl border bg-card p-8 text-center">
      <div className="h-12 w-12 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground mb-4 max-w-xs mx-auto">{desc}</p>
      <Link to={to}>
        <Button variant="outline" className="rounded-full" size="sm">
          {actionLabel}
        </Button>
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const { apiKey, workspaceId, workspaceName, workspaceSlug } = useAuth();

  const summaryQuery = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => getDashboardSummary(apiKey!),
    enabled: Boolean(apiKey),
  });

  const recentRunsQuery = useQuery({
    queryKey: ["dashboard", "recent-runs"],
    queryFn: () => getDashboardRecentRuns(apiKey!),
    enabled: Boolean(apiKey),
  });

  const recentJobsQuery = useQuery({
    queryKey: ["dashboard", "recent-jobs"],
    queryFn: () => getDashboardRecentJobs(apiKey!),
    enabled: Boolean(apiKey),
  });

  const datasetsQuery = useQuery({
    queryKey: ["datasets", workspaceId],
    queryFn: () => listDatasets(apiKey!, workspaceId),
    enabled: Boolean(apiKey && workspaceId),
  });

  const agentsQuery = useQuery({
    queryKey: ["agents", workspaceId],
    queryFn: () => listAgents(apiKey!, workspaceId),
    enabled: Boolean(apiKey && workspaceId),
  });

  const capabilitiesQuery = useQuery({
    queryKey: ["capabilities"],
    queryFn: () => getCapabilities(apiKey!),
    enabled: Boolean(apiKey),
  });

  if (!workspaceId) {
    return (
      <div className="max-w-3xl">
        <div className="rounded-2xl border bg-card p-10 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <Leaf className="h-7 w-7 text-muted-foreground" />
          </div>
          <h1 className="text-xl font-semibold text-foreground mb-2">Create a workspace to continue</h1>
          <p className="text-sm text-muted-foreground mb-6 max-w-xl mx-auto">
            Your API key is valid, but this tenant does not have a workspace yet. Complete onboarding to create one
            and unlock datasets, agents, and grounded runs.
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

  if (summaryQuery.isLoading || datasetsQuery.isLoading || agentsQuery.isLoading) {
    return (
      <div className="max-w-6xl space-y-6">
        <div className="h-48 rounded-2xl border bg-card animate-pulse" />
        <div className="grid md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-28 rounded-2xl border bg-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const summary = summaryQuery.data;
  const agents = agentsQuery.data ?? [];
  const datasets = datasetsQuery.data ?? [];
  const recentRuns = recentRunsQuery.data ?? [];
  const recentJobs = recentJobsQuery.data ?? [];
  const modeCapabilities = capabilitiesQuery.data?.modes ?? FALLBACK_MODE_OPTIONS;

  return (
    <div className="max-w-6xl">
      <WelcomeHero workspaceName={workspaceName} workspaceSlug={workspaceSlug} />

      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <StatsCard icon={Database} label="Datasets" value={summary?.dataset_count ?? 0} sub="Source-of-truth collections" />
        <StatsCard icon={Bot} label="Agents" value={summary?.agent_count ?? 0} sub="Grounded assistants in this workspace" />
        <StatsCard icon={Activity} label="Runs" value={recentRuns.length} sub="Recent answer executions" />
        <StatsCard
          icon={FileSearch}
          label="Documents"
          value={summary?.document_count ?? 0}
          sub={`${summary?.indexed_document_count ?? 0} indexed and ready`}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-foreground mb-4">Recent Runs</h3>
          {recentRuns.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="No runs yet"
              desc="Runs appear when an agent answers a question. Each run includes the grounded answer, citations, and trust signals."
              actionLabel="Open agents"
              to={workspacePath(workspaceSlug, "/agents")}
            />
          ) : (
            <div className="rounded-2xl border bg-card divide-y">
              {recentRuns.slice(0, 4).map((run) => (
                <Link
                  key={run.run_id}
                  to={workspacePath(workspaceSlug, "/runs")}
                  className="block px-5 py-4 transition-colors hover:bg-secondary/30"
                >
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <p className="text-sm font-medium text-foreground">{run.query}</p>
                    <Badge variant="accent" className="text-[10px]">
                      {run.selected_mode ?? "auto"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="text-[10px]">
                      {sentenceCase(run.effective_tier)}
                    </Badge>
                    <Badge variant={run.verification_status === "passed" ? "success" : "warning"} className="text-[10px]">
                      {sentenceCase(run.verification_status)}
                    </Badge>
                    <Badge variant={confidenceBadgeVariant(run.confidence_label)} className="text-[10px]">
                      {confidenceLabelText(run.confidence_label)}
                    </Badge>
                    <span className="text-xs text-muted-foreground ml-auto">{formatRelativeOrDate(run.created_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        <ModeStatusCard modes={modeCapabilities} />
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-foreground">Agents</h3>
            <Link to={workspacePath(workspaceSlug, "/agents")} className="text-xs text-accent hover:underline">
              View all
            </Link>
          </div>
          {agents.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="No agents yet"
              desc="Create an agent, attach datasets, and start running grounded conversations backed by your documents."
              actionLabel="Create agent"
              to={workspacePath(workspaceSlug, "/agents")}
            />
          ) : (
            <div className="rounded-2xl border bg-card divide-y">
              {agents.slice(0, 3).map((agent) => (
                <Link
                  key={agent.agent_id}
                  to={workspacePath(workspaceSlug, `/agents/${agent.agent_id}`)}
                  className="block px-5 py-4 transition-colors hover:bg-secondary/30"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="text-sm font-medium text-foreground">{agent.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {agent.description || "Grounded agent ready for workspace questions."}
                      </div>
                    </div>
                    <Badge variant="outline" className="text-[10px]">
                      {agent.default_mode}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {agent.dataset_ids.length} dataset{agent.dataset_ids.length === 1 ? "" : "s"} attached
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-foreground">Datasets</h3>
            <Link to={workspacePath(workspaceSlug, "/datasets")} className="text-xs text-accent hover:underline">
              View all
            </Link>
          </div>
          {datasets.length === 0 ? (
            <EmptyState
              icon={Database}
              title="No datasets yet"
              desc="Create a dataset and upload source files so Grounded has evidence to reason over."
              actionLabel="Create dataset"
              to={workspacePath(workspaceSlug, "/datasets")}
            />
          ) : (
            <div className="rounded-2xl border bg-card divide-y">
              {datasets.slice(0, 3).map((dataset) => (
                <Link
                  key={dataset.dataset_id}
                  to={workspacePath(workspaceSlug, `/datasets/${dataset.dataset_id}`)}
                  className="block px-5 py-4 transition-colors hover:bg-secondary/30"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="text-sm font-medium text-foreground">{dataset.name}</div>
                      <div className="text-xs text-muted-foreground">{sentenceCase(dataset.domain)}</div>
                    </div>
                    <Badge variant="outline" className="text-[10px]">
                      {sentenceCase(dataset.min_execution_tier)}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Created {formatDateTime(dataset.created_at)}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-4">Recent Jobs</h3>
          {recentJobs.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="No ingestion jobs yet"
              desc="Upload files into a dataset to track ingestion, indexing, and readiness."
              actionLabel="Open datasets"
              to={workspacePath(workspaceSlug, "/datasets")}
            />
          ) : (
            <div className="rounded-2xl border bg-card divide-y">
              {recentJobs.slice(0, 4).map((job) => (
                <Link
                  key={job.job_id}
                  to={workspacePath(workspaceSlug, `/datasets/${job.dataset_id}`)}
                  className="block px-5 py-4 transition-colors hover:bg-secondary/30"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-foreground">{job.document_title || "Untitled document"}</div>
                      <div className="text-xs text-muted-foreground">{formatRelativeOrDate(job.created_at)}</div>
                    </div>
                    <Badge
                      variant={job.status === "indexed" ? "success" : job.status === "failed" ? "destructive" : "warning"}
                      className="text-[10px]"
                    >
                      {sentenceCase(job.status)}
                    </Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border bg-card p-6">
          <h3 className="text-sm font-semibold text-foreground mb-4">Why Grounded</h3>
          <div className="space-y-4 text-sm text-muted-foreground">
            <div>
              <div className="font-medium text-foreground mb-1">Reduce hallucination</div>
              Evidence-first answers with citations keep the product honest about what it can support.
            </div>
            <div>
              <div className="font-medium text-foreground mb-1">Resolve ambiguity</div>
              The mode model lets the product match the depth of retrieval to the difficulty of the question.
            </div>
            <div>
              <div className="font-medium text-foreground mb-1">Inspect every answer</div>
              Runs, citations, confidence, and degraded reasons make the system reviewable by default.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
