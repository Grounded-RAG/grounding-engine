import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import DatasetsPage from "@/pages/DatasetsPage";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    apiKey: "grd_test_key",
    workspaceId: "ws-1",
    workspaceSlug: "test-workspace",
  }),
}));

vi.mock("@/lib/api", () => ({
  listDatasets: vi.fn().mockResolvedValue([]),
  createDataset: vi.fn(),
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DatasetsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("DatasetsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the page heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    });
  });

  it("renders a new dataset button", async () => {
    renderPage();
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /new dataset|create dataset/i });
      expect(btn).toBeInTheDocument();
    });
  });

  it("renders the search input", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search datasets/i)).toBeInTheDocument();
    });
  });

  it("shows the create form when the new dataset button is clicked", async () => {
    renderPage();
    const btn = await screen.findByRole("button", { name: /new dataset|create dataset/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/policy library/i) ||
        screen.getByLabelText(/name/i)
      ).toBeInTheDocument();
    });
  });

  it("shows datasets returned from the API", async () => {
    const { listDatasets } = await import("@/lib/api");
    vi.mocked(listDatasets).mockResolvedValueOnce([
      {
        dataset_id: "ds-1",
        workspace_id: "ws-1",
        name: "Compliance Docs",
        domain: "compliance",
        sensitivity_level: "internal",
        freshness_profile: "balanced",
        min_execution_tier: "standard",
        allow_web_fallback: false,
        allow_internal_model_retrieval: false,
        created_at: new Date().toISOString(),
      },
    ] as never);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Compliance Docs")).toBeInTheDocument();
    });
  });

  it("filters datasets by search input", async () => {
    const { listDatasets } = await import("@/lib/api");
    vi.mocked(listDatasets).mockResolvedValueOnce([
      {
        dataset_id: "ds-1",
        workspace_id: "ws-1",
        name: "Compliance Docs",
        domain: "compliance",
        sensitivity_level: "internal",
        freshness_profile: "balanced",
        min_execution_tier: "standard",
        allow_web_fallback: false,
        allow_internal_model_retrieval: false,
        created_at: new Date().toISOString(),
      },
      {
        dataset_id: "ds-2",
        workspace_id: "ws-1",
        name: "HR Handbook",
        domain: "hr",
        sensitivity_level: "internal",
        freshness_profile: "balanced",
        min_execution_tier: "standard",
        allow_web_fallback: false,
        allow_internal_model_retrieval: false,
        created_at: new Date().toISOString(),
      },
    ] as never);

    renderPage();
    await screen.findByText("Compliance Docs");

    const searchInput = screen.getByPlaceholderText(/search datasets/i);
    fireEvent.change(searchInput, { target: { value: "HR" } });

    await waitFor(() => {
      expect(screen.getByText("HR Handbook")).toBeInTheDocument();
      expect(screen.queryByText("Compliance Docs")).not.toBeInTheDocument();
    });
  });
});
