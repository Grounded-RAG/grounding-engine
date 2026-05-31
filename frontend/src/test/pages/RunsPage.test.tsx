import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import RunsPage from "@/pages/RunsPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ apiKey: "grd_test_key" }),
}));

vi.mock("@/lib/api", () => ({
  listRuns: vi.fn().mockResolvedValue([]),
  getRun: vi.fn().mockResolvedValue(null),
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
        <RunsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const MOCK_RUN = {
  trace_id: "trace-1",
  query: "What is grounded evidence?",
  answer: "Grounded evidence is verifiable.",
  citations: [],
  confidence_score: 0.9,
  confidence_label: "high",
  support_summary: "grounded",
  verification_status: "passed",
  degraded_reasons: [],
  generator_provider: "local-grounded-v1",
  provider_backend: "local_grounded_v1",
  provider_model: null,
  provider_fallback_used: false,
  provider_fallback_from: null,
  created_at: new Date().toISOString(),
  total_latency_ms: 120,
  effective_tier: "standard",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("RunsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the page heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/runs/i)).toBeInTheDocument();
    });
  });

  it("renders the search input", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search runs/i)).toBeInTheDocument();
    });
  });

  it("shows runs returned from the API", async () => {
    const { listRuns } = await import("@/lib/api");
    vi.mocked(listRuns).mockResolvedValueOnce([MOCK_RUN] as never);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/what is grounded evidence/i)).toBeInTheDocument();
    });
  });

  it("filters runs by search text", async () => {
    const { listRuns } = await import("@/lib/api");
    vi.mocked(listRuns).mockResolvedValueOnce([
      { ...MOCK_RUN, trace_id: "trace-1", query: "What is grounded evidence?" },
      { ...MOCK_RUN, trace_id: "trace-2", query: "How does retrieval work?" },
    ] as never);

    renderPage();
    await screen.findByText(/what is grounded evidence/i);

    const input = screen.getByPlaceholderText(/search runs/i);
    fireEvent.change(input, { target: { value: "retrieval" } });

    await waitFor(() => {
      expect(screen.getByText(/how does retrieval work/i)).toBeInTheDocument();
      expect(screen.queryByText(/what is grounded evidence/i)).not.toBeInTheDocument();
    });
  });

  it("shows empty state when no runs exist", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });
});
