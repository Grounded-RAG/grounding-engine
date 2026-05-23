import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import AgentsPage from "@/pages/AgentsPage";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    apiKey: "grd_test_key",
    workspaceId: "ws-1",
    workspaceSlug: "test-workspace",
  }),
}));

vi.mock("@/lib/api", () => ({
  listAgents: vi.fn().mockResolvedValue([]),
  listDatasets: vi.fn().mockResolvedValue([]),
  getCapabilities: vi.fn().mockResolvedValue({ modes: [] }),
  createAgent: vi.fn(),
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AgentsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the page heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    });
  });

  it("shows empty state when no agents are returned", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });

  it("renders a create-agent button", async () => {
    renderPage();
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /new agent|create agent/i });
      expect(btn).toBeInTheDocument();
    });
  });

  it("shows the create form when the new agent button is clicked", async () => {
    renderPage();
    const btn = await screen.findByRole("button", { name: /new agent|create agent/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/policy analyst/i) ||
        screen.getByLabelText(/name/i)
      ).toBeInTheDocument();
    });
  });

  it("renders search input", async () => {
    renderPage();
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/search agents/i);
      expect(input).toBeInTheDocument();
    });
  });

  it("shows agents returned from the API", async () => {
    const { listAgents } = await import("@/lib/api");
    vi.mocked(listAgents).mockResolvedValueOnce([
      {
        agent_id: "agent-1",
        workspace_id: "ws-1",
        name: "Policy Analyst",
        description: "Answers policy questions",
        system_instructions: "Be concise.",
        default_mode: "auto",
        allowed_modes: ["auto"],
        status: "active",
        dataset_ids: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ] as never);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Policy Analyst")).toBeInTheDocument();
    });
  });
});
