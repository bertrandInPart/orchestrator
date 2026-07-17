import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BoardView } from "./BoardView";
import * as api from "../api";
import type { Feature } from "../types";

function feature(overrides: Partial<Feature>): Feature {
  return {
    slug: "feat-a",
    title: "Feature A",
    stage: "Implementation",
    currentAgent: "Backend Builder",
    branch: "feature/feat-a",
    ticketId: "42",
    ticketUrl: "https://github.com/acme/widgets/issues/42",
    updatedAt: null,
    ...overrides,
  };
}

describe("BoardView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("groups fetched features into their stage columns", async () => {
    vi.spyOn(api, "fetchBoard").mockResolvedValue({
      provider: "github",
      features: [
        feature({ slug: "feat-a", stage: "Implementation" }),
        feature({ slug: "feat-b", title: "Feature B", stage: "Done" }),
      ],
    });

    render(
      <MemoryRouter>
        <BoardView />
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Feature A")).toBeTruthy());
    expect(screen.getByText("Feature B")).toBeTruthy();

    const implementationColumn = screen.getByText("Implementation").closest(".board-column")!;
    expect(implementationColumn.textContent).toContain("Feature A");
    expect(implementationColumn.textContent).not.toContain("Feature B");
  });

  it("puts a stage not in the known board order into an 'Other' column instead of dropping it", async () => {
    vi.spyOn(api, "fetchBoard").mockResolvedValue({
      provider: "jira",
      features: [feature({ slug: "feat-c", title: "Feature C", stage: "In Review (Jira custom)" })],
    });

    render(
      <MemoryRouter>
        <BoardView />
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Feature C")).toBeTruthy());
    expect(screen.getByText("Other")).toBeTruthy();
  });

  it("renders the ticket link and the card link as separate, non-nested anchors", async () => {
    vi.spyOn(api, "fetchBoard").mockResolvedValue({
      provider: "github",
      features: [feature({})],
    });

    render(
      <MemoryRouter>
        <BoardView />
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Feature A")).toBeTruthy());

    const ticketLink = screen.getByRole("link", { name: "#42" });
    const cardLink = screen.getByRole("link", { name: /Feature A/ });

    // Regression test: the ticket link must not be nested inside the card's
    // Link (invalid HTML — a nested <a> — that used to make its click
    // behavior unreliable across browsers).
    expect(cardLink.contains(ticketLink)).toBe(false);
    expect(ticketLink.getAttribute("href")).toBe("https://github.com/acme/widgets/issues/42");
    expect(cardLink.getAttribute("href")).toBe("/features/feat-a");
  });

  it("filters visible features by the search box across title, slug, agent, and branch", async () => {
    vi.spyOn(api, "fetchBoard").mockResolvedValue({
      provider: "github",
      features: [
        feature({ slug: "feat-a", title: "Alpha", currentAgent: "Architect", branch: "feature/alpha" }),
        feature({ slug: "feat-b", title: "Beta", currentAgent: "Reviewer", branch: "feature/beta" }),
      ],
    });

    render(
      <MemoryRouter>
        <BoardView />
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText("Alpha")).toBeTruthy());
    expect(screen.getByText("Beta")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Filter features"), { target: { value: "architect" } });

    expect(screen.getByText("Alpha")).toBeTruthy();
    expect(screen.queryByText("Beta")).toBeNull();
  });

  it("shows the error banner returned by the API instead of the board on failure", async () => {
    vi.spyOn(api, "fetchBoard").mockRejectedValue(new Error("GITHUB_TOKEN environment variable is not set."));

    render(
      <MemoryRouter>
        <BoardView />
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByText("GITHUB_TOKEN environment variable is not set.")).toBeTruthy()
    );
  });
});
