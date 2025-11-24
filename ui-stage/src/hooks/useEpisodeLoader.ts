import { useEffect, useRef, useState } from "react";
import { getLatestEpisode } from "../api/episodes";
import { buildEpisodeView } from "../vm/episodeVm";
import type { EpisodeViewModel } from "../vm/episodeVm";

export interface UseEpisodeLoaderResult {
  episode: EpisodeViewModel | null;
  error: string | null;
  isLoading: boolean;
}

export function useEpisodeLoader(): UseEpisodeLoaderResult {
  const [episode, setEpisode] = useState<EpisodeViewModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return; // ensure single fetch per mount
    startedRef.current = true;

    let isActive = true;
    (async () => {
      try {
        const raw = await getLatestEpisode();
        const vm = buildEpisodeView(raw as any);
        if (!isActive) return;
        setEpisode(vm);
        setError(null);
      } catch (err: unknown) {
        if (!isActive) return;
        const msg = err instanceof Error ? err.message : "Unknown error";
        setEpisode(null);
        setError(msg);
      } finally {
        if (isActive) setIsLoading(false);
      }
    })();

    return () => {
      isActive = false;
    };
  }, []);

  return { episode, error, isLoading };
}
