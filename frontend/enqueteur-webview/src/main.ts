import "./styles/app.css";
import { boot, type ViewerHandle } from "./app/boot";
import { resolveMbamSeedRunBases, type MbamSeedId } from "./app/mbamReplaySeeds";

const app = document.getElementById("app");
if (!app) throw new Error("#app not found");

const env = (import.meta as any).env ?? {};
const wsUrl = env.VITE_KVP_WS_URL_SIM4 ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp";
const offlineBaseUrl = env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min";
const seedRunBases = resolveMbamSeedRunBases(env, offlineBaseUrl);
const hasDistinctSeedRunBases = new Set(Object.values(seedRunBases)).size > 1;

const chrome = document.createElement("div");
chrome.className = "app-chrome";

const title = document.createElement("div");
title.className = "app-title";
title.textContent = "Enqueteur Dev Viewer";

const controls = document.createElement("div");
controls.className = "app-controls";

const liveBtn = document.createElement("button");
liveBtn.type = "button";
liveBtn.textContent = "Live";

const offlineBtn = document.createElement("button");
offlineBtn.type = "button";
offlineBtn.textContent = "Offline";

const offlineInput = document.createElement("input");
offlineInput.type = "text";
offlineInput.className = "run-input";
offlineInput.value = offlineBaseUrl;
offlineInput.placeholder = "/demo/kvp_demo_1min";

const seedControls = document.createElement("div");
seedControls.className = "seed-controls";
const seedLabel = document.createElement("span");
seedLabel.className = "seed-controls-label";
seedLabel.textContent = "MBAM Seed";
if (!hasDistinctSeedRunBases) {
    seedLabel.title = "Set VITE_WEBVIEW_RUN_BASE_MBAM_A/B/C for distinct seed replay shortcuts.";
}
seedControls.appendChild(seedLabel);

const seedButtons: Record<MbamSeedId, HTMLButtonElement> = {
    A: makeSeedButton("Seed A"),
    B: makeSeedButton("Seed B"),
    C: makeSeedButton("Seed C"),
};
let activeSeedButton: MbamSeedId | null = null;

const setActiveSeedButton = (seed: MbamSeedId | null): void => {
    activeSeedButton = seed;
    (Object.keys(seedButtons) as MbamSeedId[]).forEach((seedId) => {
        const isActive = hasDistinctSeedRunBases && seedId === activeSeedButton;
        seedButtons[seedId].dataset.active = isActive ? "true" : "false";
    });
};

const loadSeedReplay = (seed: MbamSeedId): void => {
    const base = seedRunBases[seed] || offlineBaseUrl;
    offlineInput.value = base;
    setActiveSeedButton(seed);
    void viewer.startOffline(base, 1);
};

(Object.keys(seedButtons) as MbamSeedId[]).forEach((seed) => {
    seedButtons[seed].addEventListener("click", () => loadSeedReplay(seed));
    seedControls.appendChild(seedButtons[seed]);
});
const initialSeed = (Object.keys(seedRunBases) as MbamSeedId[]).find((seed) => seedRunBases[seed] === offlineBaseUrl) ?? null;
setActiveSeedButton(initialSeed);

controls.appendChild(liveBtn);
controls.appendChild(offlineBtn);
controls.appendChild(offlineInput);
controls.appendChild(seedControls);
chrome.appendChild(title);
chrome.appendChild(controls);

const viewerRoot = document.createElement("div");
viewerRoot.className = "viewer-root";

app.appendChild(chrome);
app.appendChild(viewerRoot);

const fallbackViewer: ViewerHandle = {
    startOffline: async () => {},
    startLive: () => {},
    stop: () => {},
    setVisible: () => {},
    setDevControlsVisible: () => {},
    setHudVisible: () => {},
};

let viewer: ViewerHandle = fallbackViewer;
try {
    viewer = boot({
        mountEl: viewerRoot,
        wsUrl,
        offlineBaseUrl,
        mode: "offline",
        autoStart: true,
    });
} catch (err) {
    const msg = err instanceof Error ? err.stack ?? err.message : String(err);
    const crash = document.createElement("pre");
    crash.className = "boot-error";
    crash.textContent = `[webview] boot failed\n${msg}`;
    app.appendChild(crash);
}

viewer.setVisible(true);
viewer.setDevControlsVisible(true);
viewer.setHudVisible(true);

liveBtn.addEventListener("click", () => {
    viewer.startLive(wsUrl);
});

offlineBtn.addEventListener("click", () => {
    const target = (offlineInput.value || "").trim() || offlineBaseUrl;
    const matchingSeed = (Object.keys(seedRunBases) as MbamSeedId[]).find((seed) => seedRunBases[seed] === target) ?? null;
    setActiveSeedButton(matchingSeed);
    void viewer.startOffline(target, 1);
});

function makeSeedButton(label: string): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "seed-btn";
    btn.textContent = label;
    btn.dataset.active = "false";
    return btn;
}
