import { test } from "node:test";
import assert from "node:assert/strict";
import { agentKey, summarizeTelemetry } from "../telemetry.js";

test("agentKey normalizes a display name to the same key as a chatmode name", () => {
  assert.equal(agentKey("Backend Builder"), "backend-builder");
  assert.equal(agentKey("backend-builder"), "backend-builder");
  assert.equal(agentKey("  Spec   Writer  "), "spec-writer");
});

test("summarizeTelemetry totals duration across every run", () => {
  const runs = [{ duration_seconds: 10 }, { duration_seconds: 20 }, { duration_seconds: 5 }];
  const summary = summarizeTelemetry(runs);
  assert.equal(summary.runCount, 3);
  assert.equal(summary.durationSeconds, 35);
});

test("summarizeTelemetry treats a missing duration as zero, not skipped", () => {
  const runs = [{ duration_seconds: 10 }, {}];
  const summary = summarizeTelemetry(runs);
  assert.equal(summary.durationSeconds, 10);
});

test("summarizeTelemetry sums tokens only across runs that reported them", () => {
  const runs = [
    { duration_seconds: 1, tokens_input: 100, tokens_output: 50 },
    { duration_seconds: 1 }, // no token fields reported
    { duration_seconds: 1, tokens_input: 25, tokens_output: 10 },
  ];
  const summary = summarizeTelemetry(runs);
  assert.equal(summary.tokensInput, 125);
  assert.equal(summary.tokensOutput, 60);
});

test("summarizeTelemetry returns null tokens (not zero) when no run reported any", () => {
  const runs = [{ duration_seconds: 1 }, { duration_seconds: 2 }];
  const summary = summarizeTelemetry(runs);
  assert.equal(summary.tokensInput, null);
  assert.equal(summary.tokensOutput, null);
});

test("summarizeTelemetry handles an empty run list", () => {
  const summary = summarizeTelemetry([]);
  assert.deepEqual(summary, {
    runCount: 0,
    durationSeconds: 0,
    tokensInput: null,
    tokensOutput: null,
  });
});
