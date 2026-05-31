import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiError } from "@/lib/api";

// ---------------------------------------------------------------------------
// ApiError class
// ---------------------------------------------------------------------------

describe("ApiError", () => {
  it("extends Error", () => {
    const err = new ApiError(404, "Not found");
    expect(err).toBeInstanceOf(Error);
  });

  it("stores status code", () => {
    const err = new ApiError(422, "Validation failed");
    expect(err.status).toBe(422);
  });

  it("stores detail message", () => {
    const err = new ApiError(500, "Internal error");
    expect(err.detail).toBe("Internal error");
  });

  it("uses detail as error message", () => {
    const err = new ApiError(403, "Forbidden");
    expect(err.message).toBe("Forbidden");
  });
});

// ---------------------------------------------------------------------------
// API function integration tests (fetch mocked)
// ---------------------------------------------------------------------------

const MOCK_API_KEY = "grd_test_key";

function mockFetch(body: unknown, status = 200) {
  const response = new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(response);
}

describe("listDatasets", () => {
  afterEach(() => vi.restoreAllMocks());

  it("sends X-API-Key header", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    const { listDatasets } = await import("@/lib/api");
    await listDatasets(MOCK_API_KEY, "ws-1");
    const [, init] = spy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe(MOCK_API_KEY);
  });

  it("returns parsed dataset array", async () => {
    const dataset = {
      dataset_id: "ds-1",
      workspace_id: "ws-1",
      name: "Compliance Docs",
    };
    mockFetch([dataset]);
    const { listDatasets } = await import("@/lib/api");
    const result = await listDatasets(MOCK_API_KEY, "ws-1");
    expect(result).toEqual([dataset]);
  });

  it("throws ApiError on 401 response", async () => {
    mockFetch({ detail: "Unauthorized" }, 401);
    const { listDatasets } = await import("@/lib/api");
    await expect(listDatasets(MOCK_API_KEY, "ws-1")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("listAgents", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns parsed agents array", async () => {
    const agent = { agent_id: "a-1", name: "Policy Bot" };
    mockFetch([agent]);
    const { listAgents } = await import("@/lib/api");
    const result = await listAgents(MOCK_API_KEY, "ws-1");
    expect(result).toEqual([agent]);
  });

  it("throws ApiError on non-ok response", async () => {
    mockFetch({ detail: "Not found" }, 404);
    const { listAgents } = await import("@/lib/api");
    await expect(listAgents(MOCK_API_KEY, "ws-1")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("listRuns", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns run array on success", async () => {
    const run = { trace_id: "tr-1", query: "test?" };
    mockFetch([run]);
    const { listRuns } = await import("@/lib/api");
    const result = await listRuns(MOCK_API_KEY);
    expect(result).toEqual([run]);
  });
});
