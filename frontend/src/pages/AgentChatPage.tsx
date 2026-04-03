import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  Database,
  FileSearch,
  Plus,
  Send,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  attachDatasetToAgent,
  createAgentConversation,
  getAgent,
  getConversationMessages,
  getRun,
  listAgentConversations,
  listDatasets,
  sendAgentChat,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatRelativeOrDate, sentenceCase } from "@/lib/format";
import { workspacePath } from "@/lib/routes";
import type { UserFacingMode } from "@/lib/types";

const MODE_OPTIONS: Array<{ label: string; value: UserFacingMode; available: boolean }> = [
  { label: "Auto", value: "auto", available: true },
  { label: "Instant", value: "instant", available: true },
  { label: "Thinking", value: "thinking", available: false },
  { label: "Verified", value: "verified", available: false },
];

function EmptyPanel({
  icon: Icon,
  title,
  description,
  to,
  actionLabel,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  to: string;
  actionLabel: string;
}) {
  return (
    <div className="rounded-[28px] border bg-card px-8 py-10 text-center shadow-sm">
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10">
        <Icon className="h-6 w-6 text-accent" />
      </div>
      <h3 className="mb-2 text-2xl font-semibold tracking-[-0.02em] text-foreground">{title}</h3>
      <p className="mx-auto max-w-2xl text-sm leading-7 text-muted-foreground">{description}</p>
      <Link to={to} className="mt-6 inline-flex">
        <Button variant="outline" className="rounded-full">
          {actionLabel}
        </Button>
      </Link>
    </div>
  );
}

export default function AgentChatPage() {
  const { id } = useParams();
  const { apiKey, workspaceId, workspaceSlug } = useAuth();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<UserFacingMode>("auto");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const agentQuery = useQuery({
    queryKey: ["agent", id],
    queryFn: () => getAgent(apiKey!, id!),
    enabled: Boolean(apiKey && id),
  });

  const datasetsQuery = useQuery({
    queryKey: ["datasets", workspaceId],
    queryFn: () => listDatasets(apiKey!, workspaceId),
    enabled: Boolean(apiKey && workspaceId),
  });

  const conversationsQuery = useQuery({
    queryKey: ["agent", id, "conversations"],
    queryFn: () => listAgentConversations(apiKey!, id!),
    enabled: Boolean(apiKey && id),
  });

  const messagesQuery = useQuery({
    queryKey: ["conversation", selectedConversationId, "messages"],
    queryFn: () => getConversationMessages(apiKey!, selectedConversationId!),
    enabled: Boolean(apiKey && selectedConversationId),
  });

  const attachedDatasets = useMemo(() => {
    const datasets = datasetsQuery.data ?? [];
    const datasetIds = new Set(agentQuery.data?.dataset_ids ?? []);
    return datasets.filter((dataset) => datasetIds.has(dataset.dataset_id));
  }, [agentQuery.data?.dataset_ids, datasetsQuery.data]);

  const latestAssistantRunId = useMemo(() => {
    const messages = messagesQuery.data ?? [];
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === "assistant" && message.run_id) {
        return message.run_id;
      }
    }
    return null;
  }, [messagesQuery.data]);

  const runQuery = useQuery({
    queryKey: ["run", activeRunId],
    queryFn: () => getRun(apiKey!, activeRunId!),
    enabled: Boolean(apiKey && activeRunId),
  });

  useEffect(() => {
    if (!selectedConversationId && conversationsQuery.data && conversationsQuery.data.length > 0) {
      setSelectedConversationId(conversationsQuery.data[0].conversation_id);
    }
  }, [conversationsQuery.data, selectedConversationId]);

  useEffect(() => {
    if (agentQuery.data?.default_mode) {
      setSelectedMode(agentQuery.data.default_mode);
    }
  }, [agentQuery.data?.default_mode]);

  useEffect(() => {
    if (attachedDatasets.length === 0) {
      setSelectedDatasetId("");
      return;
    }

    if (attachedDatasets.length === 1) {
      setSelectedDatasetId(attachedDatasets[0].dataset_id);
      return;
    }

    const stillSelected = attachedDatasets.some((dataset) => dataset.dataset_id === selectedDatasetId);
    if (!stillSelected) {
      setSelectedDatasetId(attachedDatasets[0].dataset_id);
    }
  }, [attachedDatasets, selectedDatasetId]);

  useEffect(() => {
    if (latestAssistantRunId) {
      setActiveRunId(latestAssistantRunId);
    }
  }, [latestAssistantRunId, selectedConversationId]);

  const createConversationMutation = useMutation({
    mutationFn: async (title?: string) => {
      if (!apiKey || !id) {
        throw new Error("Agent conversations require an authenticated agent.");
      }
      return createAgentConversation(apiKey, id, {
        title: title || "New conversation",
        mode: selectedMode,
      });
    },
    onSuccess: (conversation) => {
      setSelectedConversationId(conversation.conversation_id);
      void queryClient.invalidateQueries({ queryKey: ["agent", id, "conversations"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to create a conversation.";
      toast.error(message);
    },
  });

  const attachDatasetMutation = useMutation({
    mutationFn: async (datasetId: string) => {
      if (!apiKey || !id) {
        throw new Error("Agent dataset attachment requires an authenticated agent.");
      }
      return attachDatasetToAgent(apiKey, id, datasetId);
    },
    onSuccess: () => {
      toast.success("Dataset attached to agent.");
      void queryClient.invalidateQueries({ queryKey: ["agent", id] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to attach the dataset.";
      toast.error(message);
    },
  });

  const chatMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey || !id || !agentQuery.data) {
        throw new Error("Agent chat is unavailable until the agent is loaded.");
      }

      if (agentQuery.data.dataset_ids.length === 0) {
        throw new Error("Attach a dataset to this agent before chatting.");
      }

      let conversationId = selectedConversationId;
      if (!conversationId) {
        const newConversation = await createAgentConversation(apiKey, id, {
          title: draft.trim().slice(0, 64),
          mode: selectedMode,
        });
        conversationId = newConversation.conversation_id;
        setSelectedConversationId(conversationId);
      }

      const datasetId =
        agentQuery.data.dataset_ids.length === 1
          ? agentQuery.data.dataset_ids[0]
          : selectedDatasetId || undefined;

      if (!datasetId) {
        throw new Error("Select which attached dataset should answer this question.");
      }

      return sendAgentChat(apiKey, id, {
        conversation_id: conversationId,
        message: draft.trim(),
        mode: selectedMode,
        dataset_id: datasetId,
      });
    },
    onSuccess: (response) => {
      setDraft("");
      setActiveRunId(response.run_id);
      void queryClient.invalidateQueries({ queryKey: ["agent", id, "conversations"] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", response.conversation_id, "messages"] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to send the message.";
      toast.error(message);
    },
  });

  if (agentQuery.isLoading) {
    return <div className="h-[calc(100vh-3.5rem)] rounded-2xl border bg-card animate-pulse" />;
  }

  const agent = agentQuery.data;
  if (!agent) {
    return (
      <div className="max-w-4xl">
        <Link
          to={workspacePath(workspaceSlug, "/agents")}
          className="mb-4 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to agents
        </Link>
        <div className="rounded-2xl border bg-card p-10 text-center">
          <h1 className="mb-2 text-lg font-semibold text-foreground">Agent not found</h1>
          <p className="text-sm text-muted-foreground">
            This agent may have been removed or is no longer available.
          </p>
        </div>
      </div>
    );
  }

  const availableDatasets = datasetsQuery.data ?? [];
  const conversations = conversationsQuery.data ?? [];
  const messages = messagesQuery.data ?? [];
  const run = runQuery.data;
  const activeConversation =
    conversations.find((conversation) => conversation.conversation_id === selectedConversationId) ?? null;

  return (
    <div className="max-w-full -m-6 md:-m-8 h-[calc(100vh-3.5rem)] grid grid-cols-1 border-y bg-background md:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[300px_minmax(0,1fr)_320px]">
      <aside className="hidden border-r bg-card/90 md:flex md:flex-col">
        <div className="border-b px-5 py-5">
          <Link
            to={workspacePath(workspaceSlug, "/agents")}
            className="mb-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Back to agents
          </Link>
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-2xl bg-accent/10">
              <Bot className="h-4 w-4 text-accent" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-foreground">{agent.name}</div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                {agent.description || "Grounded assistant backed by your datasets."}
              </p>
            </div>
          </div>
        </div>

        <div className="border-b px-4 py-4 space-y-4">
          <Button
            variant="outline"
            size="sm"
            className="h-11 w-full rounded-2xl"
            onClick={() => createConversationMutation.mutate("New conversation")}
            disabled={createConversationMutation.isPending}
          >
            <Plus className="mr-1 h-3.5 w-3.5" /> New Chat
          </Button>

          <div>
            <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Attached datasets</div>
            {attachedDatasets.length === 0 ? (
              <div className="space-y-2">
                <div className="text-xs leading-5 text-muted-foreground">
                  Attach a dataset before sending grounded questions.
                </div>
                {availableDatasets.length > 0 ? (
                  <div className="space-y-2">
                    {availableDatasets.slice(0, 3).map((dataset) => (
                      <Button
                        key={dataset.dataset_id}
                        type="button"
                        variant="outline"
                        size="sm"
                        className="w-full justify-start rounded-2xl"
                        onClick={() => attachDatasetMutation.mutate(dataset.dataset_id)}
                        disabled={attachDatasetMutation.isPending}
                      >
                        <Database className="mr-2 h-3.5 w-3.5" />
                        {dataset.name}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <Link
                    to={workspacePath(workspaceSlug, "/datasets")}
                    className="text-xs text-accent hover:underline"
                  >
                    Create a dataset first
                  </Link>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {attachedDatasets.map((dataset) => (
                  <div
                    key={dataset.dataset_id}
                    className="flex items-center gap-2 rounded-2xl border bg-background px-3 py-2.5 text-xs text-foreground"
                  >
                    <Database className="h-3 w-3 text-accent" />
                    <span className="truncate">{dataset.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-3 px-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Conversations
          </div>
          {conversations.length === 0 ? (
            <div className="px-3 py-8 text-center text-xs leading-5 text-muted-foreground">
              No conversations yet. Start a new chat to create the first run.
            </div>
          ) : (
            conversations.map((conversation) => (
              <button
                key={conversation.conversation_id}
                onClick={() => setSelectedConversationId(conversation.conversation_id)}
                className={`mb-1.5 w-full rounded-xl px-3 py-2.5 text-left transition-colors ${
                  selectedConversationId === conversation.conversation_id
                    ? "bg-accent/10 text-foreground"
                    : "text-muted-foreground hover:bg-secondary/70"
                }`}
              >
                <div className="truncate text-sm font-medium">{conversation.title}</div>
                <div className="mt-0.5 text-[10px] text-muted-foreground">
                  {conversation.last_used_mode} • {formatRelativeOrDate(conversation.updated_at)}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="min-w-0 flex flex-col bg-background">
        <div className="shrink-0 border-b bg-background/90 px-6 py-4 backdrop-blur">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4">
            <div className="min-w-0">
              <h2 className="truncate text-lg font-semibold text-foreground">
                {activeConversation?.title || "New conversation"}
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>{agent.name}</span>
                <span>•</span>
                <span>{attachedDatasets.length} dataset{attachedDatasets.length === 1 ? "" : "s"} attached</span>
              </div>
            </div>
            <Badge variant="outline" className="hidden text-[10px] sm:inline-flex">
              Grounded chat
            </Badge>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col px-6 py-8">
            {messagesQuery.isLoading && selectedConversationId ? (
              <div className="text-sm text-muted-foreground">Loading conversation...</div>
            ) : messages.length === 0 ? (
              <div className="flex flex-1 items-center justify-center">
                <EmptyPanel
                  icon={Bot}
                  title="Start a grounded conversation"
                  description="Ask a question about the datasets attached to this agent. Grounded will create a run with citations, confidence, and traceable answer metadata."
                  to={workspacePath(workspaceSlug, "/datasets")}
                  actionLabel={attachedDatasets.length === 0 ? "Open datasets" : "Review datasets"}
                />
              </div>
            ) : (
              messages.map((message) => {
                const isAssistant = message.role === "assistant";
                return (
                  <div key={message.message_id} className={`mb-8 flex ${isAssistant ? "justify-start" : "justify-end"}`}>
                    {isAssistant ? (
                      <div className="w-full max-w-3xl">
                        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                          <Bot className="h-3.5 w-3.5 text-accent" />
                          <span>{agent.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => message.run_id && setActiveRunId(message.run_id)}
                          className="w-full rounded-[26px] border bg-card px-6 py-5 text-left shadow-sm transition-colors hover:border-accent/40"
                        >
                          <p className="whitespace-pre-line text-[15px] leading-8 text-foreground">
                            {message.content}
                          </p>
                          <div className="mt-4 flex flex-wrap items-center gap-2">
                            {message.run_id ? (
                              <Badge variant="accent" className="text-[10px]">
                                <FileSearch className="mr-0.5 h-2.5 w-2.5" /> Inspect run
                              </Badge>
                            ) : null}
                            <span className="text-[10px] text-muted-foreground">
                              {formatRelativeOrDate(message.created_at)}
                            </span>
                          </div>
                        </button>
                      </div>
                    ) : (
                      <div className="max-w-xl rounded-[26px] bg-secondary px-6 py-4">
                        <p className="whitespace-pre-line text-[15px] leading-7 text-foreground">{message.content}</p>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="shrink-0 border-t bg-background/95 px-6 py-4 backdrop-blur">
          <div className="mx-auto w-full max-w-5xl rounded-[30px] border bg-card p-4 shadow-[0_20px_50px_rgba(15,23,42,0.08)]">
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a grounded question..."
              className="min-h-[88px] resize-none border-0 bg-transparent px-2 py-2 text-base shadow-none focus-visible:ring-0"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (draft.trim()) {
                    chatMutation.mutate();
                  }
                }
              }}
            />

            <div className="mt-3 flex flex-col gap-3 border-t pt-3 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {attachedDatasets.length > 1 ? (
                  <select
                    id="chat-dataset"
                    value={selectedDatasetId}
                    onChange={(event) => setSelectedDatasetId(event.target.value)}
                    className="h-9 rounded-full border bg-background px-3 text-foreground"
                  >
                    {attachedDatasets.map((dataset) => (
                      <option key={dataset.dataset_id} value={dataset.dataset_id}>
                        {dataset.name}
                      </option>
                    ))}
                  </select>
                ) : attachedDatasets.length === 1 ? (
                  <Badge variant="outline" className="h-9 rounded-full px-3 text-[11px]">
                    <Database className="mr-1.5 h-3 w-3" />
                    {attachedDatasets[0].name}
                  </Badge>
                ) : (
                  <span className="px-1">Attach a dataset to enable grounded answers.</span>
                )}
              </div>

              <div className="flex flex-wrap items-center justify-end gap-2">
                {MODE_OPTIONS.map((mode) => (
                  <button
                    key={mode.value}
                    type="button"
                    onClick={() => mode.available && setSelectedMode(mode.value)}
                    disabled={!mode.available}
                    className={`rounded-full px-4 py-2 text-xs font-medium transition-all ${
                      selectedMode === mode.value
                        ? "bg-accent text-accent-foreground"
                        : mode.available
                          ? "border border-border bg-background text-foreground hover:bg-secondary"
                          : "border border-border bg-background text-muted-foreground/40 cursor-not-allowed"
                    }`}
                  >
                    {mode.label}
                    {!mode.available ? <span className="ml-1 text-[9px]">soon</span> : null}
                  </button>
                ))}
                <Button
                  variant="pill-accent"
                  size="icon"
                  className="h-11 w-11 rounded-full"
                  disabled={!draft.trim() || chatMutation.isPending}
                  onClick={() => chatMutation.mutate()}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <aside className="hidden overflow-y-auto border-l bg-card/90 xl:block">
        <div className="border-b p-4">
          <h3 className="text-sm font-semibold text-foreground">Answer Inspector</h3>
        </div>

        {!run ? (
          <div className="p-6 text-sm leading-7 text-muted-foreground">
            Select an assistant answer to inspect citations, confidence, and run details.
          </div>
        ) : (
          <>
            <div className="space-y-2 border-b p-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Run ID</span>
                <span className="font-mono text-foreground">{run.run_id.slice(0, 8)}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Mode</span>
                <Badge variant="accent" className="text-[10px]">
                  <Zap className="mr-0.5 h-2.5 w-2.5" /> {run.selected_mode ?? "auto"}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Tier</span>
                <span className="text-foreground">{sentenceCase(run.effective_tier)}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Confidence</span>
                <span className="text-foreground">{Math.round(run.confidence_score * 100)}%</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Verification</span>
                <Badge
                  variant={run.verification_status === "passed" ? "success" : "warning"}
                  className="text-[10px]"
                >
                  {sentenceCase(run.verification_status)}
                </Badge>
              </div>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-muted-foreground">Provider</span>
                <span className="truncate text-right text-foreground">{run.generator_provider}</span>
              </div>
            </div>

            <div className="border-b p-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Routing</h4>
              <p className="text-xs leading-6 text-muted-foreground">{run.routing_reason}</p>
              {run.degraded_reasons.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {run.degraded_reasons.map((reason) => (
                    <Badge key={reason} variant="warning" className="mr-2 mb-2 text-[10px]">
                      {sentenceCase(reason)}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="p-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Citations</h4>
              <div className="space-y-3">
                {run.citations.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No citations were returned for this run.</div>
                ) : (
                  run.citations.map((citation) => (
                    <div key={citation.citation_id} className="rounded-xl border bg-secondary/30 p-3">
                      <div className="mb-2 flex items-center gap-2">
                        <FileSearch className="h-3 w-3 text-accent" />
                        <span className="truncate text-xs font-medium text-foreground">{citation.citation_id}</span>
                      </div>
                      <p className="text-xs leading-6 text-muted-foreground">"{citation.quote}"</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
