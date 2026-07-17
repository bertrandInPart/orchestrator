import { useEffect, useState } from "react";

/** "3s ago" / "5m ago" / "2h ago", ticking every second so it stays live. */
function formatRelative(date: Date, now: Date): string {
  const seconds = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

/** Live-updating "refreshed Xs ago" label, used next to the manual Refresh button. */
export function RelativeTime({ date }: { date: Date }) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="last-updated" title={date.toLocaleString()}>
      Updated {formatRelative(date, now)}
    </span>
  );
}
