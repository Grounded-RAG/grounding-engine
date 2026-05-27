import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Copy,
  CreditCard,
  Eye,
  Key,
  LockKeyhole,
  Plus,
  Shield,
  Trash2,
  UserMinus,
  UserPlus,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createApiKey,
  getCapabilities,
  getBillingSubscription,
  getBillingPortal,
  listApiKeys,
  listAuditLogs,
  listTeamMembers,
  inviteTeamMember,
  removeTeamMember,
  revokeApiKey,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatRelativeOrDate, sentenceCase } from "@/lib/format";
import type { WorkspaceMemberRole } from "@/lib/types";

// ─── Team Members ────────────────────────────────────────────────────────────

function TeamMembersSection({ workspaceId }: { workspaceId: string }) {
  const { apiKey } = useAuth();
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<WorkspaceMemberRole>("member");

  const membersQuery = useQuery({
    queryKey: ["team-members", workspaceId],
    queryFn: () => listTeamMembers(apiKey!, workspaceId),
    enabled: Boolean(apiKey),
  });

  const inviteMutation = useMutation({
    mutationFn: () => {
      if (!apiKey || !inviteEmail.trim()) throw new Error("Enter a valid email address.");
      return inviteTeamMember(apiKey, workspaceId, { email: inviteEmail.trim(), role: inviteRole });
    },
    onSuccess: () => {
      setInviteEmail("");
      toast.success("Invitation sent.");
      void queryClient.invalidateQueries({ queryKey: ["team-members", workspaceId] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to send invitation.");
    },
  });

  const removeMutation = useMutation({
    mutationFn: (memberId: string) => {
      if (!apiKey) throw new Error("You must be signed in.");
      return removeTeamMember(apiKey, workspaceId, memberId);
    },
    onSuccess: () => {
      toast.success("Member removed.");
      void queryClient.invalidateQueries({ queryKey: ["team-members", workspaceId] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to remove member.");
    },
  });

  const members = membersQuery.data ?? [];

  return (
    <div className="mb-8">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Users className="h-4 w-4" /> Team Members
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Invite teammates to collaborate in this workspace.
        </p>
      </div>

      <div className="rounded-2xl border bg-card p-5 mb-4">
        <Label htmlFor="invite-email">Invite by email</Label>
        <div className="flex gap-3 mt-2">
          <Input
            id="invite-email"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="colleague@example.com"
            className="h-11 rounded-xl"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as WorkspaceMemberRole)}
            className="h-11 rounded-xl border bg-background px-3 text-sm text-foreground focus:outline-none"
          >
            <option value="viewer">Viewer</option>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
          <Button
            variant="pill-accent"
            className="shrink-0"
            onClick={() => inviteMutation.mutate()}
            disabled={!inviteEmail.trim() || inviteMutation.isPending}
          >
            <UserPlus className="h-3.5 w-3.5 mr-1" />
            {inviteMutation.isPending ? "Inviting..." : "Invite"}
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border bg-card overflow-hidden">
        {membersQuery.isLoading ? (
          <div className="p-5 text-sm text-muted-foreground">Loading members...</div>
        ) : members.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            No members yet. Invite someone to collaborate.
          </div>
        ) : (
          <div className="divide-y">
            {members.map((m) => (
              <div key={m.member_id} className="flex items-center justify-between px-5 py-4 gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{m.email}</span>
                    <Badge variant="outline" className="text-[9px] capitalize">
                      {m.role}
                    </Badge>
                    {m.status === "pending" && (
                      <Badge variant="coming" className="text-[9px]">Pending</Badge>
                    )}
                    {m.status === "active" && (
                      <Badge variant="success" className="text-[9px]">Active</Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Invited {formatDateTime(m.invited_at)}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive"
                  disabled={removeMutation.isPending}
                  onClick={() => removeMutation.mutate(m.member_id)}
                >
                  <UserMinus className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Role-Based Access ────────────────────────────────────────────────────────

function RbacSection() {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
        <Shield className="h-4 w-4" /> Role-Based Access
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Fine-grained permissions for datasets, agents, and workspaces.
      </p>
      <div className="rounded-2xl border bg-card overflow-hidden">
        {(["admin", "member", "viewer"] as const).map((role) => (
          <div key={role} className="flex items-start justify-between px-5 py-4 gap-4 border-b last:border-b-0">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground capitalize">{role}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {role === "admin" && "Full access — manage members, datasets, agents, and settings."}
                {role === "member" && "Create and use agents and datasets. Cannot manage members."}
                {role === "viewer" && "Read-only access to agents and datasets."}
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
              Enforced
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Governance / Audit Logs ─────────────────────────────────────────────────

function GovernanceSection() {
  const { apiKey } = useAuth();
  const [page, setPage] = useState(1);

  const logsQuery = useQuery({
    queryKey: ["audit-logs", page],
    queryFn: () => listAuditLogs(apiKey!, { page, page_size: 20 }),
    enabled: Boolean(apiKey),
  });

  const logs = logsQuery.data?.items ?? [];
  const total = logsQuery.data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
        <Eye className="h-4 w-4" /> Audit Logs
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Immutable record of significant actions taken in your workspace.
      </p>
      <div className="rounded-2xl border bg-card overflow-hidden">
        {logsQuery.isLoading ? (
          <div className="p-5 text-sm text-muted-foreground">Loading audit logs...</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            No audit log entries yet. Entries appear when members take significant actions.
          </div>
        ) : (
          <>
            <div className="divide-y">
              {logs.map((log) => (
                <div key={log.log_id} className="px-5 py-3 gap-4">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-foreground">{log.action}</span>
                    <Badge variant="outline" className="text-[9px]">{log.resource_type}</Badge>
                    {log.resource_id && (
                      <span className="text-xs text-muted-foreground font-mono truncate max-w-[160px]">
                        {log.resource_id}
                      </span>
                    )}
                  </div>
                  {log.summary && (
                    <p className="text-xs text-muted-foreground mt-0.5">{log.summary}</p>
                  )}
                  <div className="text-[10px] text-muted-foreground mt-0.5">
                    {formatDateTime(log.created_at)}
                  </div>
                </div>
              ))}
            </div>
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t text-xs text-muted-foreground">
                <span>Page {page} of {totalPages} — {total} entries</span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                    Previous
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Billing ─────────────────────────────────────────────────────────────────

function BillingSection() {
  const { apiKey } = useAuth();
  const queryClient = useQueryClient();

  const subscriptionQuery = useQuery({
    queryKey: ["billing-subscription"],
    queryFn: () => getBillingSubscription(apiKey!),
    enabled: Boolean(apiKey),
  });

  const portalMutation = useMutation({
    mutationFn: () => {
      if (!apiKey) throw new Error("Not authenticated.");
      return getBillingPortal(apiKey);
    },
    onSuccess: (data) => {
      if (data.portal_url) {
        window.open(data.portal_url, "_blank", "noopener");
      } else {
        toast.info(data.message);
      }
    },
    onError: () => toast.error("Failed to open billing portal."),
  });

  const sub = subscriptionQuery.data;

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
        <CreditCard className="h-4 w-4" /> Billing
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Manage your subscription, plan, and usage limits.
      </p>
      {subscriptionQuery.isLoading ? (
        <div className="rounded-2xl border bg-card p-5 text-sm text-muted-foreground">
          Loading subscription...
        </div>
      ) : sub ? (
        <div className="rounded-2xl border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-foreground capitalize">
                {sub.plan} Plan
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5 capitalize">
                Status: {sub.status.replace("_", " ")}
              </p>
            </div>
            <Button
              variant="pill-accent"
              size="sm"
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
            >
              {portalMutation.isPending ? "Opening..." : "Manage plan"}
            </Button>
          </div>
          <ul className="space-y-1">
            {sub.features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
                {f}
              </li>
            ))}
          </ul>
          {sub.current_period_end && (
            <p className="text-xs text-muted-foreground mt-4">
              Current period ends {formatDateTime(sub.current_period_end)}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

// ─── SSO / SAML ──────────────────────────────────────────────────────────────

function SsoSection() {
  const [orgSlug, setOrgSlug] = useState("");

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-1">
        <LockKeyhole className="h-4 w-4" /> SSO & SAML
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Enterprise single sign-on for secure team access via your identity provider.
      </p>
      <div className="rounded-2xl border bg-card p-5">
        <Label htmlFor="sso-org-slug">Organization slug</Label>
        <div className="flex gap-3 mt-2">
          <Input
            id="sso-org-slug"
            value={orgSlug}
            onChange={(e) => setOrgSlug(e.target.value)}
            placeholder="your-company"
            className="h-11 rounded-xl"
          />
          <Button
            variant="pill-accent"
            className="shrink-0"
            disabled={!orgSlug.trim()}
            onClick={() => {
              toast.info(
                `SSO is not yet configured for '${orgSlug.trim()}'. Contact support to enable SAML/SSO.`,
              );
            }}
          >
            Configure SSO
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          SSO configuration requires an Enterprise plan. Contact{" "}
          <a href="mailto:support@grounded.ai" className="underline">
            support
          </a>{" "}
          to get started.
        </p>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const location = useLocation();
  const queryClient = useQueryClient();
  const { apiKey, auth } = useAuth();
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const capabilitiesQuery = useQuery({
    queryKey: ["capabilities"],
    queryFn: () => getCapabilities(apiKey!),
    enabled: Boolean(apiKey),
  });

  const apiKeysQuery = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => listApiKeys(apiKey!),
    enabled: Boolean(apiKey),
  });

  const createKeyMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey || !newKeyLabel.trim()) {
        throw new Error("Enter a label for the new API key.");
      }
      return createApiKey(apiKey, newKeyLabel.trim());
    },
    onSuccess: (response) => {
      setCreatedKey(response.api_key);
      setNewKeyLabel("");
      toast.success("API key created. Copy it now because it will not be shown again.");
      void queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to create the API key.";
      toast.error(message);
    },
  });

  const revokeKeyMutation = useMutation({
    mutationFn: async (keyId: string) => {
      if (!apiKey) {
        throw new Error("You must be signed in to revoke an API key.");
      }
      return revokeApiKey(apiKey, keyId);
    },
    onSuccess: () => {
      toast.success("API key revoked.");
      void queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to revoke the API key.";
      toast.error(message);
    },
  });

  const isApiKeysView = location.pathname.endsWith("/api-keys");
  const capabilities = capabilitiesQuery.data;
  const apiKeys = apiKeysQuery.data ?? [];

  const visibleTitle = isApiKeysView ? "API Keys" : "Settings";
  const visibleSubtitle = isApiKeysView
    ? "Manage developer access and programmatic integrations."
    : "Manage your plan, product capabilities, and developer access.";

  const planLabel = auth?.subscription_plan
    ? sentenceCase(auth.subscription_plan)
    : "Free";

  const modeCapabilities = useMemo(() => capabilities?.modes ?? [], [capabilities?.modes]);

  const workspaceId = auth?.workspace_id ?? "";

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">{visibleTitle}</h1>
        <p className="text-sm text-muted-foreground mt-1">{visibleSubtitle}</p>
      </div>

      {!isApiKeysView && (
        <div className="rounded-2xl border bg-card p-6 mb-6">
          <div className="flex items-center justify-between mb-4 gap-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">{planLabel} Plan</h2>
              <p className="text-sm text-muted-foreground">
                Current execution entitlement:{" "}
                {auth?.max_execution_tier ? sentenceCase(auth.max_execution_tier) : "Standard"}
              </p>
            </div>
            <Badge variant="accent" className="text-[10px]">
              Workspace auth via API key
            </Badge>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {modeCapabilities.map((mode) => (
              <div
                key={mode.mode}
                className={`rounded-xl border p-3 text-center ${
                  mode.enabled ? "bg-accent/5 border-accent/20" : "bg-secondary"
                }`}
              >
                <div className="text-sm font-medium text-foreground">{mode.label}</div>
                <div className="text-xs text-muted-foreground mt-1">{mode.description}</div>
                {mode.enabled ? (
                  <Badge variant="success" className="text-[9px] mt-2">
                    Live
                  </Badge>
                ) : (
                  <Badge variant="coming" className="text-[9px] mt-2">
                    {mode.availability_reason === "coming_soon" ? "Coming soon" : "Unavailable"}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4 gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Key className="h-4 w-4" /> API Keys
            </h2>
            <p className="text-sm text-muted-foreground">
              The current backend authenticates workspaces with API keys. Keep them for integrations
              and developer access.
            </p>
          </div>
        </div>

        <div className="rounded-2xl border bg-card p-5 mb-4">
          <Label htmlFor="new-api-key">Create a new key</Label>
          <div className="flex gap-3 mt-2">
            <Input
              id="new-api-key"
              value={newKeyLabel}
              onChange={(event) => setNewKeyLabel(event.target.value)}
              placeholder="Frontend integration key"
              className="h-11 rounded-xl"
            />
            <Button
              variant="pill-accent"
              className="shrink-0"
              onClick={() => createKeyMutation.mutate()}
              disabled={!newKeyLabel.trim() || createKeyMutation.isPending}
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              {createKeyMutation.isPending ? "Creating..." : "Create key"}
            </Button>
          </div>
        </div>

        {createdKey ? (
          <div className="rounded-2xl border border-accent/20 bg-accent/5 p-5 mb-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-sm font-semibold text-foreground mb-1">Copy this key now</div>
                <p className="text-xs text-muted-foreground mb-3">
                  Grounded only shows the raw API key once. Store it somewhere safe before leaving
                  this page.
                </p>
                <code className="block rounded-xl bg-background px-3 py-2 text-xs break-all">
                  {createdKey}
                </code>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  await navigator.clipboard.writeText(createdKey);
                  toast.success("API key copied.");
                }}
              >
                <Copy className="h-3.5 w-3.5 mr-1" /> Copy
              </Button>
            </div>
          </div>
        ) : null}

        <div className="rounded-2xl border bg-card overflow-hidden">
          {apiKeysQuery.isLoading ? (
            <div className="p-5 text-sm text-muted-foreground">Loading API keys...</div>
          ) : apiKeys.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No API keys yet. Create one to authenticate local integrations and developer
              workflows.
            </div>
          ) : (
            <div className="divide-y">
              {apiKeys.map((key) => {
                const isCurrentAuthKey = auth?.api_key_id === key.key_id;
                return (
                  <div
                    key={key.key_id}
                    className="flex items-center justify-between px-5 py-4 gap-4"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-foreground">{key.label}</span>
                        {isCurrentAuthKey ? (
                          <Badge variant="accent" className="text-[10px]">
                            Current session
                          </Badge>
                        ) : null}
                        {key.revoked_at ? (
                          <Badge variant="warning" className="text-[10px]">
                            Revoked
                          </Badge>
                        ) : null}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Created {formatDateTime(key.created_at)} • Last used{" "}
                        {formatRelativeOrDate(key.last_used_at)}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      disabled={
                        Boolean(key.revoked_at) ||
                        isCurrentAuthKey ||
                        revokeKeyMutation.isPending
                      }
                      onClick={() => revokeKeyMutation.mutate(key.key_id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {!isApiKeysView && workspaceId && (
        <>
          <TeamMembersSection workspaceId={workspaceId} />
          <RbacSection />
          <GovernanceSection />
          <BillingSection />
          <SsoSection />
        </>
      )}
    </div>
  );
}
