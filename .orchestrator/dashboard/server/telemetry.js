import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { REPO_ROOT } from "./config.js";

// Overridable via DASHBOARD_TELEMETRY_PATH (e.g. for local testing against a
// fixture file) — defaults to the real telemetry log agents write to.
const TELEMETRY_PATH =
  process.env.DASHBOARD_TELEMETRY_PATH ??
  path.join(REPO_ROOT, ".orchestrator", "docs", "ops", "agent-telemetry.jsonl");

/**
 * Reads every logged agent run from agent-telemetry.jsonl (one JSON object
 * per line, written by .orchestrator/scripts/log-agent-run.sh). Each entry
 * has: feature_slug, issue_number, agent, stage, started_at, finished_at,
 * duration_seconds, outcome, attempt_number, and optional tokens_input /
 * tokens_output (omitted, not zeroed, when not reported).
 */
export function readTelemetry() {
  if (!existsSync(TELEMETRY_PATH)) return [];
  const text = readFileSync(TELEMETRY_PATH, "utf8");
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line));
}

/** All logged runs for one feature slug, in file order (oldest first). */
export function getFeatureTelemetry(slug) {
  return readTelemetry().filter((entry) => entry.feature_slug === slug);
}

// Lifecycle entries record the agent's display name ("Backend Builder"),
// telemetry records its chatmode/CLI name ("backend-builder") — normalize
// both to the same key before matching.
export function agentKey(name) {
  return name.trim().toLowerCase().replace(/\s+/g, "-");
}

/**
 * Totals across every logged run for a feature: summed duration and token
 * usage (tokens omitted from the sum, not counted as zero, for any run that
 * didn't report them).
 */
export function summarizeTelemetry(runs) {
  let durationSeconds = 0;
  let tokensInput = 0;
  let tokensOutput = 0;
  let hasTokens = false;
  for (const run of runs) {
    durationSeconds += run.duration_seconds ?? 0;
    if (typeof run.tokens_input === "number") {
      tokensInput += run.tokens_input;
      hasTokens = true;
    }
    if (typeof run.tokens_output === "number") {
      tokensOutput += run.tokens_output;
      hasTokens = true;
    }
  }
  return {
    runCount: runs.length,
    durationSeconds,
    tokensInput: hasTokens ? tokensInput : null,
    tokensOutput: hasTokens ? tokensOutput : null,
  };
}
