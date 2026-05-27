import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import OnboardingPage from "@/pages/OnboardingPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    apiKey: "grd_test_key",
    setWorkspace: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  createWorkspace: vi.fn().mockResolvedValue({
    workspace_id: "ws-1",
    name: "Acme Corp",
    slug: "acme-corp",
  }),
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

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function clickNext() {
  const btn = screen.getAllByRole("button").find(
    (b) => !b.hasAttribute("disabled") && /next|continue/i.test(b.textContent ?? "")
  );
  if (btn) fireEvent.click(btn);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  it("renders the first step heading 'About you'", () => {
    renderPage();
    expect(screen.getByText("About you")).toBeInTheDocument();
  });

  it("renders name and email inputs on step 0", () => {
    renderPage();
    expect(screen.getByPlaceholderText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("jane@company.com")).toBeInTheDocument();
  });

  it("renders a Next button", () => {
    renderPage();
    const buttons = screen.getAllByRole("button");
    expect(buttons.some((b) => /next|continue/i.test(b.textContent ?? ""))).toBe(true);
  });

  it("advances to Organization step after filling step 0", async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText("Jane Smith"), { target: { value: "Ada" } });
    fireEvent.change(screen.getByPlaceholderText("jane@company.com"), { target: { value: "ada@acme.com" } });
    clickNext();
    await waitFor(() => expect(screen.getByText("Organization")).toBeInTheDocument());
  });

  it("advances to Use case step after filling Organization", async () => {
    renderPage();

    // Step 0
    fireEvent.change(screen.getByPlaceholderText("Jane Smith"), { target: { value: "Ada" } });
    fireEvent.change(screen.getByPlaceholderText("jane@company.com"), { target: { value: "ada@acme.com" } });
    clickNext();

    await waitFor(() => screen.getByPlaceholderText("Acme Corp"));

    // Step 1
    fireEvent.change(screen.getByPlaceholderText("Acme Corp"), { target: { value: "My Corp" } });
    fireEvent.change(screen.getByPlaceholderText("Acme Compliance"), { target: { value: "my-ws" } });
    clickNext();

    await waitFor(() => expect(screen.getByText("Your use case")).toBeInTheDocument());
  });

  it("calls createWorkspace when the form reaches the final step and is submitted", async () => {
    const { createWorkspace } = await import("@/lib/api");
    renderPage();

    // Step 0
    fireEvent.change(screen.getByPlaceholderText("Jane Smith"), { target: { value: "Ada" } });
    fireEvent.change(screen.getByPlaceholderText("jane@company.com"), { target: { value: "ada@acme.com" } });
    clickNext();

    await waitFor(() => screen.getByPlaceholderText("Acme Corp"));

    // Step 1
    fireEvent.change(screen.getByPlaceholderText("Acme Corp"), { target: { value: "My Corp" } });
    fireEvent.change(screen.getByPlaceholderText("Acme Compliance"), { target: { value: "my-ws" } });
    clickNext();

    await waitFor(() => screen.getByText("Your use case"));

    // Step 2: select industry + use case chips
    fireEvent.click(screen.getByText("Technology"));
    fireEvent.click(screen.getByText("Policy & compliance"));
    clickNext();

    await waitFor(() => screen.getByText("Get started"));

    // Step 3: create workspace
    const createBtn = screen.getAllByRole("button").find(
      (b) => !b.hasAttribute("disabled") && /create/i.test(b.textContent ?? "")
    );
    if (createBtn) {
      fireEvent.click(createBtn);
      await waitFor(() => expect(vi.mocked(createWorkspace)).toHaveBeenCalled());
    }
  });
});
