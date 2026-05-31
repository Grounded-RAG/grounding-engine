import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, X } from "lucide-react";
import type { FeedbackReason, FeedbackSubmission } from "@/lib/types";

const REASONS: { id: FeedbackReason; label: string }[] = [
  { id: "FAILS_TO_ANSWER", label: "Answer fails to address/answer the query" },
  { id: "HALLUCINATION", label: "Answer makes a claim that is not supported in the document (i.e., hallucination)" },
  { id: "IRRELEVANT_INFORMATION", label: "Answer contains irrelevant or unwanted information" },
  { id: "WRONG_CITATIONS", label: "Answer does not contain the correct citations" },
  { id: "PROSE_ERRORS", label: "Serious prose errors in answer (e.g., grammar, spelling, syntax)" },
  { id: "OTHER", label: "Other (please specify in feedback details)" },
];

interface FeedbackModalProps {
  runId: string;
  initialRating?: "positive" | "negative";
  onSubmit: (feedback: FeedbackSubmission) => Promise<void>;
  onClose: () => void;
}

export default function FeedbackModal({ initialRating = "negative", onSubmit, onClose }: FeedbackModalProps) {
  const [freeformText, setFreeformText] = useState("");
  const [selectedReasons, setSelectedReasons] = useState<Set<FeedbackReason>>(new Set());
  const [showSourceDoc, setShowSourceDoc] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const toggleReason = (id: FeedbackReason) => {
    setSelectedReasons((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onSubmit({
        rating: initialRating,
        reasons: Array.from(selectedReasons),
        freeform_text: freeformText.trim() || null,
      });
      setSubmitted(true);
      setTimeout(onClose, 1200);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-xl overflow-hidden rounded-2xl border bg-background shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold text-foreground">Help Us Improve</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          {submitted ? (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50">
                <svg viewBox="0 0 20 20" className="h-5 w-5 text-emerald-600" fill="none">
                  <path d="M4 10 L8 14 L16 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <p className="text-sm font-medium text-emerald-700">Thank you for your feedback!</p>
            </div>
          ) : (
            <>
              {/* Freeform section */}
              <div className="mb-5">
                <label className="mb-2 block text-sm font-medium text-foreground">
                  Freeform Feedback
                </label>
                <textarea
                  className="w-full resize-none rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-accent/60 focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
                  rows={3}
                  placeholder="What could be changed?"
                  value={freeformText}
                  onChange={(e) => setFreeformText(e.target.value)}
                />
              </div>

              {/* OR divider */}
              <div className="relative mb-5 flex items-center gap-3">
                <div className="h-px flex-1 border-t border-dashed border-border" />
                <span className="shrink-0 text-xs font-medium text-muted-foreground">OR</span>
                <div className="h-px flex-1 border-t border-dashed border-border" />
              </div>

              {/* Reasons */}
              <div className="mb-5">
                <p className="mb-3 text-sm font-medium text-foreground">Reasons</p>
                <div className="grid grid-cols-2 gap-2">
                  {REASONS.map((reason) => {
                    const checked = selectedReasons.has(reason.id);
                    return (
                      <button
                        key={reason.id}
                        type="button"
                        onClick={() => toggleReason(reason.id)}
                        className={`flex items-start gap-3 rounded-xl border px-3 py-3 text-left text-sm transition-all ${
                          checked
                            ? "border-accent/40 bg-accent/5"
                            : "border-border bg-background hover:border-border/80 hover:bg-secondary/40"
                        }`}
                      >
                        <div className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                          checked ? "border-accent bg-accent" : "border-muted-foreground/40"
                        }`}>
                          {checked && (
                            <svg viewBox="0 0 8 8" className="h-2 w-2 text-white" fill="none">
                              <circle cx="4" cy="4" r="2" fill="currentColor" />
                            </svg>
                          )}
                        </div>
                        <span className="leading-snug text-foreground">{reason.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Correct Source Document (collapsible) */}
              <div className="border-t pt-4">
                <button
                  type="button"
                  onClick={() => setShowSourceDoc((p) => !p)}
                  className="flex w-full items-center justify-between text-sm font-medium text-foreground"
                >
                  <span>Correct Source Document</span>
                  {showSourceDoc ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </button>
                {showSourceDoc && (
                  <textarea
                    className="mt-3 w-full resize-none rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-accent/60 focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
                    rows={3}
                    placeholder="Paste or describe the correct source document..."
                  />
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {!submitted && (
          <div className="flex items-center justify-between border-t px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border bg-background px-5 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="rounded-xl bg-foreground px-6 py-2 text-sm font-semibold text-background hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {submitting ? "Submitting…" : "Submit"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
