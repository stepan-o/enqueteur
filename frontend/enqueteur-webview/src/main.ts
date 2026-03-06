import "./styles/app.css";
import { boot, type ViewerHandle } from "./app/boot";

const app = document.getElementById("app");
if (!app) throw new Error("#app not found");

const env = (import.meta as any).env ?? {};
const wsUrl = env.VITE_KVP_WS_URL_SIM4 ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp";
const offlineBaseUrl = env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min";

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

controls.appendChild(liveBtn);
controls.appendChild(offlineBtn);
controls.appendChild(offlineInput);
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
    void viewer.startOffline(target, 1);
});
