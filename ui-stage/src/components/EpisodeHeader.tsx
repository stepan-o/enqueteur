import type { EpisodeViewModel } from "../vm/episodeVm";

export interface EpisodeHeaderProps {
  episode: EpisodeViewModel;
}

export default function EpisodeHeader({ episode }: EpisodeHeaderProps) {
  return (
    <header className="episode-header">
      <h1>Loopforge Stage Viewer</h1>
      <p>
        <strong>Episode:</strong> {episode.id ?? "—"}
        <br />
        <strong>Run:</strong> {episode.runId ?? "—"}
        <br />
        <strong>Days:</strong> {episode.days.length}
        <br />
        <strong>Stage Version:</strong> {episode.stageVersion}
      </p>
    </header>
  );
}
