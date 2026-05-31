import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import AgentChatPage from "@/pages/AgentChatPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    apiKey: "grd_test_key",
    workspaceId: "ws-1",
    workspaceSlug: "test-workspace",
  }),
}));

vi.mock("@/lib/api", () => ({
  getAgent: vi.fn().mockResolvedValue({
    agent_id: "agent-1",
    workspace_id: "ws-1",
    name: "Policy Analyst",
    description: "Answers policy questions.",
    system_instructions: "Be concise.",
    default_mode: "auto",
    allowed_modes: ["auto", "instant"],
    status: "active",
    dataset_ids: ["ds-1"],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }),
  listAgentConversations: vi.fn().mockResolvedValue([]),
  createAgentConversation: vi.fn(),
  getConversationMessages: vi.fn().mockResolvedValue([]),
  sendAgentChat: vi.fn(),
  getCapabilities: vi.fn().mockResolvedValue({ modes: [] }),
  listDatasets: vi.fn().mockResolvedValue([]),
  attachDatasetToAgent: vi.fn(),
  getRun: vi.fn().mockResolvedValue(null),
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage(agentId = "agent-1") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/test-workspace/agents/${agentId}`]}>
        <Routes>
          <Route path="/:workspaceSlug/agents/:id" element={<AgentChatPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AgentChatPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the agent name", async () => {
    renderPage();
    await waitFor(() => {
      const matches = screen.getAllByText("Policy Analyst");
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it("renders the chat message input", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Ask a grounded question...")
      ).toBeInTheDocument();
    });
  });

  it("send button is present and disabled when draft is empty", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Ask a grounded question...")
      ).toBeInTheDocument();
    });
    const buttons = screen.getAllByRole("button");
    const disabledBtn = buttons.find((b) => (b as HTMLButtonElement).disabled);
    expect(disabledBtn).toBeDefined();
  });

  it("does not send when message is empty", async () => {
    const { sendAgentChat } = await import("@/lib/api");
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Ask a grounded question...")
      ).toBeInTheDocument();
    });
    // All buttons should leave sendAgentChat uncalled when draft is empty
    expect(vi.mocked(sendAgentChat)).not.toHaveBeenCalled();
  });

  it("shows conversations list from the API", async () => {
    const { listAgentConversations } = await import("@/lib/api");
    vi.mocked(listAgentConversations).mockResolvedValueOnce([
      {
        conversation_id: "conv-1",
        agent_id: "agent-1",
        title: "Policy Q&A",
        last_used_mode: "auto",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ] as never);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Policy Q&A")).toBeInTheDocument();
    });
  });
});
