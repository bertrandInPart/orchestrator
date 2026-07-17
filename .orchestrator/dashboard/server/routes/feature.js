import { Router } from "express";
import { loadConfig } from "../config.js";
import { getLifecycleHistory } from "../lifecycle.js";
import { getFeatureTelemetry, summarizeTelemetry, agentKey } from "../telemetry.js";
import * as githubAdapter from "../adapters/github.js";
import * as jiraAdapter from "../adapters/jira.js";

function adapterFor(config) {
  return config.provider === "github" ? githubAdapter : jiraAdapter;
}

export const featureRouter = Router();

// Attaches the matching telemetry run's duration/token usage to a lifecycle
// entry (matched by agent name + attempt number — lifecycle files record the
// agent's display name, telemetry records its kebab-case chatmode name, see
// telemetry.js's agentKey()). Entries with no matching run (e.g. logged
// before telemetry was wired up, or not yet run) are left un-enriched rather
// than guessing.
function enrichEntryWithTelemetry(entry, runs) {
  const run = runs.find(
    (r) => agentKey(r.agent) === agentKey(entry.agent) && r.attempt_number === entry.attempt
  );
  if (!run) return { ...entry, telemetry: null };
  return {
    ...entry,
    telemetry: {
      durationSeconds: run.duration_seconds ?? null,
      tokensInput: run.tokens_input ?? null,
      tokensOutput: run.tokens_output ?? null,
      outcome: run.outcome ?? null,
    },
  };
}

// GET /api/features/:slug -> lifecycle history (DoR/DoD/callback/retry/
// escalation entries, parsed from the local lifecycle file, each enriched
// with matching duration/token telemetry where available) plus the ticket's
// comment activity feed (parsed meta lines), for one feature's drill-down
// view.
featureRouter.get("/features/:slug", async (req, res) => {
  const { slug } = req.params;
  try {
    const config = loadConfig();
    const adapter = adapterFor(config);

    const [lifecycle, comments] = await Promise.all([
      Promise.resolve(getLifecycleHistory(slug)),
      adapter.getFeatureComments(config, slug).catch((err) => {
        // A feature can have a lifecycle file before its ticket has any
        // comments yet (or vice versa) — don't fail the whole response for
        // either half being unavailable.
        return { error: err.message };
      }),
    ]);

    const runs = getFeatureTelemetry(slug);
    const enrichedLifecycle = lifecycle && {
      ...lifecycle,
      entries: lifecycle.entries.map((entry) => enrichEntryWithTelemetry(entry, runs)),
    };

    res.json({
      slug,
      lifecycle: enrichedLifecycle,
      telemetrySummary: summarizeTelemetry(runs),
      comments: Array.isArray(comments) ? comments : [],
      commentsError: Array.isArray(comments) ? null : comments.error,
    });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});
