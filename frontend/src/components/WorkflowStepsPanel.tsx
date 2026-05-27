import { Check, X, ZoomIn, ZoomOut, Move } from "lucide-react";
import type { WorkflowStep, WorkflowStepId } from "@/lib/types";

const STEP_ORDER: WorkflowStepId[] = [
  "init",
  "conversation_history",
  "check_retrieval",
  "research",
  "generate",
];

const STEP_LABELS: Record<WorkflowStepId, string> = {
  init: "Workflow Steps",
  conversation_history: "Create Message History",
  check_retrieval: "Check Retrieval Need",
  research: "Research",
  generate: "Generate",
};

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms}ms`;
}

function StepNode({
  step,
  isActive,
}: {
  step: WorkflowStep;
  isActive: boolean;
}) {
  const isCompleted = step.status === "completed";
  const isRunning = step.status === "running";

  return (
    <div
      className={`relative flex min-w-[140px] flex-col items-center gap-2 rounded-2xl border p-4 transition-all ${
        isRunning
          ? "border-blue-400 bg-white shadow-[0_0_0_2px_rgba(96,165,250,0.4)]"
          : isCompleted
            ? "border-border bg-white/90"
            : "border-border/50 bg-white/50 opacity-50"
      }`}
    >
      {isRunning && (
        <span className="absolute -top-1.5 -right-1.5 h-3 w-3 rounded-full bg-blue-400">
          <span className="absolute inset-0 animate-ping rounded-full bg-blue-400/60" />
        </span>
      )}

      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full border ${
          isRunning
            ? "border-blue-300 bg-blue-50"
            : isCompleted
              ? "border-emerald-200 bg-emerald-50"
              : "border-border bg-background"
        }`}
      >
        {isRunning ? (
          <svg
            className="h-4 w-4 animate-spin text-blue-400"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        ) : isCompleted ? (
          <Check className="h-3.5 w-3.5 text-emerald-600" />
        ) : (
          <div className="h-2 w-2 rounded-full bg-border" />
        )}
      </div>

      <span className="text-center text-[11px] font-medium leading-tight text-foreground">
        {STEP_LABELS[step.step] ?? step.label}
      </span>

      {isCompleted && step.durationMs !== undefined && (
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground">
          {formatMs(step.durationMs)}
        </span>
      )}

      {isRunning && (
        <span className="text-[10px] text-blue-400">
          running…
        </span>
      )}

      {step.metadata?.evidence_count !== undefined && isCompleted && (
        <span className="text-[10px] text-muted-foreground">
          {String(step.metadata.evidence_count)} evidence
        </span>
      )}
      {step.metadata?.message_count !== undefined &&
        Number(step.metadata.message_count) > 0 &&
        isCompleted && (
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-accent/20 text-[9px] font-semibold text-accent">
            {String(step.metadata.message_count)}
          </span>
        )}
    </div>
  );
}

function Arrow({ dashed = false }: { dashed?: boolean }) {
  return (
    <div className="flex items-center px-1">
      <svg width="32" height="16" viewBox="0 0 32 16" fill="none">
        <line
          x1="0"
          y1="8"
          x2="24"
          y2="8"
          stroke={dashed ? "#cbd5e1" : "#94a3b8"}
          strokeWidth="1.5"
          strokeDasharray={dashed ? "4 3" : undefined}
        />
        <path d="M20 4 L26 8 L20 12" stroke={dashed ? "#cbd5e1" : "#94a3b8"} strokeWidth="1.5" fill="none" />
      </svg>
    </div>
  );
}

function DownArrow() {
  return (
    <div className="flex justify-center py-1">
      <svg width="16" height="28" viewBox="0 0 16 28" fill="none">
        <line x1="8" y1="0" x2="8" y2="22" stroke="#94a3b8" strokeWidth="1.5" />
        <path d="M4 18 L8 24 L12 18" stroke="#94a3b8" strokeWidth="1.5" fill="none" />
      </svg>
    </div>
  );
}

interface WorkflowStepsPanelProps {
  steps: WorkflowStep[];
  onClose?: () => void;
}

export default function WorkflowStepsPanel({ steps, onClose }: WorkflowStepsPanelProps) {
  const byId = Object.fromEntries(steps.map((s) => [s.step, s])) as Record<WorkflowStepId, WorkflowStep | undefined>;

  const getStep = (id: WorkflowStepId): WorkflowStep => {
    return (
      byId[id] ?? {
        step: id,
        label: STEP_LABELS[id],
        status: "idle",
      }
    );
  };

  const init = getStep("init");
  const convHistory = getStep("conversation_history");
  const checkRetrieval = getStep("check_retrieval");
  const research = getStep("research");
  const generate = getStep("generate");

  const activeStep = steps.find((s) => s.status === "running")?.step ?? null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-muted-foreground">
            <circle cx="3" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="13" cy="3" r="2" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="13" cy="13" r="2" stroke="currentColor" strokeWidth="1.5" />
            <line x1="5" y1="8" x2="11" y2="4" stroke="currentColor" strokeWidth="1.5" />
            <line x1="5" y1="8" x2="11" y2="12" stroke="currentColor" strokeWidth="1.5" />
          </svg>
          <span className="text-sm font-semibold text-foreground">Workflow Steps</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:text-foreground"
            title="Zoom in"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:text-foreground"
            title="Zoom out"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:text-foreground"
            title="Pan"
          >
            <Move className="h-3.5 w-3.5" />
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="ml-1 rounded p-1 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center overflow-auto p-6">
        <div className="flex flex-col gap-0">
          {/* Main horizontal flow: init → conv_history → research → generate */}
          <div className="flex items-start gap-0">
            <StepNode step={init} isActive={activeStep === "init"} />
            <Arrow dashed={init.status !== "completed"} />
            <StepNode step={convHistory} isActive={activeStep === "conversation_history"} />
            <Arrow dashed={convHistory.status !== "completed"} />
            <StepNode step={research} isActive={activeStep === "research"} />
            <Arrow dashed={research.status !== "completed"} />
            <StepNode step={generate} isActive={activeStep === "generate"} />
          </div>

          {/* check_retrieval branch: hangs below conv_history */}
          <div className="ml-[calc(140px+32px+140px/2-8px)] flex flex-col items-center" style={{ marginLeft: "calc(140px + 48px + 70px - 8px)" }}>
            <DownArrow />
            <StepNode step={checkRetrieval} isActive={activeStep === "check_retrieval"} />
          </div>
        </div>
      </div>
    </div>
  );
}
