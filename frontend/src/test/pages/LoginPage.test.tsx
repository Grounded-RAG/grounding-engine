import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";

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
    signInWithApiKey: vi.fn().mockResolvedValue(undefined),
    setWorkspace: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  listWorkspaces: vi.fn().mockResolvedValue([
    { slug: "acme", workspace_id: "ws-1", name: "Acme" },
  ]),
  signInWithEmail: vi.fn(),
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
    form: ({ children, ...props }: React.FormHTMLAttributes<HTMLFormElement>) => (
      <form {...props}>{children}</form>
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
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function openDeveloperAccess() {
  const toggle = screen.getByText(/developer access/i);
  fireEvent.click(toggle.closest("button") ?? toggle);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  it("renders the Developer access toggle", () => {
    renderPage();
    expect(screen.getByText(/developer access/i)).toBeInTheDocument();
  });

  it("reveals the API key input after clicking Developer access", () => {
    renderPage();
    openDeveloperAccess();
    expect(screen.getByPlaceholderText("grd_...")).toBeInTheDocument();
  });

  it("renders a sign-in button", () => {
    renderPage();
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("renders the email input when email sign-in tab is active", async () => {
    renderPage();
    const emailTabBtn = screen.getByRole("button", { name: /sign in with email/i });
    fireEvent.click(emailTabBtn);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/you@company\.com/i)).toBeInTheDocument();
    });
  });

  it("renders the sign-up link", () => {
    renderPage();
    const matches = screen.getAllByText(/sign up/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("navigates after successful API key sign-in", async () => {
    renderPage();
    openDeveloperAccess();

    const input = screen.getByPlaceholderText("grd_...");
    fireEvent.change(input, { target: { value: "grd_test_key" } });

    const form = input.closest("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalled();
    });
  });
});
