import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock,
  FileSearch,
  Search,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { listRuns, getRun } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatRelativeOrDate, sentenceCase } from "@/lib/format";
import {
  confidenceBadgeVariant,
  confidenceLabelText,
  degradedReasonDescription,
  providerDisplayText,
  supportSummaryText,
} from "@/lib/trust";

export default function RunsPage() {
  const { apiKey } = useAuth();
  const [search, setSearch] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const runsQuery = useQuery({
    queryKey: ["runs"],
    queryFn: () => listRuns(apiKey!),
    enabled: Boolean(apiKey),
  });

  const filteredRuns = useMemo(() => {
    const runs = runsQuery.data ?? [];
    const value = search.trim().toLowerCase();
    if (!value) return runs;
    return runs.filter((run) => run.query.toLowerCase().includes(value));
  }, [runsQuery.data, search]);

  useEffect(() => {
    const selectedStillVisible = filteredRuns.some((run) => run.run_id === selectedRunId);
    if ((!selectedRunId || !selectedStillVisible) && filteredRuns.length > 0) {
      setSelectedRunId(filteredRuns[0].run_id);
    }
  }, [filteredRuns, selectedRunId]);

  const selectedRunQuery = useQuery({
    queryKey: ["run", selectedRunId],
    queryFn: () => getRun(apiKey!, selectedRunId!),
    enabled: Boolean(apiKey && selectedRunId),
  });

  const selectedRun = selectedRunQuery.data;

  return (
    <div className="max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">Runs</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Inspect every grounded query, answer, and trace for trust and auditing.
        </p>
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search runs..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="pl-10 h-10 rounded-xl"
        />
      </div>

      {runsQuery.isLoading ? (
        <div className="grid lg:grid-cols-[420px_minmax(0,1fr)] gap-6">
          <div className="h-[520px] rounded-2xl border bg-card animate-pulse" />
          <div className="h-[520px] rounded-2xl border bg-card animate-pulse" />
        </div>
      ) : filteredRuns.length === 0 ? (
        <div className="rounded-2xl border bg-card p-12 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <Activity className="h-7 w-7 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No runs yet</h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            Runs are created when an agent answers a question. Each run captures the query, answer, citations, and routing details.
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[420px_minmax(0,1fr)] gap-6 items-start">
          <div className="rounded-2xl border bg-card overflow-hidden">
            <div className="divide-y max-h-[65vh] overflow-y-auto">
              {filteredRuns.map((run) => (
                <button
                  key={run.run_id}
                  type="button"
                  onClick={() => setSelectedRunId(run.run_id)}
                  className={`w-full text-left px-5 py-4 transition-colors ${
                    selectedRunId === run.run_id ? "bg-accent/10" : "hover:bg-secondary/30"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <p className="text-sm font-medium text-foreground">{run.query}</p>
                    <Badge variant="accent" className="text-[10px] shrink-0">
                      {run.selected_mode ?? "auto"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {run.agent_id ? (
                      <Badge variant="outline" className="text-[10px]">
                        <Bot className="h-2.5 w-2.5 mr-0.5" /> Agent run
                      </Badge>
                    ) : null}
                    <Badge variant="outline" className="text-[10px]">
                      {sentenceCase(run.effective_tier)}
                    </Badge>
                    <Badge variant={run.verification_status === "passed" ? "success" : "warning"} className="text-[10px]">
                      {run.verification_status === "passed" ? (
                        <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />
                      ) : null}
                      {sentenceCase(run.verification_status)}
                    </Badge>
                    <Badge variant={confidenceBadgeVariant(run.confidence_label)} className="text-[10px]">
                      {confidenceLabelText(run.confidence_label)}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground ml-auto flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5" /> {formatRelativeOrDate(run.created_at)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border bg-card p-6 min-h-[65vh]">
            {!selectedRun ? (
              <div className="text-sm text-muted-foreground">
                Select a run to inspect the grounded answer, routing, and citations.
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <Badge variant="accent" className="text-[10px]">
                      <Zap className="h-2.5 w-2.5 mr-0.5" /> {selectedRun.selected_mode ?? "auto"}
                    </Badge>
                    <Badge variant="outline" className="text-[10px]">
                      {sentenceCase(selectedRun.effective_tier)}
                    </Badge>
                    <Badge variant={selectedRun.verification_status === "passed" ? "success" : "warning"} className="text-[10px]">
                      {sentenceCase(selectedRun.verification_status)}
                    </Badge>
                    <Badge variant={confidenceBadgeVariant(selectedRun.confidence_label)} className="text-[10px]">
                      {confidenceLabelText(selectedRun.confidence_label)}
                    </Badge>
                  </div>
                  <h2 className="text-lg font-semibold text-foreground mb-2">{selectedRun.query}</h2>
                  <p className="text-sm text-muted-foreground">
                    Created {formatDateTime(selectedRun.created_at)} • {selectedRun.total_latency_ms} ms • Provider {providerDisplayText(selectedRun)}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-2">Answer</h3>
                  <div className="rounded-2xl border bg-secondary/30 px-5 py-4">
                    <p className="text-sm text-foreground whitespace-pre-line leading-relaxed">{selectedRun.answer}</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="rounded-2xl border bg-secondary/20 p-4">
                    <div className="text-xs text-muted-foreground mb-1">Confidence</div>
                    <div className="text-lg font-semibold text-foreground">
                      {Math.round(selectedRun.confidence_score * 100)}%
                    </div>
                    <div className="mt-2">
                      <Badge variant={confidenceBadgeVariant(selectedRun.confidence_label)} className="text-[10px]">
                        {confidenceLabelText(selectedRun.confidence_label)}
                      </Badge>
                    </div>
                  </div>
                  <div className="rounded-2xl border bg-secondary/20 p-4">
                    <div className="text-xs text-muted-foreground mb-1">Routing reason</div>
                    <div className="text-sm text-foreground">{selectedRun.routing_reason}</div>
                  </div>
                </div>

                <div className="rounded-2xl border bg-secondary/20 p-4">
                  <div className="text-xs text-muted-foreground mb-1">Support summary</div>
                  <div className="text-sm text-foreground">{supportSummaryText(selectedRun.support_summary)}</div>
                  {selectedRun.provider_fallback_used ? (
                    <div className="mt-2 text-xs text-muted-foreground">
                      Provider fallback used from {selectedRun.provider_fallback_from ?? "configured backend"}.
                    </div>
                  ) : null}
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Citations</h3>
                  {selectedRun.citations.length === 0 ? (
                    <div className="text-sm text-muted-foreground">No citations were returned for this run.</div>
                  ) : (
                    <div className="space-y-3">
                      {selectedRun.citations.map((citation) => (
                        <div key={citation.citation_id} className="rounded-2xl border bg-secondary/20 p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <FileSearch className="h-4 w-4 text-accent" />
                            <span className="text-sm font-medium text-foreground">{citation.citation_id}</span>
                          </div>
                          <p className="text-sm text-muted-foreground leading-relaxed">"{citation.quote}"</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {selectedRun.degraded_reasons.length > 0 ? (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-2">Degraded reasons</h3>
                    <div className="space-y-2">
                      {selectedRun.degraded_reasons.map((reason) => (
                        <div key={reason} className="rounded-2xl border border-amber-200/70 bg-amber-50/70 p-4">
                          <div className="text-sm font-medium text-amber-900">{sentenceCase(reason)}</div>
                          <div className="mt-1 text-sm leading-relaxed text-amber-800">
                            {degradedReasonDescription(reason)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
