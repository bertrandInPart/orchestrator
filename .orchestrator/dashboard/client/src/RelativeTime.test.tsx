import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { RelativeTime } from "./RelativeTime";

describe("RelativeTime", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows 'just now' immediately after the given date", () => {
    render(<RelativeTime date={new Date()} />);
    expect(screen.getByText(/just now/i)).toBeTruthy();
  });

  it("ticks forward to show elapsed seconds without needing a re-render from the parent", () => {
    vi.useFakeTimers();
    const date = new Date();
    render(<RelativeTime date={date} />);

    act(() => {
      vi.advanceTimersByTime(90_000);
    });

    expect(screen.getByText(/1m ago/i)).toBeTruthy();
  });
});
