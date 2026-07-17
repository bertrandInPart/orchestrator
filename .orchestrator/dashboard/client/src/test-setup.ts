import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// @testing-library/react does not auto-unmount between tests under Vitest
// (unlike Jest, where it's wired in automatically) — without this, each
// test's rendered DOM piles up on top of the previous test's, and queries
// like getByRole start matching multiple leftover copies.
afterEach(() => {
  cleanup();
});
