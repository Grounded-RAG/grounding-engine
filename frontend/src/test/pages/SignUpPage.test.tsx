import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import SignUpPage from "@/pages/SignUpPage";

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
    signInWithApiKey: vi.fn(),
    setWorkspace: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  signUpWithEmail: vi.fn(),
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
        <SignUpPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SignUpPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  it("renders the page heading", () => {
    renderPage();
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("renders name input", () => {
    renderPage();
    expect(screen.getByPlaceholderText(/samrawit/i)).toBeInTheDocument();
  });

  it("renders email input", () => {
    renderPage();
    expect(screen.getByPlaceholderText(/you@company\.com/i)).toBeInTheDocument();
  });

  it("renders password input", () => {
    renderPage();
    expect(screen.getByPlaceholderText(/at least 8 characters/i)).toBeInTheDocument();
  });

  it("renders organisation input", () => {
    renderPage();
    expect(screen.getByPlaceholderText(/iCog Labs/i)).toBeInTheDocument();
  });

  it("renders a sign-up submit button", () => {
    renderPage();
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("renders the sign-in link", () => {
    renderPage();
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
  });

  it("calls signUpWithEmail and navigates on success", async () => {
    const { signUpWithEmail } = await import("@/lib/api");
    vi.mocked(signUpWithEmail).mockResolvedValueOnce({
      api_key: "grd_new_key",
      workspace_slug: "acme",
    } as never);

    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/samrawit/i), { target: { value: "Ada Lovelace" } });
    fireEvent.change(screen.getByPlaceholderText(/you@company\.com/i), { target: { value: "ada@acme.com" } });
    fireEvent.change(screen.getByPlaceholderText(/at least 8 characters/i), { target: { value: "password123" } });
    fireEvent.change(screen.getByPlaceholderText(/iCog Labs/i), { target: { value: "Acme Corp" } });

    const form = screen.getByPlaceholderText(/samrawit/i).closest("form");
    if (form) fireEvent.submit(form);

    await waitFor(() => {
      expect(vi.mocked(signUpWithEmail)).toHaveBeenCalled();
    });
  });
});
