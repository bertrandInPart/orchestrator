import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchBoard, fetchFeature } from "./api";

function jsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

describe("api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchBoard returns the parsed body on success", async () => {
    const body = { provider: "github", features: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));

    await expect(fetchBoard()).resolves.toEqual(body);
    expect(fetch).toHaveBeenCalledWith("/api/board");
  });

  it("fetchBoard throws the server-provided error message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ error: "config missing" }, false, 502))
    );

    await expect(fetchBoard()).rejects.toThrow("config missing");
  });

  it("fetchBoard falls back to a generic message when the body has no error field", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, false, 500)));

    await expect(fetchBoard()).rejects.toThrow("Request to /api/board failed with 500");
  });

  it("fetchFeature URL-encodes the slug and returns the parsed body", async () => {
    const body = { slug: "a/b", lifecycle: null, telemetrySummary: {}, comments: [], commentsError: null };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchFeature("a/b")).resolves.toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith("/api/features/a%2Fb");
  });
});
