import type {
  AgentChatResponse,
  AgentResponse,
  ApiKeyCreateResponse,
  ApiKeyResponse,
  AuditLogListResponse,
  AuthSmokeResponse,
  BillingPortalResponse,
  BillingSubscriptionResponse,
  CapabilitiesResponse,
  ConversationResponse,
  DashboardRecentJobResponse,
  DashboardSummaryResponse,
  DatasetDocumentResponse,
  DatasetIngestionJobResponse,
  DatasetResponse,
  DatasetUploadResponse,
  EmailAuthResponse,
  MessageResponse,
  RunResponse,
  SSOInitiateResponse,
  TeamMemberResponse,
  UserFacingMode,
  WorkspaceMemberRole,
  WorkspaceResponse,
} from "@/lib/types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

function buildHeaders(apiKey: string, extra?: HeadersInit): HeadersInit {
  return {
    "X-API-Key": apiKey,
    ...extra,
  };
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : response.statusText || "Request failed";
    throw new ApiError(response.status, detail);
  }

  return data as T;
}

async function request<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: buildHeaders(apiKey, init?.headers),
  });
  return parseResponse<T>(response);
}

export const apiBaseUrl = API_BASE_URL;

export async function signInWithEmail(payload: {
  email: string;
  password: string;
}) {
  const response = await fetch(`${API_BASE_URL}/v1/auth/email/sign-in`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<EmailAuthResponse>(response);
}

export async function signUpWithEmail(payload: {
  email: string;
  password: string;
  full_name?: string;
  organization_name?: string;
  workspace_name?: string;
}) {
  const response = await fetch(`${API_BASE_URL}/v1/auth/email/sign-up`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<EmailAuthResponse>(response);
}

export function authenticateWithApiKey(apiKey: string) {
  return request<AuthSmokeResponse>("/v1/auth/smoke", apiKey);
}

export function getCapabilities(apiKey: string) {
  return request<CapabilitiesResponse>("/v1/capabilities", apiKey);
}

export function listWorkspaces(apiKey: string) {
  return request<WorkspaceResponse[]>("/v1/workspaces", apiKey);
}

export function createWorkspace(
  apiKey: string,
  payload: { name: string; slug?: string; description?: string },
) {
  return request<WorkspaceResponse>("/v1/workspaces", apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getDashboardSummary(apiKey: string) {
  return request<DashboardSummaryResponse>("/v1/dashboard/summary", apiKey);
}

export function getDashboardRecentRuns(apiKey: string) {
  return request<RunResponse[]>("/v1/dashboard/recent-runs", apiKey);
}

export function getDashboardRecentJobs(apiKey: string) {
  return request<DashboardRecentJobResponse[]>("/v1/dashboard/recent-jobs", apiKey);
}

export function listDatasets(apiKey: string, workspaceId?: string | null) {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  return request<DatasetResponse[]>(`/v1/datasets${query}`, apiKey);
}

export function getDataset(apiKey: string, datasetId: string) {
  return request<DatasetResponse>(`/v1/datasets/${datasetId}`, apiKey);
}

export function createDataset(
  apiKey: string,
  payload: {
    workspace_id: string;
    name: string;
    domain?: string;
    sensitivity_level?: string;
    freshness_profile?: string;
    min_execution_tier?: string;
    allow_web_fallback?: boolean;
    allow_internal_model_retrieval?: boolean;
  },
) {
  return request<DatasetResponse>("/v1/datasets", apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listDatasetDocuments(apiKey: string, datasetId: string) {
  return request<DatasetDocumentResponse[]>(`/v1/datasets/${datasetId}/documents`, apiKey);
}

export function listDatasetJobs(apiKey: string, datasetId: string) {
  return request<DatasetIngestionJobResponse[]>(`/v1/datasets/${datasetId}/ingestion-jobs`, apiKey);
}

export async function uploadDatasetDocument(
  apiKey: string,
  datasetId: string,
  file: File,
  title?: string,
) {
  const body = new FormData();
  body.append("file", file);
  if (title) body.append("title", title);

  const response = await fetch(`${API_BASE_URL}/v1/datasets/${datasetId}/upload`, {
    method: "POST",
    headers: buildHeaders(apiKey),
    body,
  });
  return parseResponse<DatasetUploadResponse>(response);
}

export function listAgents(apiKey: string, workspaceId?: string | null) {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
  return request<AgentResponse[]>(`/v1/agents${query}`, apiKey);
}

export function getAgent(apiKey: string, agentId: string) {
  return request<AgentResponse>(`/v1/agents/${agentId}`, apiKey);
}

export function createAgent(
  apiKey: string,
  payload: {
    workspace_id: string;
    name: string;
    description?: string;
    system_instructions?: string;
    default_mode?: UserFacingMode;
    allowed_modes?: UserFacingMode[];
  },
) {
  return request<AgentResponse>("/v1/agents", apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function attachDatasetToAgent(apiKey: string, agentId: string, datasetId: string) {
  return request<AgentResponse>(`/v1/agents/${agentId}/datasets`, apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId }),
  });
}

export function listAgentConversations(apiKey: string, agentId: string) {
  return request<ConversationResponse[]>(`/v1/agents/${agentId}/conversations`, apiKey);
}

export function createAgentConversation(
  apiKey: string,
  agentId: string,
  payload: { title?: string; mode?: UserFacingMode },
) {
  return request<ConversationResponse>(`/v1/agents/${agentId}/conversations`, apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getConversationMessages(apiKey: string, conversationId: string) {
  return request<MessageResponse[]>(`/v1/conversations/${conversationId}/messages`, apiKey);
}

export function sendAgentChat(
  apiKey: string,
  agentId: string,
  payload: {
    conversation_id: string;
    message: string;
    mode?: UserFacingMode;
    dataset_id?: string;
  },
) {
  return request<AgentChatResponse>(`/v1/agents/${agentId}/chat`, apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listRuns(apiKey: string, datasetId?: string | null) {
  const query = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
  return request<RunResponse[]>(`/v1/runs${query}`, apiKey);
}

export function getRun(apiKey: string, runId: string) {
  return request<RunResponse>(`/v1/runs/${runId}`, apiKey);
}

export function listApiKeys(apiKey: string) {
  return request<ApiKeyResponse[]>("/v1/api-keys", apiKey);
}

export function createApiKey(apiKey: string, label: string) {
  return request<ApiKeyCreateResponse>("/v1/api-keys", apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label }),
  });
}

export function revokeApiKey(apiKey: string, keyId: string) {
  return request<ApiKeyResponse>(`/v1/api-keys/${keyId}/revoke`, apiKey, {
    method: "POST",
  });
}

// Team Members
export function listTeamMembers(apiKey: string, workspaceId: string) {
  return request<TeamMemberResponse[]>(`/v1/workspaces/${workspaceId}/members`, apiKey);
}

export function inviteTeamMember(
  apiKey: string,
  workspaceId: string,
  payload: { email: string; role: WorkspaceMemberRole },
) {
  return request<TeamMemberResponse>(`/v1/workspaces/${workspaceId}/members`, apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateTeamMember(
  apiKey: string,
  workspaceId: string,
  memberId: string,
  payload: { role: WorkspaceMemberRole },
) {
  return request<TeamMemberResponse>(
    `/v1/workspaces/${workspaceId}/members/${memberId}`,
    apiKey,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export async function removeTeamMember(
  apiKey: string,
  workspaceId: string,
  memberId: string,
) {
  const response = await fetch(
    `${API_BASE_URL}/v1/workspaces/${workspaceId}/members/${memberId}`,
    {
      method: "DELETE",
      headers: buildHeaders(apiKey),
    },
  );
  if (!response.ok) {
    const data = response.headers.get("content-type")?.includes("application/json")
      ? await response.json()
      : null;
    const detail =
      data && "detail" in data ? String(data.detail) : response.statusText || "Request failed";
    throw new ApiError(response.status, detail);
  }
}

// Audit Logs
export function listAuditLogs(
  apiKey: string,
  params?: { workspace_id?: string; page?: number; page_size?: number },
) {
  const q = new URLSearchParams();
  if (params?.workspace_id) q.set("workspace_id", params.workspace_id);
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));
  const query = q.toString() ? `?${q.toString()}` : "";
  return request<AuditLogListResponse>(`/v1/audit-logs${query}`, apiKey);
}

// Billing
export function getBillingSubscription(apiKey: string) {
  return request<BillingSubscriptionResponse>("/v1/billing/subscription", apiKey);
}

export function getBillingPortal(apiKey: string) {
  return request<BillingPortalResponse>("/v1/billing/portal", apiKey, { method: "POST" });
}

// SSO
export async function initiateSso(payload: { organization_slug: string }) {
  const response = await fetch(`${API_BASE_URL}/v1/auth/sso/initiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<SSOInitiateResponse>(response);
}

// Google OAuth
export async function signInWithGoogle(id_token: string) {
  const response = await fetch(`${API_BASE_URL}/v1/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token }),
  });
  return parseResponse<EmailAuthResponse>(response);
}
