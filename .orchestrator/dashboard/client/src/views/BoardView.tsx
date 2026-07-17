import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchBoard } from "../api";
import type { Feature } from "../types";
import { RelativeTime } from "../RelativeTime";

const AUTO_REFRESH_MS = 30_000;

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
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [query, setQuery] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBoard();
      setFeatures(data.features);
      setProvider(data.provider);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // Passive auto-refresh on top of the manual Refresh button — this is
    // read-only polling of our own API, not the ticket provider directly,
    // so it stays well within GitHub/Jira rate limits.
    const id = setInterval(load, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  const filtered = useMemo(() => {
    if (!features) return null;
    const q = query.trim().toLowerCase();
    if (!q) return features;
    return features.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.slug.toLowerCase().includes(q) ||
        (f.currentAgent ?? "").toLowerCase().includes(q) ||
        (f.branch ?? "").toLowerCase().includes(q)
    );
  }, [features, query]);

  const columns = filtered ? groupByStage(filtered) : null;

  return (
    <div>
      <div className="toolbar">
        <h1>Feature chain board{provider ? ` (${provider})` : ""}</h1>
        <div className="toolbar-actions">
          {lastUpdated && <RelativeTime date={lastUpdated} />}
          <button type="button" onClick={load} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {features && features.length > 0 && (
        <input
          type="search"
          className="board-search"
          placeholder="Filter by title, slug, agent, or branch…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter features"
        />
      )}

      <div role="status" aria-live="polite" className="visually-hidden">
        {loading ? "Refreshing board…" : lastUpdated ? `Board updated ${lastUpdated.toLocaleTimeString()}` : ""}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!columns && loading && <BoardSkeleton />}

      {columns && (
        <div className="board">
          {columns.map(([stage, items]) => (
            <div className="board-column" key={stage}>
              <h2>
                {stage} <span className="count">{items.length}</span>
              </h2>
              {items.length === 0 && query && <p className="empty">No matches</p>}
              {items.map((feature) => (
                <div className="feature-card" key={feature.slug}>
                  <Link to={`/features/${encodeURIComponent(feature.slug)}`} className="feature-card-link">
                    <div className="feature-title">{feature.title}</div>
                    <div className="feature-slug">{feature.slug}</div>
                    <div className="feature-meta">
                      <span>👤 {feature.currentAgent ?? "none"}</span>
                      {feature.branch && <span>🌿 {feature.branch}</span>}
                    </div>
                  </Link>
                  <a href={feature.ticketUrl} target="_blank" rel="noreferrer" className="ticket-link">
                    #{feature.ticketId}
                  </a>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BoardSkeleton() {
  return (
    <div className="board" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div className="board-column" key={i}>
          <h2 className="skeleton skeleton-text" style={{ width: "60%" }} />
          {Array.from({ length: 2 }).map((_, j) => (
            <div className="feature-card skeleton-card" key={j}>
              <div className="skeleton skeleton-text" style={{ width: "80%" }} />
              <div className="skeleton skeleton-text" style={{ width: "50%" }} />
              <div className="skeleton skeleton-text" style={{ width: "40%" }} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

