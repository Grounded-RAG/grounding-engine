import type { ConfidenceLabel, SupportSummary } from "@/lib/types";

export function confidenceBadgeVariant(label: ConfidenceLabel): "success" | "warning" | "outline" {
  if (label === "high") return "success";
  if (label === "medium") return "warning";
  return "outline";
}

export function confidenceLabelText(label: ConfidenceLabel): string {
  if (label === "high") return "High confidence";
  if (label === "medium") return "Medium confidence";
  return "Low confidence";
}

export function supportSummaryText(summary: SupportSummary): string {
  if (summary === "grounded") return "Well-supported by retrieved evidence";
  if (summary === "partial") return "Partially supported; review citations";
  return "Insufficient support for a strong grounded answer";
}

export function providerDisplayText(run: {
  provider_backend: string;
  provider_model: string | null;
  provider_fallback_used: boolean;
  provider_fallback_from: string | null;
  generator_provider: string;
}): string {
  const base =
    run.provider_backend === "gemini_v1"
      ? `Gemini${run.provider_model ? ` (${run.provider_model})` : ""}`
      : run.provider_backend === "openai_compatible_v1"
        ? `OpenAI-compatible${run.provider_model ? ` (${run.provider_model})` : ""}`
        : run.provider_backend === "local_grounded_v1"
          ? "Local grounded generator"
          : run.provider_backend === "degraded_handler_v1"
            ? "Degraded response handler"
            : run.generator_provider;

  if (!run.provider_fallback_used) {
    return base;
  }

  return `${base} fallback from ${run.provider_fallback_from ?? "provider"}`;
}

export function degradedReasonDescription(reason: string): string {
  switch (reason) {
    case "NO_GROUNDED_EVIDENCE":
      return "No retrieved evidence supported the question.";
    case "INSUFFICIENT_SUPPORT":
      return "Related evidence existed, but not enough to answer confidently.";
    case "LOW_CONFIDENCE_SUPPORT":
      return "The answer used weak or limited evidence and should be reviewed.";
    case "QUERY_REQUIRES_CLARIFICATION":
      return "The question was too vague to ground reliably.";
    case "INSUFFICIENT_QUERY_ALIGNMENT":
      return "Retrieved evidence did not directly align with the question.";
    default:
      return reason.replaceAll("_", " ").toLowerCase();
  }
}
