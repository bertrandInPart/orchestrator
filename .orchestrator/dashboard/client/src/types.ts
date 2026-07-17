export interface Feature {
  slug: string;
  title: string;
  stage: string;
  currentAgent: string | null;
  branch: string | null;
  ticketId: string;
  ticketUrl: string;
  updatedAt: string | null;
}

export interface BoardResponse {
  provider: "github" | "jira";
  features: Feature[];
}

export interface EntryTelemetry {
  durationSeconds: number | null;
  tokensInput: number | null;
  tokensOutput: number | null;
  outcome: string | null;
}

export interface LifecycleEntry {
  agent: string;
  attempt: number;
  timestamp: string;
  check: string | null;
  result: string | null;
  details: string | null;
  actionTaken: string | null;
  telemetry: EntryTelemetry | null;
}

export interface Lifecycle {
  issueId: string | null;
  slug: string | null;
  createdAt: string | null;
  lastUpdated: string | null;
  entries: LifecycleEntry[];
}

export interface TelemetrySummary {
  runCount: number;
  durationSeconds: number;
  tokensInput: number | null;
  tokensOutput: number | null;
}

export interface CommentMeta {
  agent: string;
  stage: string;
  status: string;
  timestamp: string;
}

export interface Comment {
  id: string;
  author: string;
  createdAt: string;
  body: string;
  url: string;
  meta: CommentMeta | null;
}

export interface FeatureDetailResponse {
  slug: string;
  lifecycle: Lifecycle | null;
  telemetrySummary: TelemetrySummary;
  comments: Comment[];
  commentsError: string | null;
}

export interface ApiError {
  error: string;
}
