import type { BoardResponse, FeatureDetailResponse } from "./types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  const body = await res.json();
  if (!res.ok) {
    throw new Error(body?.error ?? `Request to ${path} failed with ${res.status}`);
  }
  return body as T;
}

export function fetchBoard(): Promise<BoardResponse> {
  return get<BoardResponse>("/api/board");
}

export function fetchFeature(slug: string): Promise<FeatureDetailResponse> {
  return get<FeatureDetailResponse>(`/api/features/${encodeURIComponent(slug)}`);
}
