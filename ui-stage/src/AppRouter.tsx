import { Routes, Route } from "react-router-dom";
import AppShell from "./AppShell";
import LatestEpisodeView from "./routes/LatestEpisodeView";
import EpisodesListPlaceholder from "./routes/EpisodesListPlaceholder";
import AgentsPlaceholder from "./routes/AgentsPlaceholder";
import SettingsPlaceholder from "./routes/SettingsPlaceholder";

export default function AppRouter() {

  console.log("Render AppRouter");

  return (
    <Routes>
      <Route path="/" element={<AppShell />}> 
        <Route index element={<LatestEpisodeView />} />
        <Route path="episodes" element={<EpisodesListPlaceholder />} />
        <Route path="agents" element={<AgentsPlaceholder />} />
        <Route path="settings" element={<SettingsPlaceholder />} />
      </Route>
    </Routes>
  );
}
