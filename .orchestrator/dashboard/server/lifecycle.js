import { readdirSync, readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { REPO_ROOT } from "./config.js";

const FEATURES_DIR = path.join(REPO_ROOT, ".orchestrator", "docs", "features");

// Matches "### <Agent name> — Attempt <n> — <ISO timestamp>" per
// .orchestrator/skills/lifecycle-file.skill.md. Dash character between
// segments may be an em dash, en dash, or hyphen depending on how it was
// typed/rendered.
const ENTRY_HEADER_RE = /^([^\n]+?)\s+[—–-]\s+Attempt\s+(\d+)\s+[—–-]\s+(\S+)\s*$/;

// "- **Field:** value" bullet lines within an entry body.
const FIELD_RE = /^-\s*\*\*([^*]+):\*\*\s*(.*)$/;

/**
 * Locates the single lifecycle file for a feature slug:
 * .orchestrator/docs/features/<slug>/<issue_id>_<slug>_lifecycle.md
 */
export function findLifecycleFile(slug) {
  const dir = path.join(FEATURES_DIR, slug);
  if (!existsSync(dir)) return null;
  const match = readdirSync(dir).find((f) => f.endsWith("_lifecycle.md"));
  return match ? path.join(dir, match) : null;
}

/**
 * Parses a feature's lifecycle file into its header metadata and the
 * append-only Execution History entries (DoR/DoD checks, callbacks, retries,
 * escalations), oldest first.
 */
export function parseLifecycleFile(filePath) {
  const text = readFileSync(filePath, "utf8");

  const titleMatch = text.match(/^#\s*Lifecycle:\s*Issue\s*#(\S+)\s*[—–-]\s*(.+)$/m);
  const createdMatch = text.match(/\*\*Created:\*\*\s*(.+)$/m);
  const lastUpdatedMatch = text.match(/\*\*Last Updated:\*\*\s*(.+)$/m);

  const entries = [];
  // Split on "### " headings — each one is either an Execution History entry
  // or (rarely) another section heading we don't recognize, which we skip.
  const blocks = text.split(/^###\s+/m).slice(1);
  for (const block of blocks) {
    const lines = block.split(/\r?\n/);
    const headerLine = lines[0].trim();
    const headerMatch = headerLine.match(ENTRY_HEADER_RE);
    if (!headerMatch) continue; // not an Execution History entry block

    const [, agent, attempt, timestamp] = headerMatch;
    const fields = {};
    let currentField = null;
    for (const line of lines.slice(1)) {
      const fieldMatch = line.match(FIELD_RE);
      if (fieldMatch) {
        currentField = fieldMatch[1].trim().toLowerCase();
        fields[currentField] = fieldMatch[2].trim();
      } else if (currentField && line.trim()) {
        // Continuation of a multi-line field value.
        fields[currentField] += ` ${line.trim()}`;
      }
    }

    entries.push({
      agent: agent.trim(),
      attempt: Number(attempt),
      timestamp,
      check: fields.check ?? null,
      result: fields.result ?? null,
      details: fields.details ?? null,
      actionTaken: fields["action taken"] ?? null,
    });
  }

  return {
    issueId: titleMatch?.[1] ?? null,
    slug: titleMatch?.[2]?.trim() ?? null,
    createdAt: createdMatch?.[1]?.trim() ?? null,
    lastUpdated: lastUpdatedMatch?.[1]?.trim() ?? null,
    entries,
  };
}

/**
 * Convenience: find + parse a feature's lifecycle file by slug in one call.
 * Returns null if no lifecycle file exists for that slug yet.
 */
export function getLifecycleHistory(slug) {
  const file = findLifecycleFile(slug);
  if (!file) return null;
  return parseLifecycleFile(file);
}
