export type ExecutionTier = "standard" | "enterprise" | "critical";
export type UserFacingMode = "auto" | "instant" | "thinking" | "verified";
export type VerificationStatus = "passed" | "degraded";
export type ConfidenceLabel = "low" | "medium" | "high";
export type SupportSummary = "grounded" | "partial" | "insufficient";
export type IngestionJobStatus = "queued" | "running" | "indexed" | "failed";
export type DocumentStatus = "uploaded" | "processing" | "indexed" | "failed";

export interface AuthSmokeResponse {
  status: string;
  tenant_id: string;
  tenant_name: string;
  subscription_plan: string;
  max_execution_tier: ExecutionTier;
  api_key_id: string;
  api_key_label: string;
}

export interface EmailAuthResponse extends AuthSmokeResponse {
  api_key: string;
  workspace_id: string | null;
  workspace_name: string | null;
  workspace_slug: string | null;
  created_tenant: boolean;
  created_workspace: boolean;
}

export interface WorkspaceResponse {
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetResponse {
  dataset_id: string;
  workspace_id: string | null;
  name: string;
  domain: string;
  sensitivity_level: string;
  freshness_profile: string;
  min_execution_tier: ExecutionTier;
  allow_web_fallback: boolean;
  allow_internal_model_retrieval: boolean;
  created_at: string;
}

export interface DatasetDocumentResponse {
  document_id: string;
  dataset_id: string;
  title: string | null;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  created_at: string;
}

export interface DatasetIngestionJobResponse {
  job_id: string;
  document_id: string;
  dataset_id: string;
  status: IngestionJobStatus;
  attempt_count: number;
  error_code: string | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DatasetUploadResponse {
  dataset_id: string;
  document_id: string;
  job_id: string;
  filename: string;
  title: string;
  mime_type: string;
  file_size_bytes: number;
  document_status: DocumentStatus;
  job_status: IngestionJobStatus;
  already_exists: boolean;
}

export interface AgentResponse {
  agent_id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  system_instructions: string;
  default_mode: UserFacingMode;
  allowed_modes: UserFacingMode[];
  status: string;
  dataset_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ConversationResponse {
  conversation_id: string;
  workspace_id: string;
  agent_id: string;
  created_by_api_key_id: string | null;
  title: string;
  last_used_mode: UserFacingMode;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  message_id: string;
  conversation_id: string;
  created_by_api_key_id: string | null;
  run_id: string | null;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface CitationResponse {
  citation_id: string;
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  quote: string;
}

export interface AgentChatResponse {
  answer: string;
  citations: CitationResponse[];
  confidence_score: number;
  confidence_label: ConfidenceLabel;
  support_summary: SupportSummary;
  verification_status: VerificationStatus;
  degraded_reasons: string[];
  generator_provider: string;
  provider_backend: string;
  provider_model: string | null;
  provider_fallback_used: boolean;
  provider_fallback_from: string | null;
  agent_id: string;
  conversation_id: string;
  dataset_id: string;
  mode: UserFacingMode;
  run_id: string;
  user_message_id: string;
  assistant_message_id: string;
}

export interface RunResponse {
  run_id: string;
  dataset_id: string | null;
  agent_id: string | null;
  conversation_id: string | null;
  selected_mode: UserFacingMode | null;
  requested_tier: ExecutionTier | null;
  router_recommendation: ExecutionTier;
  effective_tier: ExecutionTier;
  routing_reason: string;
  query: string;
  answer: string;
  citations: CitationResponse[];
  confidence_score: number;
  confidence_label: ConfidenceLabel;
  support_summary: SupportSummary;
  verification_status: VerificationStatus;
  degraded_reasons: string[];
  generator_provider: string;
  provider_backend: string;
  provider_model: string | null;
  provider_fallback_used: boolean;
  provider_fallback_from: string | null;
  retrieved_chunk_ids: string[];
  selected_evidence_ids: string[];
  stage_latencies_ms: Record<string, number>;
  total_latency_ms: number;
  created_at: string;
}

export type WorkflowStepId =
  | "init"
  | "conversation_history"
  | "check_retrieval"
  | "research"
  | "generate";

export type WorkflowStepStatus = "idle" | "running" | "completed";

export interface WorkflowStep {
  step: WorkflowStepId;
  label: string;
  status: WorkflowStepStatus;
  durationMs?: number;
  metadata?: Record<string, unknown>;
}

export type ChatStreamEvent =
  | { type: "step_started"; step: WorkflowStepId; label: string }
  | { type: "step_completed"; step: WorkflowStepId; label: string; duration_ms: number; evidence_count?: number; message_count?: number }
  | { type: "answer"; data: AgentChatResponse }
  | { type: "error"; detail: string; status_code: number }
  | { type: "done" };

export interface DashboardSummaryResponse {
  dataset_count: number;
  document_count: number;
  indexed_document_count: number;
  running_job_count: number;
  failed_job_count: number;
  agent_count: number;
  conversation_count: number;
}

export interface DashboardRecentJobResponse {
  job_id: string;
  document_id: string;
  dataset_id: string;
  document_title: string | null;
  status: IngestionJobStatus;
  attempt_count: number;
  error_code: string | null;
  error_detail: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ApiKeyResponse {
  key_id: string;
  label: string;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface ApiKeyCreateResponse extends ApiKeyResponse {
  api_key: string;
}

export type WorkspaceMemberRole = "admin" | "member" | "viewer";
export type WorkspaceMemberStatus = "pending" | "active" | "removed";

export interface TeamMemberResponse {
  member_id: string;
  workspace_id: string;
  email: string;
  role: WorkspaceMemberRole;
  status: WorkspaceMemberStatus;
  invited_at: string;
  joined_at: string | null;
}

export interface AuditLogResponse {
  log_id: string;
  workspace_id: string | null;
  actor_key_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  summary: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

export type SubscriptionPlan = "free" | "pro" | "business" | "enterprise";
export type BillingSubscriptionStatus = "active" | "past_due" | "canceled" | "trialing";

export interface BillingSubscriptionResponse {
  subscription_id: string;
  plan: SubscriptionPlan;
  status: BillingSubscriptionStatus;
  current_period_start: string | null;
  current_period_end: string | null;
  features: string[];
}

export interface BillingPortalResponse {
  portal_url: string | null;
  message: string;
}

export interface SSOInitiateResponse {
  redirect_url: string | null;
  message: string;
}

export interface ModeCapabilityResponse {
  mode: UserFacingMode;
  label: string;
  enabled: boolean;
  backing_tier: ExecutionTier | null;
  description: string;
  availability_reason: "coming_soon" | "plan_restricted" | "tier_restricted" | null;
}

export interface FeatureCapabilityResponse {
  key: string;
  enabled: boolean;
  description: string;
  availability_reason: "coming_soon" | "plan_restricted" | "tier_restricted" | null;
}

export interface CapabilitiesResponse {
  subscription_plan: string;
  max_execution_tier: ExecutionTier;
  default_mode: UserFacingMode;
  manual_mode_override_allowed: boolean;
  modes: ModeCapabilityResponse[];
  features: FeatureCapabilityResponse[];
}
