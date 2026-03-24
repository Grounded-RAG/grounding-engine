import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Database,
  FileSearch,
  Plus,
  Send,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
        <Link to={workspacePath(workspaceSlug, "/agents")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to agents
        </Link>
        <div className="rounded-2xl border bg-card p-10 text-center">
          <h1 className="text-lg font-semibold text-foreground mb-2">Agent not found</h1>
          <p className="text-sm text-muted-foreground">This agent may have been removed or is no longer available.</p>
        </div>
      </div>
    );
  }

  const availableDatasets = datasetsQuery.data ?? [];
  const conversations = conversationsQuery.data ?? [];
  const messages = messagesQuery.data ?? [];
  const run = runQuery.data;

  return (
    <div className="max-w-full -m-6 md:-m-8 h-[calc(100vh-3.5rem)] flex">
      <div className="w-72 border-r bg-card flex flex-col shrink-0 hidden md:flex">
        <div className="p-4 border-b">
          <Link to={workspacePath(workspaceSlug, "/agents")} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-3">
            <ArrowLeft className="h-3 w-3" /> Back to agents
          </Link>
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-accent" />
            <span className="text-sm font-semibold text-foreground truncate">{agent.name}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {agent.description || "Grounded assistant backed by your datasets."}
          </p>
        </div>
        <div className="p-3 border-b space-y-3">
          <Button
            variant="pill-outline"
            size="sm"
            className="w-full"
            onClick={() => createConversationMutation.mutate("New conversation")}
            disabled={createConversationMutation.isPending}
          >
            <Plus className="h-3.5 w-3.5 mr-1" /> New Chat
          </Button>
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Attached datasets</div>
            {attachedDatasets.length === 0 ? (
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">
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
                        className="w-full justify-start rounded-xl"
                        onClick={() => attachDatasetMutation.mutate(dataset.dataset_id)}
                        disabled={attachDatasetMutation.isPending}
                      >
                        <Database className="h-3.5 w-3.5 mr-2" />
                        {dataset.name}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <Link to={workspacePath(workspaceSlug, "/datasets")} className="text-xs text-accent hover:underline">
                    Create a dataset first
                  </Link>
                )}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {attachedDatasets.map((dataset) => (
                  <Badge key={dataset.dataset_id} variant="outline" className="text-[10px]">
                    <Database className="h-2.5 w-2.5 mr-0.5" /> {dataset.name}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">
              No conversations yet. Start a new chat to create the first run.
            </div>
          ) : (
            conversations.map((conversation) => (
              <button
                key={conversation.conversation_id}
                onClick={() => setSelectedConversationId(conversation.conversation_id)}
                className={`w-full text-left rounded-xl px-3 py-2.5 transition-colors ${
                  selectedConversationId === conversation.conversation_id
                    ? "bg-accent/10 text-foreground"
                    : "text-muted-foreground hover:bg-secondary"
                }`}
              >
                <div className="text-xs font-medium truncate">{conversation.title}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">
                  {conversation.last_used_mode} • {formatRelativeOrDate(conversation.updated_at)}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="border-b flex flex-col gap-3 px-4 py-4 shrink-0">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-medium text-foreground">
                {conversations.find((conversation) => conversation.conversation_id === selectedConversationId)?.title ||
                  "New conversation"}
              </h2>
              <div className="flex items-center gap-2 flex-wrap mt-1">
                <Badge variant="outline" className="text-[10px]">
                  {agent.default_mode}
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {agent.dataset_ids.length} dataset{agent.dataset_ids.length === 1 ? "" : "s"} attached
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {MODE_OPTIONS.map((mode) => (
                <button
                  key={mode.value}
                  type="button"
                  onClick={() => mode.available && setSelectedMode(mode.value)}
                  disabled={!mode.available}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    selectedMode === mode.value
                      ? "bg-accent text-accent-foreground"
                      : mode.available
                        ? "border border-border text-foreground hover:bg-secondary"
                        : "border border-border text-muted-foreground/40 cursor-not-allowed"
                  }`}
                >
                  {mode.label}
                  {!mode.available ? <span className="ml-1 text-[9px]">soon</span> : null}
                </button>
              ))}
            </div>
          </div>
          {attachedDatasets.length > 1 ? (
            <div className="flex items-center gap-3 text-xs">
              <label htmlFor="chat-dataset" className="text-muted-foreground">
                Answer from dataset
              </label>
              <select
                id="chat-dataset"
                value={selectedDatasetId}
                onChange={(event) => setSelectedDatasetId(event.target.value)}
                className="h-9 rounded-xl border bg-background px-3 text-foreground"
              >
                {attachedDatasets.map((dataset) => (
                  <option key={dataset.dataset_id} value={dataset.dataset_id}>
                    {dataset.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messagesQuery.isLoading && selectedConversationId ? (
            <div className="text-sm text-muted-foreground">Loading conversation…</div>
          ) : messages.length === 0 ? (
            <div className="max-w-2xl rounded-2xl border bg-card p-8">
              <h3 className="text-lg font-semibold text-foreground mb-2">Start a grounded conversation</h3>
              <p className="text-sm text-muted-foreground">
                Ask a question about the datasets attached to this agent. Grounded will create a run with citations,
                confidence, and traceable answer metadata.
              </p>
            </div>
          ) : (
            messages.map((message) => {
              const isAssistant = message.role === "assistant";
              return (
                <div
                  key={message.message_id}
                  className={`max-w-3xl ${isAssistant ? "" : "ml-auto"}`}
                >
                  {isAssistant ? (
                    <button
                      type="button"
                      onClick={() => message.run_id && setActiveRunId(message.run_id)}
                      className="w-full text-left rounded-2xl border bg-card px-5 py-4 hover:border-accent/40 transition-colors"
                    >
                      <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{message.content}</p>
                      <div className="flex items-center gap-2 mt-3 flex-wrap">
                        {message.run_id ? (
                          <Badge variant="accent" className="text-[10px]">
                            <FileSearch className="h-2.5 w-2.5 mr-0.5" /> Inspect run
                          </Badge>
                        ) : null}
                        <span className="text-[10px] text-muted-foreground">
                          {formatRelativeOrDate(message.created_at)}
                        </span>
                      </div>
                    </button>
                  ) : (
                    <div className="rounded-2xl bg-secondary px-5 py-3.5">
                      <p className="text-sm text-foreground whitespace-pre-line">{message.content}</p>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        <div className="border-t p-4">
          <div className="max-w-3xl mx-auto flex gap-2">
            <Input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a grounded question..."
              className="flex-1 h-11 rounded-xl"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (draft.trim()) {
                    chatMutation.mutate();
                  }
                }
              }}
            />
            <Button
              variant="pill-accent"
              size="icon"
              className="h-11 w-11"
              disabled={!draft.trim() || chatMutation.isPending}
              onClick={() => chatMutation.mutate()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="w-80 border-l bg-card overflow-y-auto hidden lg:block">
        <div className="p-4 border-b">
          <h3 className="text-sm font-semibold text-foreground">Answer Inspector</h3>
        </div>

        {!run ? (
          <div className="p-6 text-sm text-muted-foreground">
            Select an assistant answer to inspect citations, confidence, and run details.
          </div>
        ) : (
          <>
            <div className="p-4 border-b space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Run ID</span>
                <span className="font-mono text-foreground">{run.run_id.slice(0, 8)}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Mode</span>
                <Badge variant="accent" className="text-[10px]">
                  <Zap className="h-2.5 w-2.5 mr-0.5" /> {run.selected_mode ?? "auto"}
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
                <Badge variant={run.verification_status === "passed" ? "success" : "warning"} className="text-[10px]">
                  {sentenceCase(run.verification_status)}
                </Badge>
              </div>
            </div>

            <div className="p-4 border-b">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Routing</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">{run.routing_reason}</p>
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
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Citations</h4>
              <div className="space-y-3">
                {run.citations.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No citations were returned for this run.</div>
                ) : (
                  run.citations.map((citation) => (
                    <div key={citation.citation_id} className="rounded-xl border bg-secondary/30 p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <FileSearch className="h-3 w-3 text-accent" />
                        <span className="text-xs font-medium text-foreground truncate">{citation.citation_id}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">"{citation.quote}"</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
