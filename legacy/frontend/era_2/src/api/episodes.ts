// Typed API client for Stage Episodes
// Single source of truth for network calls from the Stage Viewer.

import type { StageEpisode } from "../types/stage";

export interface ApiError {
  message: string;
  status?: number;
}

function getBaseUrl(): string {
  // Vite exposes env via import.meta.env
  const env = (import.meta as any).env;
  const base: unknown = env?.VITE_API_BASE_URL;
  return (typeof base === "string" && base.length > 0) ? base : "http://127.0.0.1:8000";
}

async function getJson<T>(path: string): Promise<T> {
  const base = getBaseUrl();
  const url = `${base}${path}`;
  let res: Response;
  try {
    res = await fetch(url, { method: "GET" });
  } catch (err: any) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Network error: ${message}`);
  }

  if (!res.ok) {
    // Try to surface a meaningful error body if provided
    let detail = "";
    try {
      const data = await res.json();
      if (data && typeof data === "object") {
        const msg = (data as any).detail ?? (data as any).message;
        if (typeof msg === "string") detail = ` - ${msg}`;
      }
    } catch {
      // ignore body parse errors
    }
    throw new Error(`HTTP ${res.status}${detail}`);
  }

  return (await res.json()) as T;
}

export async function getLatestEpisode(): Promise<StageEpisode> {
  const json = await getJson<StageEpisode>("/episodes/latest");
  return json as StageEpisode;
}

export async function getEpisodeById(episodeId: string): Promise<StageEpisode> {
  const json = await getJson<StageEpisode>(`/episodes/${encodeURIComponent(episodeId)}`);
  return json as StageEpisode;
}
