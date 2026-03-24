import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Copy,
  CreditCard,
  Eye,
  Key,
  LockKeyhole,
  Plus,
  Shield,
  Trash2,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createApiKey, getCapabilities, listApiKeys, revokeApiKey } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatRelativeOrDate, sentenceCase } from "@/lib/format";

function ComingSoonCard({
  icon: Icon,
  title,
  desc,
}: {
  icon: typeof Users;
  title: string;
  desc: string;
}) {
  return (
    <div className="rounded-2xl border bg-secondary/30 p-6 flex items-start gap-4">
      <div className="h-10 w-10 rounded-xl bg-secondary flex items-center justify-center shrink-0">
        <Icon className="h-5 w-5 text-muted-foreground" />
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <Badge variant="coming" className="text-[9px]">
            Coming soon
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}

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
                Current execution entitlement: {auth?.max_execution_tier ? sentenceCase(auth.max_execution_tier) : "Standard"}
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
                    Available
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
            <h2 className="text-lg font-semibold text-foreground">API Keys</h2>
            <p className="text-sm text-muted-foreground">
              The current backend authenticates workspaces with API keys. Keep them for integrations and developer access.
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
                  Grounded only shows the raw API key once. Store it somewhere safe before leaving this page.
                </p>
                <code className="block rounded-xl bg-background px-3 py-2 text-xs break-all">{createdKey}</code>
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
              No API keys yet. Create one to authenticate local integrations and developer workflows.
            </div>
          ) : (
            <div className="divide-y">
              {apiKeys.map((key) => {
                const isCurrentAuthKey = auth?.api_key_id === key.key_id;
                return (
                  <div key={key.key_id} className="flex items-center justify-between px-5 py-4 gap-4">
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
                        Created {formatDateTime(key.created_at)} • Last used {formatRelativeOrDate(key.last_used_at)}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      disabled={Boolean(key.revoked_at) || isCurrentAuthKey || revokeKeyMutation.isPending}
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

      {!isApiKeysView && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Coming Soon</h2>
          <ComingSoonCard icon={Users} title="Team Members" desc="Invite teammates and manage workspace membership." />
          <ComingSoonCard icon={LockKeyhole} title="SSO & SAML" desc="Enterprise human login for secure team access." />
          <ComingSoonCard icon={Shield} title="Role-Based Access" desc="Fine-grained permissions for datasets, agents, and workspaces." />
          <ComingSoonCard icon={Eye} title="Governance" desc="Audit logs, data policies, and compliance controls." />
          <ComingSoonCard icon={CreditCard} title="Billing" desc="Subscription management, invoices, and usage limits." />
        </div>
      )}
    </div>
  );
}
