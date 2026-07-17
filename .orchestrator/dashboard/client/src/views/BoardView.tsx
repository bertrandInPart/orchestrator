import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchBoard } from "../api";
import type { Feature } from "../types";

// Fixed order for the GitHub Projects v2 board Stage column (see
// .github/instructions/github-workflow.instructions.md section 2). Any
// stage/status that doesn't match one of these (e.g. a Jira status with a
// different name) falls into a trailing "Other" column instead of being
// dropped.
const STAGE_ORDER = [
  "Backlog",
  "Spec Drafting",
  "Spec Review",
  "Architecture Drafting",
  "Architecture Review",
  "Implementation",
  "Testing",
  "Governance Review",
  "Release Prep",
  "PR Open",
  "Done",
];

function groupByStage(features: Feature[]): [string, Feature[]][] {
  const groups = new Map<string, Feature[]>();
  for (const stage of STAGE_ORDER) groups.set(stage, []);
  for (const feature of features) {
    const key = STAGE_ORDER.includes(feature.stage) ? feature.stage : "Other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(feature);
  }
  return Array.from(groups.entries());
}

export function BoardView() {
  const [features, setFeatures] = useState<Feature[] | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBoard();
      setFeatures(data.features);
      setProvider(data.provider);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const columns = features ? groupByStage(features) : null;

  return (
    <div>
      <div className="toolbar">
        <h1>Feature chain board{provider ? ` (${provider})` : ""}</h1>
        <button type="button" onClick={load} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {columns && (
        <div className="board">
          {columns.map(([stage, items]) => (
            <div className="board-column" key={stage}>
              <h2>
                {stage} <span className="count">{items.length}</span>
              </h2>
              {items.map((feature) => (
                <Link
                  to={`/features/${encodeURIComponent(feature.slug)}`}
                  className="feature-card"
                  key={feature.slug}
                >
                  <div className="feature-title">{feature.title}</div>
                  <div className="feature-slug">{feature.slug}</div>
                  <div className="feature-meta">
                    <span>👤 {feature.currentAgent ?? "none"}</span>
                    {feature.branch && <span>🌿 {feature.branch}</span>}
                  </div>
                  <a
                    href={feature.ticketUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="ticket-link"
                    onClick={(e) => e.stopPropagation()}
                  >
                    #{feature.ticketId}
                  </a>
                </Link>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
