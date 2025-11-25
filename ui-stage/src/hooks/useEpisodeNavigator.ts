import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

export interface EpisodeNavigatorApi {
  navigateToEpisode: (episodeId: string) => void;
}

export function useEpisodeNavigator(): EpisodeNavigatorApi {
  const navigate = useNavigate();

  const navigateToEpisode = useCallback(
    (episodeId: string) => {
      try {
        const id = String(episodeId || "").trim();
        // keep runtime stable even if id is malformed
        const path = id ? `/episodes/${encodeURIComponent(id)}` : "/episodes/";
        navigate(path);
      } catch (e) {
        // fail-soft: do nothing
        // eslint-disable-next-line no-console
        console.warn("navigateToEpisode failed", e);
      }
    },
    [navigate]
  );

  return { navigateToEpisode };
}

export default useEpisodeNavigator;
