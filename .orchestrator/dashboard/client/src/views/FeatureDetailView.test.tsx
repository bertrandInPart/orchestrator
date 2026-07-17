import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { FeatureDetailView } from "./FeatureDetailView";
import * as api from "../api";
import type { FeatureDetailResponse } from "../types";

function renderForSlug(slug: string) {
  return render(
    <MemoryRouter initialEntries={[`/features/${slug}`]}>
      <Routes>
        <Route path="/features/:slug" element={<FeatureDetailView />} />
      </Routes>
    </MemoryRouter>
  );
}

function response(overrides: Partial<FeatureDetailResponse>): FeatureDetailResponse {
  return {
    slug: "feat-a",
    lifecycle: null,
    telemetrySummary: { runCount: 0, durationSeconds: 0, tokensInput: null, tokensOutput: null },
    comments: [],
    commentsError: null,
    ...overrides,
  };
}

describe("FeatureDetailView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an empty-state message when the feature has no lifecycle file yet", async () => {
    vi.spyOn(api, "fetchFeature").mockResolvedValue(response({}));

    renderForSlug("feat-a");

    await waitFor(() =>
      expect(screen.getByText("No lifecycle file found for this feature yet.")).toBeTruthy()
    );
  });

  it("renders each lifecycle entry with its check/result and enriched telemetry", async () => {
    vi.spyOn(api, "fetchFeature").mockResolvedValue(
      response({
        lifecycle: {
          issueId: "42",
          slug: "feat-a",
          createdAt: "2026-01-01T00:00:00Z",
          lastUpdated: "2026-01-02T00:00:00Z",
          entries: [
            {
              agent: "Backend Builder",
              attempt: 1,
              timestamp: "2026-01-01T01:00:00Z",
              check: "DoD",
              result: "Pass",
              details: "All acceptance criteria met.",
              actionTaken: null,
              telemetry: { durationSeconds: 125, tokensInput: 1000, tokensOutput: 250, outcome: "success" },
            },
          ],
        },
        telemetrySummary: { runCount: 1, durationSeconds: 125, tokensInput: 1000, tokensOutput: 250 },
      })
    );

    renderForSlug("feat-a");

    await waitFor(() => expect(screen.getByText("Backend Builder")).toBeTruthy());
    expect(screen.getByText(/attempt 1/)).toBeTruthy();
    expect(screen.getByText("All acceptance criteria met.")).toBeTruthy();
    expect(screen.getAllByText("2m 5s", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getByText("1 logged run")).toBeTruthy();
  });

  it("shows the ticket comments error message without hiding the rest of the page", async () => {
    vi.spyOn(api, "fetchFeature").mockResolvedValue(
      response({ commentsError: "GITHUB_TOKEN environment variable is not set." })
    );

    renderForSlug("feat-a");

    await waitFor(() =>
      expect(screen.getByText("GITHUB_TOKEN environment variable is not set.")).toBeTruthy()
    );
    expect(screen.getByText("No lifecycle file found for this feature yet.")).toBeTruthy();
  });

  it("re-fetches for the current slug when navigating between features", async () => {
    const fetchFeature = vi.spyOn(api, "fetchFeature").mockResolvedValue(response({ slug: "feat-a" }));

    renderForSlug("feat-a");

    await waitFor(() => expect(fetchFeature).toHaveBeenCalledWith("feat-a"));
  });
});
