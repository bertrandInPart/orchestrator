import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchFeature } from "../api";
import type { FeatureDetailResponse } from "../types";

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "n/a";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remaining}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function formatTokens(count: number | null): string {
  if (count === null) return "n/a";
  return count.toLocaleString();
}

export function FeatureDetailView() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [data, setData] = useState<FeatureDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchFeature(slug));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  return (
    <div>
      <div className="toolbar">
        <div>
          <Link to="/">← Back to board</Link>
          <h1>{slug}</h1>
        </div>
        <button type="button" onClick={load} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {data && (
        <div className="detail-columns">
          <section>
            <h2>Lifecycle history</h2>
            {data.telemetrySummary.runCount > 0 && (
              <div className="telemetry-summary">
                <span>⏱ {formatDuration(data.telemetrySummary.durationSeconds)} total</span>
                <span>
                  🔤 {formatTokens(data.telemetrySummary.tokensInput)} in /{" "}
                  {formatTokens(data.telemetrySummary.tokensOutput)} out
                </span>
                <span>
                  {data.telemetrySummary.runCount} logged run
                  {data.telemetrySummary.runCount === 1 ? "" : "s"}
                </span>
              </div>
            )}
            {!data.lifecycle && <p className="empty">No lifecycle file found for this feature yet.</p>}
            {data.lifecycle && data.lifecycle.entries.length === 0 && (
              <p className="empty">Lifecycle file exists but has no execution history entries yet.</p>
            )}
            {data.lifecycle && data.lifecycle.entries.length > 0 && (
              <ol className="timeline">
                {data.lifecycle.entries.map((entry, i) => (
                  <li key={i} className={`result-${(entry.result ?? "unknown").toLowerCase()}`}>
                    <div className="timeline-header">
                      <strong>{entry.agent}</strong> — attempt {entry.attempt}
                      <span className="timestamp">{entry.timestamp}</span>
                    </div>
                    <div className="timeline-body">
                      <div>
                        <strong>{entry.check}</strong> check: <strong>{entry.result}</strong>
                      </div>
                      {entry.details && <div>{entry.details}</div>}
                      {entry.actionTaken && <div className="action-taken">{entry.actionTaken}</div>}
                      {entry.telemetry && (
                        <div className="entry-telemetry">
                          <span>⏱ {formatDuration(entry.telemetry.durationSeconds)}</span>
                          <span>
                            🔤 {formatTokens(entry.telemetry.tokensInput)} in /{" "}
                            {formatTokens(entry.telemetry.tokensOutput)} out
                          </span>
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section>
            <h2>Ticket activity</h2>
            {data.commentsError && <p className="empty">{data.commentsError}</p>}
            {!data.commentsError && data.comments.length === 0 && (
              <p className="empty">No comments yet.</p>
            )}
            <ol className="timeline">
              {data.comments.map((comment) => (
                <li key={comment.id}>
                  <div className="timeline-header">
                    <strong>{comment.meta?.agent ?? comment.author}</strong>
                    <span className="timestamp">{comment.createdAt}</span>
                  </div>
                  <div className="timeline-body">
                    {comment.meta && (
                      <div>
                        {comment.meta.stage} — <strong>{comment.meta.status}</strong>
                      </div>
                    )}
                    <a href={comment.url} target="_blank" rel="noreferrer">
                      view on ticket
                    </a>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </div>
  );
}
