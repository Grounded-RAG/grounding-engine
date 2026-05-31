import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Maximize2, Move, X, ZoomIn, ZoomOut } from "lucide-react";
import type { WorkflowStep, WorkflowStepId } from "@/lib/types";

const STEP_LABELS: Record<WorkflowStepId, string> = {
  init: "Initialize",
  conversation_history: "Load Context",
  check_retrieval: "Analyze Query",
  research: "Retrieve Evidence",
  generate: "Generate Answer",
};

const STEP_DESCRIPTIONS: Record<WorkflowStepId, string> = {
  init: "Pipeline started and configuration loaded",
  conversation_history: "Recent conversation history loaded and structured",
  check_retrieval: "Determined whether knowledge base retrieval is required",
  research: "Searched the vector index and packaged grounded evidence",
  generate: "Generated a grounded answer from the retrieved evidence",
};

const PIPELINE_ORDER: WorkflowStepId[] = [
  "init",
  "conversation_history",
  "check_retrieval",
  "research",
  "generate",
];

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms}ms`;
}

function StepNode({ step, isActive }: { step: WorkflowStep; isActive: boolean }) {
  const isCompleted = step.status === "completed";
  const isRunning = step.status === "running";

  return (
    <div
      className={`relative flex w-[130px] flex-col items-center gap-2 rounded-2xl border p-3 transition-all select-none ${
        isRunning
          ? "border-blue-400 bg-white shadow-[0_0_0_2px_rgba(96,165,250,0.4)]"
          : isCompleted
            ? "border-border bg-white/90"
            : "border-border/50 bg-white/50 opacity-40"
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
          <svg className="h-4 w-4 animate-spin text-blue-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : isCompleted ? (
          <Check className="h-3.5 w-3.5 text-emerald-600" />
        ) : (
          <div className="h-2 w-2 rounded-full bg-border" />
        )}
      </div>
      <span className="text-center text-[11px] font-semibold leading-tight text-foreground">
        {STEP_LABELS[step.step] ?? step.label}
      </span>
      {isCompleted && step.durationMs !== undefined && (
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground">
          {formatMs(step.durationMs)}
        </span>
      )}
      {isRunning && <span className="text-[10px] text-blue-400">running…</span>}
      {step.step === "research" && isCompleted && step.metadata?.evidence_count !== undefined && (
        <span className="text-[10px] text-muted-foreground">
          {String(step.metadata.evidence_count)} evidence
        </span>
      )}
    </div>
  );
}

function Arrow({ dashed = false }: { dashed?: boolean }) {
  return (
    <div className="flex shrink-0 items-center px-1">
      <svg width="32" height="16" viewBox="0 0 32 16" fill="none">
        <line x1="0" y1="8" x2="24" y2="8" stroke={dashed ? "#cbd5e1" : "#94a3b8"} strokeWidth="1.5" strokeDasharray={dashed ? "4 3" : undefined} />
        <path d="M20 4 L26 8 L20 12" stroke={dashed ? "#cbd5e1" : "#94a3b8"} strokeWidth="1.5" fill="none" />
      </svg>
    </div>
  );
}

interface WorkflowStepsPanelProps {
  steps: WorkflowStep[];
  onClose?: () => void;
}

export default function WorkflowStepsPanel({ steps, onClose }: WorkflowStepsPanelProps) {
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [panMode, setPanMode] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null);

  useEffect(() => {
    if (!onClose) return;
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const zoomIn = useCallback(() => setScale((s) => Math.min(+(s + 0.15).toFixed(2), 2.5)), []);
  const zoomOut = useCallback(() => setScale((s) => Math.max(+(s - 0.15).toFixed(2), 0.4)), []);
  const resetView = useCallback(() => { setScale(1); setTranslate({ x: 0, y: 0 }); }, []);
  const togglePan = useCallback(() => setPanMode((p) => !p), []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!panMode) return;
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startY: e.clientY, originX: translate.x, originY: translate.y };
  }, [panMode, translate]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragRef.current) return;
    setTranslate({
      x: dragRef.current.originX + (e.clientX - dragRef.current.startX),
      y: dragRef.current.originY + (e.clientY - dragRef.current.startY),
    });
  }, []);

  const handleMouseUp = useCallback(() => { dragRef.current = null; }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((s) => Math.min(Math.max(+(s + delta).toFixed(2), 0.4), 2.5));
  }, []);

  const byId = Object.fromEntries(steps.map((s) => [s.step, s])) as Record<WorkflowStepId, WorkflowStep | undefined>;

  const getStep = (id: WorkflowStepId): WorkflowStep =>
    byId[id] ?? { step: id, label: STEP_LABELS[id], status: "idle" };

  const activeStep = steps.find((s) => s.status === "running")?.step ?? null;
  const allSteps = PIPELINE_ORDER.map(getStep);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
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
          {scale !== 1 && (
            <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {Math.round(scale * 100)}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button type="button" onClick={zoomIn} className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground" title="Zoom in (scroll up)">
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={zoomOut} className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground" title="Zoom out (scroll down)">
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={togglePan}
            className={`rounded p-1 hover:bg-secondary hover:text-foreground ${panMode ? "bg-secondary text-foreground" : "text-muted-foreground"}`}
            title="Pan mode (drag to move)"
          >
            <Move className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={resetView} className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground" title="Reset view">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          {onClose && (
            <button type="button" onClick={onClose} className="ml-1 rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div
        className={`relative flex flex-1 overflow-hidden ${panMode ? "cursor-grab active:cursor-grabbing" : ""}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{ transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`, transformOrigin: "center center", transition: dragRef.current ? "none" : "transform 0.15s ease" }}
        >
          {/* Pipeline: two rows if needed, linear order */}
          <div className="flex flex-col items-center gap-0">
            {/* Row 1: Initialize → Load Context → Analyze Query */}
            <div className="flex items-center gap-0">
              {allSteps.slice(0, 3).map((step, i) => (
                <div key={step.step} className="flex items-center">
                  <StepNode step={step} isActive={activeStep === step.step} />
                  {i < 2 && <Arrow dashed={step.status !== "completed"} />}
                </div>
              ))}
            </div>

            {/* Connector from Analyze Query to Retrieve Evidence */}
            <div className="flex justify-end" style={{ width: "calc(3 * 130px + 2 * 48px)" }}>
              <div className="flex flex-col items-center" style={{ width: 130 }}>
                <svg width="16" height="32" viewBox="0 0 16 32" fill="none">
                  <line x1="8" y1="0" x2="8" y2="26" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray={allSteps[2].status !== "completed" ? "4 3" : undefined} />
                  <path d="M4 22 L8 28 L12 22" stroke="#94a3b8" strokeWidth="1.5" fill="none" />
                </svg>
              </div>
            </div>

            {/* Row 2: Retrieve Evidence → Generate Answer (right-aligned under Analyze Query) */}
            <div className="flex items-center justify-end gap-0" style={{ width: "calc(3 * 130px + 2 * 48px)" }}>
              {allSteps.slice(3).map((step, i) => (
                <div key={step.step} className="flex items-center">
                  {i > 0 && <Arrow dashed={allSteps[3].status !== "completed"} />}
                  <StepNode step={step} isActive={activeStep === step.step} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer: step descriptions */}
      <div className="border-t bg-secondary/30 px-4 py-2">
        <div className="grid grid-cols-5 gap-2">
          {PIPELINE_ORDER.map((id) => {
            const step = getStep(id);
            const isCompleted = step.status === "completed";
            const isRunning = step.status === "running";
            return (
              <div key={id} className="text-center">
                <div className={`mb-0.5 text-[10px] font-semibold ${isRunning ? "text-blue-500" : isCompleted ? "text-foreground" : "text-muted-foreground/40"}`}>
                  {STEP_LABELS[id]}
                </div>
                <div className="text-[9px] leading-tight text-muted-foreground/60">
                  {STEP_DESCRIPTIONS[id]}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
