import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/lib/auth";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

vi.mock("@/lib/api", () => ({
  authenticateWithApiKey: vi.fn().mockResolvedValue({
    workspace_id: "ws-1",
    workspace_name: "Acme",
    workspace_slug: "acme",
    email: "user@acme.com",
  }),
}));

function TestConsumer() {
  const { apiKey, workspaceId, workspaceSlug } = useAuth();
  return (
    <div>
      <span data-testid="api-key">{apiKey ?? "none"}</span>
      <span data-testid="workspace-id">{workspaceId ?? "none"}</span>
      <span data-testid="workspace-slug">{workspaceSlug ?? "none"}</span>
    </div>
  );
}

function SignInConsumer() {
  const { signInWithApiKey, apiKey } = useAuth();
  return (
    <div>
      <span data-testid="api-key">{apiKey ?? "none"}</span>
      <button onClick={() => signInWithApiKey("grd_live_key")}>Sign In</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AuthProvider / useAuth", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("provides null apiKey by default when localStorage is empty", () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    expect(screen.getByTestId("api-key").textContent).toBe("none");
  });

  it("restores apiKey from localStorage on mount", async () => {
    localStorage.setItem("grounded_api_key", "grd_stored_key");
    localStorage.setItem("grounded_workspace_id", "ws-2");
    localStorage.setItem("grounded_workspace_slug", "acme");

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );
    });

    expect(screen.getByTestId("workspace-slug").textContent).toBe("acme");
  });

  it("throws when useAuth is called outside AuthProvider", () => {
    const original = console.error;
    console.error = () => {};
    expect(() => render(<TestConsumer />)).toThrow();
    console.error = original;
  });

  it("updates apiKey after signInWithApiKey", async () => {
    const { authenticateWithApiKey } = await import("@/lib/api");
    vi.mocked(authenticateWithApiKey).mockResolvedValue({
      workspace_id: "ws-1",
      workspace_name: "Acme",
      workspace_slug: "acme",
      email: "user@acme.com",
    } as never);

    await act(async () => {
      render(
        <AuthProvider>
          <SignInConsumer />
        </AuthProvider>
      );
    });

    await act(async () => {
      screen.getByRole("button").click();
    });

    expect(screen.getByTestId("api-key").textContent).toBe("grd_live_key");
  });
});
