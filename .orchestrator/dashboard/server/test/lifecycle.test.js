import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { parseLifecycleFile, findLifecycleFile, getLifecycleHistory } from "../lifecycle.js";
import { REPO_ROOT } from "../config.js";

const SAMPLE = `# Lifecycle: Issue #123 — some-feature-slug

**Created:** 2026-01-01T00:00:00Z
**Last Updated:** 2026-01-02T00:00:00Z

## Execution History

### Spec Writer — Attempt 1 — 2026-01-01T00:05:00Z
- **Check:** DoR
- **Result:** Pass
- **Details:** Spec is ready for review.

### Architect — Attempt 1 — 2026-01-01T01:00:00Z
- **Check:** DoD
- **Result:** Fail
- **Details:** Missing data model section.
- **Action Taken:** Sent back to spec-writer for revision.
`;

test("parseLifecycleFile extracts header metadata", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "lifecycle-"));
  const file = path.join(dir, "123_some-feature-slug_lifecycle.md");
  writeFileSync(file, SAMPLE);

  const parsed = parseLifecycleFile(file);
  assert.equal(parsed.issueId, "123");
  assert.equal(parsed.slug, "some-feature-slug");
  assert.equal(parsed.createdAt, "2026-01-01T00:00:00Z");
  assert.equal(parsed.lastUpdated, "2026-01-02T00:00:00Z");

  rmSync(dir, { recursive: true, force: true });
});

test("parseLifecycleFile extracts every Execution History entry in order", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "lifecycle-"));
  const file = path.join(dir, "123_some-feature-slug_lifecycle.md");
  writeFileSync(file, SAMPLE);

  const parsed = parseLifecycleFile(file);
  assert.equal(parsed.entries.length, 2);

  const [first, second] = parsed.entries;
  assert.equal(first.agent, "Spec Writer");
  assert.equal(first.attempt, 1);
  assert.equal(first.check, "DoR");
  assert.equal(first.result, "Pass");
  assert.equal(first.actionTaken, null);

  assert.equal(second.agent, "Architect");
  assert.equal(second.result, "Fail");
  assert.equal(second.actionTaken, "Sent back to spec-writer for revision.");

  rmSync(dir, { recursive: true, force: true });
});

// findLifecycleFile/getLifecycleHistory resolve against the real
// .orchestrator/docs/features/<slug> directory (via REPO_ROOT), so these
// tests create/remove a throwaway slug directory there rather than in a
// generic temp dir.
const FEATURES_DIR = path.join(REPO_ROOT, ".orchestrator", "docs", "features");

test("findLifecycleFile returns null when the feature has no lifecycle file yet", () => {
  const slug = `__test-no-lifecycle-${process.pid}__`;
  const featureDir = path.join(FEATURES_DIR, slug);
  mkdirSync(featureDir, { recursive: true });

  try {
    assert.equal(findLifecycleFile(slug), null);
  } finally {
    rmSync(featureDir, { recursive: true, force: true });
  }
});

test("findLifecycleFile locates the *_lifecycle.md file for a slug", () => {
  const slug = `__test-with-lifecycle-${process.pid}__`;
  const featureDir = path.join(FEATURES_DIR, slug);
  mkdirSync(featureDir, { recursive: true });
  const file = path.join(featureDir, "999_lifecycle.md");
  writeFileSync(file, SAMPLE);

  try {
    assert.equal(findLifecycleFile(slug), file);
  } finally {
    rmSync(featureDir, { recursive: true, force: true });
  }
});

test("getLifecycleHistory returns null for a slug with no lifecycle directory", () => {
  const slug = "__slug-that-does-not-exist__";
  assert.equal(existsSync(path.join(FEATURES_DIR, slug)), false);
  assert.equal(getLifecycleHistory(slug), null);
});
