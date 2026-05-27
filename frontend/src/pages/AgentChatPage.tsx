import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Check,
  Copy,
  Database,
  FileSearch,
  Flag,
  GitMerge,
  LoaderCircle,
  Plus,
  RefreshCw,
  Send,
  Share2,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
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
  getCapabilities,
  getConversationMessages,
  getRun,
  listAgentConversations,
  listDatasets,
  streamAgentChat,
  submitFeedback,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatRelativeOrDate, sentenceCase } from "@/lib/format";
import { workspacePath } from "@/lib/routes";
import {
  confidenceBadgeVariant,
  confidenceLabelText,
  degradedReasonDescription,
  providerDisplayText,
  supportSummaryText,
} from "@/lib/trust";
import type {
  FeedbackSubmission,
  MessageResponse,
  ModeCapabilityResponse,
  UserFacingMode,
  WorkflowStep,
} from "@/lib/types";
import WorkflowStepsPanel from "@/components/WorkflowStepsPanel";
import QueryJourneyModal from "@/components/QueryJourneyModal";
import FeedbackModal from "@/components/FeedbackModal";

const FALLBACK_MODE_OPTIONS: ModeCapabilityResponse[] = [
  {
    mode: "auto",
    label: "Auto",
    enabled: true,
    backing_tier: null,
    description: "Recommended mode that follows the current Standard path.",
    availability_reason: null,
  },
  {
    mode: "instant",
    label: "Instant",
    enabled: true,
    backing_tier: "standard",
    description: "Fast grounded answers for everyday document questions.",
    availability_reason: null,
  },
  {
    mode: "thinking",
    label: "Thinking",
    enabled: true,
    backing_tier: "enterprise",
    description: "Deeper retrieval for harder questions.",
    availability_reason: null,
  },
  {
    mode: "verified",
    label: "Verified",
    enabled: true,
    backing_tier: "critical",
    description: "Highest-assurance path for sensitive work.",
    availability_reason: null,
  },
];

const GENERATING_COPY = [
  "Reviewing grounded evidence",
  "Tracing relevant citations",
  "Drafting the answer",
];

type LocalExchangeStatus = "pending" | "error";

interface LocalExchange {
  tempUserId: string;
  tempAssistantId: string;
  conversationId: string | null;
  conversationTitle: string;
  message: string;
  mode: UserFacingMode;
  datasetId?: string;
  submittedAt: string;
  status: LocalExchangeStatus;
  errorMessage?: string;
}

interface ChatSubmission {
  tempUserId: string;
  tempAssistantId: string;
  conversationId: string | null;
  conversationTitle: string;
  message: string;
  mode: UserFacingMode;
  datasetId?: string;
  submittedAt: string;
}

type VisibleChatMessage =
  | {
      kind: "server";
      key: string;
      role: "user" | "assistant";
      content: string;
      createdAt: string;
      runId: string | null;
      isPending?: false;
      isError?: false;
    }
  | {
      kind: "optimistic-user";
      key: string;
      role: "user";
      content: string;
      createdAt: string;
      runId: null;
      isPending?: false;
      isError?: false;
    }
  | {
      kind: "pending";
      key: string;
      role: "assistant";
      content: string;
      createdAt: string;
      runId: null;
      isPending: true;
      isError?: false;
    }
  | {
      kind: "error";
      key: string;
      role: "assistant";
      content: string;
      createdAt: string;
      runId: null;
      isPending?: false;
      isError: true;
      retryLabel: string;
    };

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
    <div className="gradient-subtle rounded-[32px] border border-border/70 px-8 py-12 text-center shadow-[0_24px_60px_rgba(15,23,42,0.06)]">
      <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-[22px] bg-accent/10 text-accent shadow-[0_12px_30px_rgba(59,130,246,0.14)]">
        <Icon className="h-7 w-7" />
      </div>
      <h3 className="mb-3 font-display text-3xl font-semibold tracking-[-0.03em] text-foreground">
        {title}
      </h3>
      <p className="mx-auto max-w-2xl text-sm leading-7 text-muted-foreground">{description}</p>
      <div className="mt-8">
        <Link to={to} className="inline-flex">
          <Button variant="outline" className="rounded-full px-6">
            {actionLabel}
          </Button>
        </Link>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5">
        <span className="chat-typing-dot" />
        <span className="chat-typing-dot [animation-delay:0.16s]" />
        <span className="chat-typing-dot [animation-delay:0.32s]" />
      </div>
      <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
        Generating
      </span>
    </div>
  );
}

function AssistantStatusCopy({ submittedAt }: { submittedAt: string }) {
  const cycleIndex = Math.floor((Date.now() - new Date(submittedAt).getTime()) / 1400) % GENERATING_COPY.length;
  return <span className="text-sm text-muted-foreground">{GENERATING_COPY[cycleIndex]}</span>;
}


function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      title="Copy"
      onClick={() => {
        void navigator.clipboard?.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function isSameConversation(
  exchangeConversationId: string | null,
  selectedConversationId: string | null,
  hasMessages: boolean,
) {
  if (exchangeConversationId && selectedConversationId) {
    return exchangeConversationId === selectedConversationId;
  }

  if (!exchangeConversationId && !selectedConversationId) {
    return true;
  }

  return !hasMessages && !selectedConversationId;
}

export default function AgentChatPage() {
  const { id } = useParams();
  const { apiKey, workspaceId, workspaceSlug } = useAuth();
  const queryClient = useQueryClient();
  const scrollAnchorRef = useRef<HTMLDivElement | null>(null);
  const [draft, setDraft] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<UserFacingMode>("auto");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [datasetToAttachId, setDatasetToAttachId] = useState("");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [localExchange, setLocalExchange] = useState<LocalExchange | null>(null);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [showWorkflowPanel, setShowWorkflowPanel] = useState(false);
  const [lastStreamedRunId, setLastStreamedRunId] = useState<string | null>(null);
  const [queryJourneyRunId, setQueryJourneyRunId] = useState<string | null>(null);
  const [feedbackRunId, setFeedbackRunId] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<"positive" | "negative">("negative");
  const [messageFeedback, setMessageFeedback] = useState<Record<string, "positive" | "negative">>({});
  const [isStreaming, setIsStreaming] = useState(false);
  const streamAbortRef = useRef<(() => void) | null>(null);

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

  const capabilitiesQuery = useQuery({
    queryKey: ["capabilities"],
    queryFn: () => getCapabilities(apiKey!),
    enabled: Boolean(apiKey),
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

  const attachableDatasets = useMemo(() => {
    const attachedIds = new Set(attachedDatasets.map((dataset) => dataset.dataset_id));
    return (datasetsQuery.data ?? []).filter((dataset) => !attachedIds.has(dataset.dataset_id));
  }, [attachedDatasets, datasetsQuery.data]);

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

  const modeOptions = useMemo(() => {
    const capabilityModes = capabilitiesQuery.data?.modes ?? FALLBACK_MODE_OPTIONS;
    return capabilityModes;
  }, [agentQuery.data?.allowed_modes, capabilitiesQuery.data?.modes]);

  useEffect(() => {
    if (modeOptions.length === 0) {
      return;
    }

    const selectedOption = modeOptions.find((mode) => mode.mode === selectedMode);
    if (selectedOption?.enabled) {
      return;
    }

    const fallbackMode =
      modeOptions.find((mode) => mode.enabled && mode.mode === agentQuery.data?.default_mode) ??
      modeOptions.find((mode) => mode.enabled) ??
      modeOptions[0];

    if (fallbackMode) {
      setSelectedMode(fallbackMode.mode);
    }
  }, [agentQuery.data?.default_mode, modeOptions, selectedMode]);

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
    if (attachableDatasets.length === 0) {
      setDatasetToAttachId("");
      return;
    }

    const stillSelected = attachableDatasets.some((dataset) => dataset.dataset_id === datasetToAttachId);
    if (!stillSelected) {
      setDatasetToAttachId(attachableDatasets[0].dataset_id);
    }
  }, [attachableDatasets, datasetToAttachId]);

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


  const runStreamingChat = useCallback(
    async (submission: ChatSubmission & { resolvedConversationId: string }) => {
      if (!apiKey || !id) return;

      setIsStreaming(true);
      setWorkflowSteps([]);
      setShowWorkflowPanel(true);

      let aborted = false;
      streamAbortRef.current = () => { aborted = true; };

      try {
        const gen = streamAgentChat(apiKey, id, {
          conversation_id: submission.resolvedConversationId,
          message: submission.message,
          mode: submission.mode,
          dataset_id: submission.datasetId,
        });

        for await (const event of gen) {
          if (aborted) break;

          if (event.type === "step_started") {
            setWorkflowSteps((prev) => {
              if (prev.find((s) => s.step === event.step)) {
                return prev.map((s) =>
                  s.step === event.step ? { ...s, status: "running" } : s,
                );
              }
              return [...prev, { step: event.step, label: event.label, status: "running" }];
            });
          } else if (event.type === "step_completed") {
            setWorkflowSteps((prev) =>
              prev.map((s) =>
                s.step === event.step
                  ? {
                      ...s,
                      status: "completed",
                      durationMs: event.duration_ms,
                      metadata: {
                        ...(event.evidence_count !== undefined ? { evidence_count: event.evidence_count } : {}),
                        ...(event.message_count !== undefined ? { message_count: event.message_count } : {}),
                      },
                    }
                  : s,
              ),
            );
          } else if (event.type === "answer") {
            const response = event.data;
            setActiveRunId(response.run_id);
            setLastStreamedRunId(response.run_id);
            setSelectedConversationId(response.conversation_id);
            setLocalExchange(null);
            setDraft("");

            queryClient.setQueryData<MessageResponse[]>(
              ["conversation", response.conversation_id, "messages"],
              (current = []) => {
                const existingIds = new Set(current.map((m) => m.message_id));
                const next = [...current];
                if (!existingIds.has(response.user_message_id)) {
                  next.push({
                    message_id: response.user_message_id,
                    conversation_id: response.conversation_id,
                    created_by_api_key_id: null,
                    run_id: null,
                    role: "user",
                    content: submission.message,
                    created_at: submission.submittedAt,
                  });
                }
                if (!existingIds.has(response.assistant_message_id)) {
                  next.push({
                    message_id: response.assistant_message_id,
                    conversation_id: response.conversation_id,
                    created_by_api_key_id: null,
                    run_id: response.run_id,
                    role: "assistant",
                    content: response.answer,
                    created_at: new Date().toISOString(),
                  });
                }
                return next;
              },
            );

            void queryClient.invalidateQueries({ queryKey: ["agent", id, "conversations"] });
            void queryClient.invalidateQueries({ queryKey: ["conversation", response.conversation_id, "messages"] });
            void queryClient.invalidateQueries({ queryKey: ["runs"] });
            void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
          } else if (event.type === "error") {
            setLocalExchange((prev) =>
              prev ? { ...prev, status: "error", errorMessage: event.detail } : null,
            );
            toast.error(event.detail);
          }
        }
      } catch (err) {
        if (!aborted) {
          const msg = err instanceof Error ? err.message : "Unable to send the message.";
          setLocalExchange((prev) =>
            prev ? { ...prev, status: "error", errorMessage: msg } : null,
          );
          toast.error(msg);
        }
      } finally {
        streamAbortRef.current = null;
        setIsStreaming(false);
      }
    },
    [apiKey, id, queryClient],
  );

  const availableDatasets = datasetsQuery.data ?? [];
  const conversations = conversationsQuery.data ?? [];
  const messages = messagesQuery.data ?? [];
  const hasActiveRun = localExchange?.status === "pending" || isStreaming;
  const run = runQuery.data;
  const activeConversation =
    conversations.find((conversation) => conversation.conversation_id === selectedConversationId) ?? null;

  const visibleMessages = useMemo<VisibleChatMessage[]>(() => {
    const baseMessages: VisibleChatMessage[] = messages.map((message) => ({
      kind: "server",
      key: message.message_id,
      role: message.role,
      content: message.content,
      createdAt: message.created_at,
      runId: message.run_id,
    }));

    if (!localExchange) {
      return baseMessages;
    }

    if (!isSameConversation(localExchange.conversationId, selectedConversationId, messages.length > 0)) {
      return baseMessages;
    }

    return [
      ...baseMessages,
      {
        kind: "optimistic-user",
        key: localExchange.tempUserId,
        role: "user",
        content: localExchange.message,
        createdAt: localExchange.submittedAt,
        runId: null,
      },
      localExchange.status === "pending"
        ? {
            kind: "pending",
            key: localExchange.tempAssistantId,
            role: "assistant",
            content: "",
            createdAt: localExchange.submittedAt,
            runId: null,
            isPending: true,
          }
        : {
            kind: "error",
            key: localExchange.tempAssistantId,
            role: "assistant",
            content: localExchange.errorMessage ?? "Unable to send the message.",
            createdAt: localExchange.submittedAt,
            runId: null,
            isError: true,
            retryLabel: "Retry last message",
          },
    ];
  }, [localExchange, messages, selectedConversationId]);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [visibleMessages.length, localExchange?.status, selectedConversationId]);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.();
    };
  }, []);

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

  function prepareSubmission(messageText: string): ChatSubmission | null {
    if (!apiKey || !id || !agentQuery.data) {
      toast.error("Agent chat is unavailable until the agent is loaded.");
      return null;
    }

    if (hasActiveRun) {
      toast("Please wait for the current response to finish.");
      return null;
    }

    if (agentQuery.data.dataset_ids.length === 0) {
      toast.error("Attach a dataset to this agent before chatting.");
      return null;
    }

    const message = messageText.trim();
    if (!message) {
      return null;
    }

    const datasetId =
      agentQuery.data.dataset_ids.length === 1
        ? agentQuery.data.dataset_ids[0]
        : selectedDatasetId || undefined;

    if (!datasetId) {
      toast.error("Select which attached dataset should answer this question.");
      return null;
    }

    const nonce = `${Date.now()}`;
    return {
      tempUserId: `temp-user-${nonce}`,
      tempAssistantId: `temp-assistant-${nonce}`,
      conversationId: selectedConversationId,
      conversationTitle: activeConversation?.title || message.slice(0, 64) || "New conversation",
      message,
      mode: selectedMode,
      datasetId,
      submittedAt: new Date().toISOString(),
    };
  }

  function submitMessage(messageText: string) {
    const submission = prepareSubmission(messageText);
    if (!submission) return;

    setDraft("");

    if (!submission.conversationId) {
      createConversationMutation.mutate(submission.conversationTitle, {
        onSuccess: (conversation) => {
          const resolvedSubmission = { ...submission, conversationId: conversation.conversation_id };
          setLocalExchange({ ...resolvedSubmission, status: "pending" });
          void runStreamingChat({ ...resolvedSubmission, resolvedConversationId: conversation.conversation_id });
        },
        onError: (error) => {
          const msg = error instanceof Error ? error.message : "Unable to create conversation.";
          toast.error(msg);
        },
      });
    } else {
      setLocalExchange({ ...submission, status: "pending" });
      void runStreamingChat({ ...submission, resolvedConversationId: submission.conversationId });
    }
  }

  function retryLastMessage() {
    if (!localExchange || localExchange.status !== "error" || !localExchange.conversationId) {
      return;
    }

    const retrySubmission: ChatSubmission = {
      tempUserId: `temp-user-${Date.now()}`,
      tempAssistantId: `temp-assistant-${Date.now()}`,
      conversationId: localExchange.conversationId,
      conversationTitle: localExchange.conversationTitle,
      message: localExchange.message,
      mode: localExchange.mode,
      datasetId: localExchange.datasetId,
      submittedAt: new Date().toISOString(),
    };

    setLocalExchange({ ...retrySubmission, status: "pending" });
    void runStreamingChat({ ...retrySubmission, resolvedConversationId: localExchange.conversationId });
  }

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
            disabled={createConversationMutation.isPending || hasActiveRun}
          >
            <Plus className="mr-1 h-3.5 w-3.5" /> New Chat
          </Button>

          <div>
            <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Attached datasets</div>
            <div className="space-y-3">
              {attachedDatasets.length === 0 ? (
                <div className="text-xs leading-5 text-muted-foreground">
                  Attach a dataset before sending grounded questions.
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

              {availableDatasets.length > 0 ? (
                attachableDatasets.length > 0 ? (
                  <div className="rounded-2xl border bg-background/70 p-3">
                    <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      Attach more datasets
                    </div>
                    <div className="flex flex-col gap-2">
                      <select
                        value={datasetToAttachId}
                        onChange={(event) => setDatasetToAttachId(event.target.value)}
                        className="h-10 rounded-xl border bg-background px-3 text-sm text-foreground"
                        disabled={attachDatasetMutation.isPending || hasActiveRun}
                      >
                        {attachableDatasets.map((dataset) => (
                          <option key={dataset.dataset_id} value={dataset.dataset_id}>
                            {dataset.name}
                          </option>
                        ))}
                      </select>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="w-full rounded-2xl"
                        onClick={() => datasetToAttachId && attachDatasetMutation.mutate(datasetToAttachId)}
                        disabled={attachDatasetMutation.isPending || !datasetToAttachId || hasActiveRun}
                      >
                        <Database className="mr-2 h-3.5 w-3.5" />
                        {attachDatasetMutation.isPending ? "Attaching..." : "Attach selected dataset"}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border bg-background px-3 py-2.5 text-xs text-muted-foreground">
                    All workspace datasets are already attached to this agent.
                  </div>
                )
              ) : (
                <Link
                  to={workspacePath(workspaceSlug, "/datasets")}
                  className="text-xs text-accent hover:underline"
                >
                  Create a dataset first
                </Link>
              )}
            </div>
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
                disabled={hasActiveRun}
                className={`mb-1.5 w-full rounded-xl px-3 py-2.5 text-left transition-colors ${
                  selectedConversationId === conversation.conversation_id
                    ? "bg-accent/10 text-foreground"
                    : "text-muted-foreground hover:bg-secondary/70"
                } ${hasActiveRun ? "cursor-not-allowed opacity-70" : ""}`}
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

      <section className="min-w-0 flex flex-col bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(248,250,252,0.88))]">
        <div className="shrink-0 border-b bg-white/80 px-6 py-4 backdrop-blur">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4">
            <div className="min-w-0">
              <h2 className="truncate font-display text-xl font-semibold tracking-[-0.03em] text-foreground">
                {activeConversation?.title || localExchange?.conversationTitle || "New conversation"}
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>{agent.name}</span>
                <span>•</span>
                <span>{attachedDatasets.length} dataset{attachedDatasets.length === 1 ? "" : "s"} attached</span>
                {hasActiveRun ? (
                  <span className="inline-flex items-center gap-1.5 text-accent">
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                    Generating answer
                  </span>
                ) : null}
              </div>
            </div>
            <Badge variant="outline" className="hidden text-[10px] sm:inline-flex">
              Grounded chat
            </Badge>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-[linear-gradient(180deg,hsl(214_32%_98%),hsl(0_0%_100%))]">
          <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col px-6 py-8">
            {messagesQuery.isLoading && selectedConversationId ? (
              <div className="text-sm text-muted-foreground">Loading conversation...</div>
            ) : visibleMessages.length === 0 ? (
              <div className="flex flex-1 items-center justify-center">
                <EmptyPanel
                  icon={Sparkles}
                  title="Ask something grounded"
                  description="Send a question and we’ll show your message immediately, keep the thread active while the agent works, and return a citation-backed answer when the run finishes."
                  to={workspacePath(workspaceSlug, "/datasets")}
                  actionLabel={attachedDatasets.length === 0 ? "Open datasets" : "Review datasets"}
                />
              </div>
            ) : (
              <div className="space-y-7 pb-4">
                {visibleMessages.map((message) => {
                  const isAssistant = message.role === "assistant";

                  if (isAssistant) {
                    return (
                      <div key={message.key} className="flex justify-start animate-fade-up">
                        <div className="w-full max-w-3xl">
                          <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                            <Bot className="h-3.5 w-3.5 text-accent" />
                            <span>{agent.name}</span>
                            {message.isPending ? (
                              <Badge variant="outline" className="h-6 rounded-full px-2 text-[10px]">
                                Working
                              </Badge>
                            ) : null}
                            {message.isError ? (
                              <Badge variant="warning" className="h-6 rounded-full px-2 text-[10px]">
                                Needs retry
                              </Badge>
                            ) : null}
                          </div>
                          <div
                            className={`w-full rounded-[28px] border px-6 py-5 text-left shadow-sm transition-all ${
                              message.isPending
                                ? "border-accent/20 bg-card/90 shadow-[0_18px_45px_rgba(59,130,246,0.08)]"
                                : message.isError
                                  ? "border-destructive/20 bg-card"
                                  : "bg-card hover:border-accent/40"
                            }`}
                          >
                            {message.isPending ? (
                              <div className="space-y-3">
                                <TypingIndicator />
                                {workflowSteps.length > 0 ? (
                                  <div className="mt-3 space-y-2">
                                    {workflowSteps.map((step) => {
                                      const isRunning = step.status === "running";
                                      const isCompleted = step.status === "completed";
                                      return (
                                        <div key={step.step} className="flex items-center gap-2 text-xs">
                                          {isRunning ? (
                                            <LoaderCircle className="h-3.5 w-3.5 animate-spin text-blue-400 shrink-0" />
                                          ) : isCompleted ? (
                                            <svg viewBox="0 0 12 12" className="h-3.5 w-3.5 shrink-0 text-emerald-500" fill="none">
                                              <path d="M2 6 L5 9 L10 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                          ) : (
                                            <div className="h-3.5 w-3.5 shrink-0 rounded-full border border-border" />
                                          )}
                                          <span className={isRunning ? "text-foreground font-medium" : isCompleted ? "text-muted-foreground" : "text-muted-foreground/50"}>
                                            {step.label}
                                            {step.step === "research" && isCompleted && step.metadata?.evidence_count !== undefined && (
                                              <span className="ml-1 text-muted-foreground">
                                                — {String(step.metadata.evidence_count)} piece{Number(step.metadata.evidence_count) !== 1 ? "s" : ""} of evidence
                                              </span>
                                            )}
                                          </span>
                                          {isCompleted && step.durationMs !== undefined && (
                                            <span className="ml-auto text-[10px] text-muted-foreground/60">
                                              {step.durationMs >= 1000 ? `${(step.durationMs / 1000).toFixed(2)}s` : `${step.durationMs}ms`}
                                            </span>
                                          )}
                                        </div>
                                      );
                                    })}
                                    <button
                                      type="button"
                                      onClick={() => setShowWorkflowPanel(true)}
                                      className="mt-1 flex items-center gap-1 text-[11px] text-accent hover:underline"
                                    >
                                      <GitMerge className="h-3 w-3" />
                                      View Workflow Progress
                                    </button>
                                  </div>
                                ) : (
                                  <AssistantStatusCopy submittedAt={message.createdAt} />
                                )}
                              </div>
                            ) : message.isError ? (
                              <div className="space-y-4">
                                <div className="flex items-start gap-3 rounded-2xl border border-destructive/10 bg-destructive/5 px-4 py-3 text-destructive">
                                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                                  <div className="min-w-0">
                                    <p className="text-sm font-medium text-foreground">We couldn’t complete that run.</p>
                                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{message.content}</p>
                                  </div>
                                </div>
                                <div className="flex flex-wrap items-center gap-3">
                                  <Button
                                    type="button"
                                    variant="outline"
                                    className="rounded-full"
                                    onClick={retryLastMessage}
                                    disabled={hasActiveRun}
                                  >
                                    <RefreshCw className="mr-2 h-3.5 w-3.5" />
                                    {message.retryLabel}
                                  </Button>
                                  <span className="text-[11px] text-muted-foreground">
                                    You can also edit the prompt and resend once you’re ready.
                                  </span>
                                </div>
                              </div>
                            ) : (
                              <>
                                <div className="prose prose-sm max-w-none text-foreground [&_p]:leading-8 [&_p]:text-[15px] [&_li]:text-[15px] [&_li]:leading-7 [&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base [&_strong]:text-foreground [&_code]:rounded [&_code]:bg-secondary [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-sm [&_pre]:rounded-xl [&_pre]:bg-secondary [&_pre]:p-4 [&_blockquote]:border-l-accent [&_a]:text-accent">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {message.content}
                                  </ReactMarkdown>
                                </div>

                                {/* Inline workflow steps preview — only on the latest streamed message */}
                                {message.runId && message.runId === lastStreamedRunId && workflowSteps.length > 0 && (
                                  <button
                                    type="button"
                                    onClick={() => setShowWorkflowPanel(true)}
                                    className="mt-4 w-full rounded-2xl border border-border/60 bg-secondary/30 px-4 py-3 text-left hover:border-accent/30 hover:bg-secondary/50 transition-all group"
                                  >
                                    <div className="mb-2 flex items-center justify-between">
                                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Pipeline Execution</span>
                                      <span className="text-[10px] text-accent opacity-0 group-hover:opacity-100 transition-opacity">View full diagram →</span>
                                    </div>
                                    {/* Row 1: first 3 steps */}
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      {workflowSteps.slice(0, 3).map((step, i) => (
                                        <div key={step.step} className="flex items-center gap-1.5">
                                          <div className="flex items-center gap-1.5 rounded-xl border border-border/80 bg-background px-2.5 py-1.5">
                                            <div className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50">
                                              <svg viewBox="0 0 12 12" className="h-2.5 w-2.5 text-emerald-600" fill="none">
                                                <path d="M2 6 L5 9 L10 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                              </svg>
                                            </div>
                                            <span className="text-[11px] font-medium text-foreground">{step.label}</span>
                                            {step.durationMs !== undefined && (
                                              <span className="text-[10px] text-muted-foreground">
                                                {step.durationMs >= 1000 ? `${(step.durationMs / 1000).toFixed(2)}s` : `${step.durationMs}ms`}
                                              </span>
                                            )}
                                          </div>
                                          {i < 2 && (
                                            <svg width="16" height="10" viewBox="0 0 16 10" fill="none" className="shrink-0 text-muted-foreground/40">
                                              <path d="M0 5 H12 M9 2 L13 5 L9 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                                            </svg>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                    {/* Row 2: remaining steps */}
                                    {workflowSteps.length > 3 && (
                                      <div className="mt-1.5 flex items-center gap-1.5 pl-6">
                                        <svg width="10" height="16" viewBox="0 0 10 16" fill="none" className="shrink-0 text-muted-foreground/40">
                                          <path d="M5 0 V12 M2 9 L5 13 L8 9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                                        </svg>
                                        {workflowSteps.slice(3).map((step, i) => (
                                          <div key={step.step} className="flex items-center gap-1.5">
                                            <div className="flex items-center gap-1.5 rounded-xl border border-border/80 bg-background px-2.5 py-1.5">
                                              <div className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50">
                                                <svg viewBox="0 0 12 12" className="h-2.5 w-2.5 text-emerald-600" fill="none">
                                                  <path d="M2 6 L5 9 L10 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                                </svg>
                                              </div>
                                              <span className="text-[11px] font-medium text-foreground">{step.label}</span>
                                              {step.durationMs !== undefined && (
                                                <span className="text-[10px] text-muted-foreground">
                                                  {step.durationMs >= 1000 ? `${(step.durationMs / 1000).toFixed(2)}s` : `${step.durationMs}ms`}
                                                </span>
                                              )}
                                            </div>
                                            {i < workflowSteps.slice(3).length - 1 && (
                                              <svg width="16" height="10" viewBox="0 0 16 10" fill="none" className="shrink-0 text-muted-foreground/40">
                                                <path d="M0 5 H12 M9 2 L13 5 L9 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                                              </svg>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </button>
                                )}

                                {/* Action bar */}
                                <div className="mt-3 flex items-center justify-between">
                                  <div className="flex items-center gap-0.5">
                                    {/* Thumbs up */}
                                    <button
                                      type="button"
                                      title="Good response"
                                      onClick={async () => {
                                        if (!message.runId || !apiKey) return;
                                        const prev = messageFeedback[message.runId];
                                        if (prev === "positive") return;
                                        setMessageFeedback((m) => ({ ...m, [message.runId!]: "positive" }));
                                        try {
                                          await submitFeedback(apiKey, message.runId, { rating: "positive", reasons: [], freeform_text: null });
                                          toast.success("Thanks for the feedback!");
                                        } catch {
                                          setMessageFeedback((m) => { const n = { ...m }; delete n[message.runId!]; return n; });
                                        }
                                      }}
                                      className={`rounded p-1.5 transition-colors ${messageFeedback[message.runId ?? ""] === "positive" ? "text-emerald-600" : "text-muted-foreground hover:text-foreground hover:bg-secondary"}`}
                                    >
                                      <ThumbsUp className="h-3.5 w-3.5" />
                                    </button>
                                    {/* Thumbs down */}
                                    <button
                                      type="button"
                                      title="Bad response"
                                      onClick={() => {
                                        if (!message.runId) return;
                                        setFeedbackRating("negative");
                                        setFeedbackRunId(message.runId);
                                      }}
                                      className={`rounded p-1.5 transition-colors ${messageFeedback[message.runId ?? ""] === "negative" ? "text-destructive" : "text-muted-foreground hover:text-foreground hover:bg-secondary"}`}
                                    >
                                      <ThumbsDown className="h-3.5 w-3.5" />
                                    </button>
                                    {/* Flag */}
                                    <button
                                      type="button"
                                      title="Flag this response"
                                      onClick={() => {
                                        if (!message.runId) return;
                                        setFeedbackRating("negative");
                                        setFeedbackRunId(message.runId);
                                      }}
                                      className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                                    >
                                      <Flag className="h-3.5 w-3.5" />
                                    </button>

                                    <div className="mx-1.5 h-4 w-px bg-border" />

                                    {/* Copy */}
                                    <CopyButton text={message.content} />

                                    {/* Retry */}
                                    <button
                                      type="button"
                                      title="Retry"
                                      onClick={retryLastMessage}
                                      disabled={hasActiveRun}
                                      className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors disabled:opacity-40"
                                    >
                                      <RefreshCw className="h-3.5 w-3.5" />
                                    </button>

                                    {/* Share */}
                                    <button
                                      type="button"
                                      title="Share"
                                      className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                                      onClick={() => {
                                        void navigator.clipboard?.writeText(window.location.href);
                                        toast.success("Link copied!");
                                      }}
                                    >
                                      <Share2 className="h-3.5 w-3.5" />
                                    </button>

                                    <div className="mx-1.5 h-4 w-px bg-border" />

                                    {/* Inspect run */}
                                    {message.runId && (
                                      <button
                                        type="button"
                                        onClick={() => setActiveRunId(message.runId)}
                                        className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                                        title="Inspect run"
                                      >
                                        <FileSearch className="h-3.5 w-3.5" />
                                      </button>
                                    )}

                                    {/* Query Journey */}
                                    {message.runId && (
                                      <button
                                        type="button"
                                        title="Query Journey"
                                        onClick={() => {
                                          setActiveRunId(message.runId);
                                          setQueryJourneyRunId(message.runId);
                                        }}
                                        className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                                      >
                                        <GitMerge className="h-3.5 w-3.5" />
                                      </button>
                                    )}
                                  </div>
                                  <span className="text-[10px] text-muted-foreground">
                                    {formatRelativeOrDate(message.createdAt)}
                                  </span>
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div key={message.key} className="flex justify-end animate-fade-up">
                      <div className="max-w-2xl">
                        <div className="rounded-[28px] border border-accent/20 bg-[linear-gradient(135deg,hsl(217_91%_55%/0.08),hsl(0_0%_100%/0.96))] px-6 py-4 text-foreground shadow-[0_8px_24px_rgba(15,23,42,0.08)]">
                          <p className="whitespace-pre-line text-[15px] leading-7">{message.content}</p>
                          <div className="mt-3 text-right text-[10px] text-muted-foreground">
                            {formatRelativeOrDate(message.createdAt)}
                          </div>
                        </div>
                        {message.kind === "optimistic-user" && hasActiveRun ? (
                          <div className="mt-2 flex items-center justify-end gap-2 pr-3 text-[11px] text-muted-foreground">
                            <div className="flex items-center gap-1.5">
                              <span className="chat-typing-dot" />
                              <span className="chat-typing-dot [animation-delay:0.16s]" />
                              <span className="chat-typing-dot [animation-delay:0.32s]" />
                            </div>
                            <span>Thinking</span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
                <div ref={scrollAnchorRef} />
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 border-t bg-white/88 px-6 py-4 backdrop-blur">
          <div className="mx-auto w-full max-w-5xl rounded-[30px] border border-border/80 bg-white/96 p-4 shadow-[0_24px_60px_rgba(15,23,42,0.08)]">
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a grounded question..."
              aria-busy={hasActiveRun}
              className="min-h-[96px] resize-none border-0 bg-transparent px-2 py-2 text-base shadow-none focus-visible:ring-0"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (hasActiveRun) {
                    toast("Please wait for the current response to finish.");
                    return;
                  }
                  submitMessage(draft);
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
                    disabled={hasActiveRun}
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
                {modeOptions.map((mode) => {
                  const allowedModes = new Set(agentQuery.data?.allowed_modes ?? []);
                  const agentAllowsMode =
                    allowedModes.size === 0 || allowedModes.has(mode.mode);
                  const modeIsSelectable = mode.enabled && agentAllowsMode;
                  const disabledReason = !mode.enabled
                    ? mode.description
                    : agentAllowsMode
                      ? undefined
                      : "Enable this mode for the agent before using it in chat.";

                  return (
                    <button
                      key={mode.mode}
                      type="button"
                      onClick={() => modeIsSelectable && setSelectedMode(mode.mode)}
                      disabled={!modeIsSelectable || hasActiveRun}
                      title={disabledReason}
                      className={`rounded-full px-4 py-2 text-xs font-medium transition-all ${
                        selectedMode === mode.mode
                          ? "bg-accent text-accent-foreground"
                          : modeIsSelectable
                            ? "border border-border bg-background text-foreground hover:bg-secondary"
                            : "border border-border bg-background text-muted-foreground/40 cursor-not-allowed"
                      } ${hasActiveRun && modeIsSelectable ? "opacity-60" : ""}`}
                    >
                      {mode.label}
                      {!mode.enabled ? <span className="ml-1 text-[9px]">soon</span> : null}
                    </button>
                  );
                })}
                <Button
                  variant="pill-accent"
                  size="icon"
                  className="h-11 w-11 rounded-full"
                  disabled={!draft.trim() || hasActiveRun}
                  onClick={() => submitMessage(draft)}
                >
                  {hasActiveRun ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <aside className="hidden overflow-y-auto border-l bg-card/90 xl:block">
          <>
        <div className="border-b p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Answer Inspector</h3>
            {workflowSteps.length > 0 && (
              <button
                type="button"
                onClick={() => setShowWorkflowPanel(true)}
                className="flex items-center gap-1 rounded-full border border-border px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground"
              >
                <GitMerge className="h-3 w-3" /> Workflow
              </button>
            )}
          </div>
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
                <div className="flex items-center gap-2">
                  <span className="text-foreground">{Math.round(run.confidence_score * 100)}%</span>
                  <Badge variant={confidenceBadgeVariant(run.confidence_label)} className="text-[10px]">
                    {confidenceLabelText(run.confidence_label)}
                  </Badge>
                </div>
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
                <span className="max-w-[180px] truncate text-right text-foreground">
                  {providerDisplayText(run)}
                </span>
              </div>
            </div>

            <div className="border-b p-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Routing</h4>
              <p className="text-xs leading-6 text-muted-foreground">{run.routing_reason}</p>
              <div className="mt-3 rounded-xl border bg-secondary/20 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Support summary
                </div>
                <p className="mt-2 text-xs leading-6 text-foreground">
                  {supportSummaryText(run.support_summary)}
                </p>
              </div>
              {run.degraded_reasons.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {run.degraded_reasons.map((reason) => (
                    <div key={reason} className="rounded-xl border border-amber-200/70 bg-amber-50/70 p-3 text-xs">
                      <div className="font-medium text-amber-900">{sentenceCase(reason)}</div>
                      <div className="mt-1 leading-5 text-amber-800">{degradedReasonDescription(reason)}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="p-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Citations</h4>
              <div className="space-y-3">
                {run.citations.length === 0 ? (
                  <div className="text-xs text-muted-foreground">
                    No citations were returned because this run stayed in clarification or degraded mode.
                  </div>
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
          </>
      </aside>

      {queryJourneyRunId && runQuery.data && String(runQuery.data.run_id) === queryJourneyRunId ? (
        <QueryJourneyModal
          run={runQuery.data}
          onClose={() => setQueryJourneyRunId(null)}
        />
      ) : queryJourneyRunId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="flex h-24 w-48 items-center justify-center rounded-2xl border bg-background shadow-lg">
            <LoaderCircle className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        </div>
      ) : null}

      {showWorkflowPanel && workflowSteps.length > 0 && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setShowWorkflowPanel(false)}
        >
          <div
            className="relative flex h-[580px] w-full max-w-[860px] flex-col overflow-hidden rounded-3xl border bg-background shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <WorkflowStepsPanel
              steps={workflowSteps}
              onClose={() => setShowWorkflowPanel(false)}
            />
          </div>
        </div>
      )}

      {feedbackRunId && (
        <FeedbackModal
          runId={feedbackRunId}
          initialRating={feedbackRating}
          onSubmit={async (feedback: FeedbackSubmission) => {
            if (!apiKey) return;
            await submitFeedback(apiKey, feedbackRunId, feedback);
            setMessageFeedback((m) => ({ ...m, [feedbackRunId]: feedback.rating }));
            toast.success("Thank you for your feedback!");
          }}
          onClose={() => setFeedbackRunId(null)}
        />
      )}
    </div>
  );
}
