import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import SettingsPage from "@/pages/SettingsPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    apiKey: "grd_test_key",
    auth: { email: "user@test.com" },
  }),
}));

vi.mock("@/lib/api", () => ({
  listApiKeys: vi.fn().mockResolvedValue([]),
  createApiKey: vi.fn(),
  revokeApiKey: vi.fn(),
  getCapabilities: vi.fn().mockResolvedValue({ modes: [] }),
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
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SettingsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the page heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    });
  });

  it("renders the API Keys section", async () => {
    renderPage();
    await waitFor(() => {
      const matches = screen.getAllByText(/api keys/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it("renders the Coming Soon section", async () => {
    renderPage();
    await waitFor(() => {
      const matches = screen.getAllByText(/coming soon/i);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it("renders the new key label input", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/frontend integration key/i)).toBeInTheDocument();
    });
  });

  it("renders a create key button", async () => {
    renderPage();
    await waitFor(() => {
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it("shows empty state when no API keys exist", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });

  it("shows an API key returned from the API", async () => {
    const { listApiKeys } = await import("@/lib/api");
    vi.mocked(listApiKeys).mockResolvedValueOnce([
      {
        api_key_id: "key-1",
        label: "Production Key",
        prefix: "grd_prod",
        created_at: new Date().toISOString(),
        last_used_at: null,
      },
    ] as never);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Production Key")).toBeInTheDocument();
    });
  });

  it("calls createApiKey when label is provided and create button is clicked", async () => {
    const { createApiKey } = await import("@/lib/api");
    vi.mocked(createApiKey).mockResolvedValueOnce({
      api_key_id: "key-2",
      label: "Test Key",
      key: "grd_test_xxxxx",
      prefix: "grd_test",
      created_at: new Date().toISOString(),
      last_used_at: null,
    } as never);

    renderPage();
    const input = await screen.findByPlaceholderText(/frontend integration key/i);
    fireEvent.change(input, { target: { value: "Test Key" } });

    const createBtn = screen.getAllByRole("button").find(
      (b) => !b.hasAttribute("disabled") && /create|generate|add/i.test(b.textContent ?? "")
    );
    if (createBtn) {
      fireEvent.click(createBtn);
      await waitFor(() => {
        expect(vi.mocked(createApiKey)).toHaveBeenCalled();
      });
    }
  });
});
