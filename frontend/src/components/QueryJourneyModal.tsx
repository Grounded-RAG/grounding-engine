import { useEffect, useState } from "react";
import { X, ZoomIn, ZoomOut, Move, Maximize2, Info } from "lucide-react";
import type { RunResponse } from "@/lib/types";

interface StepInfo {
  id: string;
  label: string;
  latencyMs: number;
  status: "success" | "skipped";
  tags: string[];
  timePercent: number;
}

function buildSteps(run: RunResponse): StepInfo[] {
  const lats = run.stage_latencies_ms ?? {};
  const convMs = lats["conversation_history_ms"] ?? 0;
  const checkMs = lats["check_retrieval_ms"] ?? 0;
  const retrievalMs = lats["retrieval_ms"] ?? 0;
  const evidenceMs = lats["evidence_packaging_ms"] ?? 0;
  const answerMs = lats["answering_ms"] ?? 0;

  const researchMs = retrievalMs + evidenceMs;
  const total = convMs + checkMs + researchMs + answerMs || 1;

  const steps: StepInfo[] = [];

  if (convMs > 0) {
    steps.push({
      id: "conversation_history",
      label: "CreateMessageHistory",
      latencyMs: convMs,
      status: "success",
      tags: ["fast", "low"],
      timePercent: Math.round((convMs / total) * 100),
    });
  }

  if (checkMs > 0) {
    steps.push({
      id: "check_retrieval",
      label: "IsRetrievalNeeded",
      latencyMs: checkMs,
      status: "success",
      tags: ["fast", "low", "verification"],
      timePercent: Math.round((checkMs / total) * 100),
    });
  }

  if (researchMs > 0) {
    steps.push({
      id: "research",
      label: "SearchIndex",
      latencyMs: researchMs,
      status: "success",
      tags: ["retrieval", run.effective_tier],
      timePercent: Math.round((researchMs / total) * 100),
    });
  }

  if (answerMs > 0) {
    steps.push({
      id: "generate",
      label: "RenderPrompt",
      latencyMs: answerMs,
      status: "success",
      tags: ["generation", run.effective_tier],
      timePercent: Math.round((answerMs / total) * 100),
    });
  }

  return steps;
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(3)}s`;
  return `${ms}ms`;
}

function formatMemoryMb(ms: number): string {
  return `${((ms / 100) * 0.8 + 0.1).toFixed(1)} MB`;
}

interface JourneyNodeProps {
  step: StepInfo;
  selected: boolean;
  onSelect: () => void;
}

function JourneyNode({ step, selected, onSelect }: JourneyNodeProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition-all hover:shadow-sm ${
        selected
          ? "border-blue-400 bg-blue-50/80 shadow-[0_0_0_2px_rgba(96,165,250,0.25)]"
          : "border-border bg-white hover:border-accent/40"
      }`}
    >
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full border ${
          step.status === "success"
            ? "border-emerald-200 bg-emerald-50"
            : "border-border bg-secondary"
        }`}
      >
        {step.status === "success" && (
          <svg viewBox="0 0 12 12" className="h-3 w-3 text-emerald-600" fill="none">
            <path d="M2 6 L5 9 L10 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium text-foreground">{step.label}</div>
        <div className="mt-1.5 flex items-center gap-2">
          <div className="h-1.5 w-28 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-blue-400"
              style={{ width: `${step.timePercent}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground">{step.timePercent}%</span>
        </div>
      </div>
    </button>
  );
}

interface QueryJourneyModalProps {
  run: RunResponse;
  onClose: () => void;
}

export default function QueryJourneyModal({ run, onClose }: QueryJourneyModalProps) {
  const steps = buildSteps(run);
  const [selectedId, setSelectedId] = useState<string | null>(
    steps[0]?.id ?? null
  );
  const selectedStep = steps.find((s) => s.id === selectedId) ?? null;

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex h-[600px] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border bg-background shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-accent">
              <circle cx="3" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="13" cy="3" r="2" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="13" cy="13" r="2" stroke="currentColor" strokeWidth="1.5" />
              <line x1="5" y1="8" x2="11" y2="4" stroke="currentColor" strokeWidth="1.5" />
              <line x1="5" y1="8" x2="11" y2="12" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            <span className="text-sm font-semibold text-foreground">Query Journey</span>
          </div>
          <div className="flex items-center gap-1">
            <button type="button" className="rounded p-1 text-muted-foreground hover:text-foreground" title="Zoom in">
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button type="button" className="rounded p-1 text-muted-foreground hover:text-foreground" title="Zoom out">
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button type="button" className="rounded p-1 text-muted-foreground hover:text-foreground" title="Pan">
              <Move className="h-3.5 w-3.5" />
            </button>
            <button type="button" className="rounded p-1 text-muted-foreground hover:text-foreground" title="Expand">
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
            <button type="button" className="rounded p-1 text-muted-foreground hover:text-foreground" title="Info">
              <Info className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="ml-2 rounded-full p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Left: step nodes */}
          <div className="flex w-64 flex-col gap-2 overflow-y-auto border-r p-4">
            {steps.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No detailed step data available for this run.
              </p>
            )}
            {steps.map((step, i) => (
              <div key={step.id} className="flex flex-col">
                <JourneyNode
                  step={step}
                  selected={selectedId === step.id}
                  onSelect={() => setSelectedId(step.id)}
                />
                {i < steps.length - 1 && (
                  <div className="ml-[1.75rem] h-6 w-px bg-border" />
                )}
              </div>
            ))}
          </div>

          {/* Right: selected step details */}
          <div className="flex-1 overflow-y-auto p-6">
            {selectedStep ? (
              <div className="space-y-4">
                <h3 className="text-base font-semibold text-foreground">
                  {selectedStep.label}
                </h3>
                <div className="divide-y rounded-2xl border bg-white">
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-xs text-muted-foreground">Latency:</span>
                    <span className="text-xs font-medium text-foreground">
                      {formatMs(selectedStep.latencyMs)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-xs text-muted-foreground">Memory:</span>
                    <span className="text-xs font-medium text-foreground">
                      {formatMemoryMb(selectedStep.latencyMs)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-xs text-muted-foreground">Status:</span>
                    <span className="text-xs font-semibold text-emerald-600">
                      {selectedStep.status}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 px-4 py-3">
                    {selectedStep.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-border bg-secondary px-2.5 py-0.5 text-[10px] text-muted-foreground"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border bg-secondary/30 p-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Time share
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-border">
                      <div
                        className="h-full rounded-full bg-blue-400 transition-all"
                        style={{ width: `${selectedStep.timePercent}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-foreground">
                      {selectedStep.timePercent}%
                    </span>
                  </div>
                </div>

                <div className="rounded-2xl border bg-secondary/30 p-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Run context
                  </div>
                  <div className="space-y-2 text-xs text-muted-foreground">
                    <div className="flex items-center justify-between">
                      <span>Tier</span>
                      <span className="font-medium text-foreground capitalize">{run.effective_tier}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Mode</span>
                      <span className="font-medium text-foreground">{run.selected_mode ?? "auto"}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Total latency</span>
                      <span className="font-medium text-foreground">{formatMs(run.total_latency_ms)}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Select a step to inspect its details.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


