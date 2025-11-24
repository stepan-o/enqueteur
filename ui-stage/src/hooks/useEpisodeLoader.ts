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
  // const startedRef = useRef(false);

  // This ref will be set to true in the cleanup of *this* effect run
  const ignoreRef = useRef(false);

  // logging the initial state
  console.log("loader start", { episode, error, isLoading });

  useEffect(() => {
    //if (startedRef.current) return; // ensure single fetch per mount
    //startedRef.current = true;

    ignoreRef.current = false; // this run is "active"
    setIsLoading(true);

    //let isActive = true;

    (async () => {

      // logging before the fetch begins
      console.log("fetching…");

      try {
        const raw = await getLatestEpisode();
        const vm = buildEpisodeView(raw as any);

        if (ignoreRef.current) return;

        // if (!isActive) return;

        console.log("setting episode", vm);

        setEpisode(vm);
        setError(null);
      } catch (err: unknown) {
        if (ignoreRef.current) return;

        const msg = err instanceof Error ? err.message : "Unknown error";

        console.log("error caught", err);

        setEpisode(null);
        setError(msg);
      } finally {
        if (!ignoreRef.current) {
          setIsLoading(false);
          console.log("finally: setting isLoading=false");
        }
      }
    })();

    return () => {
      // If this effect run gets cleaned up (unmounted / StrictMode double run),
      // mark it as ignored so its async work won't touch state.
      ignoreRef.current = true;
      //isActive = false;
    };
  }, []);

  return { episode, error, isLoading };
}
