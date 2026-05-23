import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import DatasetDetailPage from "@/pages/DatasetDetailPage";

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
  getDataset: vi.fn().mockResolvedValue({
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
  }),
  listDatasetDocuments: vi.fn().mockResolvedValue([]),
  listDatasetJobs: vi.fn().mockResolvedValue([]),
  uploadDatasetDocument: vi.fn(),
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

function renderPage(datasetId = "ds-1") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/test-workspace/datasets/${datasetId}`]}>
        <Routes>
          <Route path="/:workspaceSlug/datasets/:id" element={<DatasetDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("DatasetDetailPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the dataset name", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Compliance Docs")).toBeInTheDocument();
    });
  });

  it("renders the file upload area", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
    });
  });

  it("renders the optional title input", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/policy update memo/i)).toBeInTheDocument();
    });
  });

  it("renders the browse files button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/browse files/i)).toBeInTheDocument();
    });
  });

  it("shows empty ingestion job state when no jobs exist", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/no ingestion jobs yet/i)).toBeInTheDocument();
    });
  });

  it("shows uploaded document when documents are returned from API", async () => {
    const { listDatasetDocuments } = await import("@/lib/api");
    vi.mocked(listDatasetDocuments).mockResolvedValueOnce([
      {
        document_id: "doc-1",
        dataset_id: "ds-1",
        title: "Policy Manual 2024",
        filename: "policy-manual.pdf",
        mime_type: "application/pdf",
        file_size_bytes: 12345,
        status: "indexed",
        created_at: new Date().toISOString(),
      },
    ] as never);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Policy Manual 2024")).toBeInTheDocument();
    });
  });
});
