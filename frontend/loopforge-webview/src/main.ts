import "./styles/app.css";
import { boot } from "./app/boot";
import type { ViewerHandle } from "./app/boot";
import { createMenu, type MenuAction, type MenuRun } from "./ui/menu";

const app = document.getElementById("app");
if (!app) throw new Error("#app not found");

const env = (import.meta as any).env ?? {};
const sim4WsUrl = env.VITE_KVP_WS_URL_SIM4 ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp";
const simSimWsUrl = env.VITE_KVP_WS_URL_SIM_SIM ?? "ws://localhost:7777/kvp";

const menuRoot = document.createElement("div");
const viewerRoot = document.createElement("div");
const fadeLayer = document.createElement("div");
menuRoot.className = "menu-shell";
viewerRoot.className = "viewer-root";
fadeLayer.className = "fade-layer";

app.appendChild(menuRoot);
app.appendChild(viewerRoot);
app.appendChild(fadeLayer);

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
        wsUrl: sim4WsUrl,
        sim4WsUrl,
        simSimWsUrl,
        offlineBaseUrl: env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min",
        mode: "offline",
        autoStart: false,
    });
} catch (err) {
    const msg = err instanceof Error ? err.stack ?? err.message : String(err);
    console.error("[webview] boot failed", msg);
    const crash = document.createElement("div");
    crash.style.position = "absolute";
    crash.style.left = "16px";
    crash.style.top = "16px";
    crash.style.zIndex = "9999";
    crash.style.maxWidth = "min(90vw, 720px)";
    crash.style.padding = "10px 12px";
    crash.style.borderRadius = "10px";
    crash.style.background = "rgba(46, 12, 12, 0.92)";
    crash.style.color = "#ffd9cf";
    crash.style.fontFamily = "monospace";
    crash.style.fontSize = "12px";
    crash.style.whiteSpace = "pre-wrap";
    crash.textContent = `[webview] boot failed\n${msg}`;
    app.appendChild(crash);
}

viewer.setVisible(false);
viewer.setDevControlsVisible(true);
viewer.setHudVisible(true);

const runs: MenuRun[] = [
    {
        id: "kvp_demo_1min",
        label: "1 Minute Demo",
        detail: "30 Hz · Loopforge demo",
        baseUrl: env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min",
    },
];

const menu = createMenu(handleMenuAction);
menuRoot.appendChild(menu.root);
menu.setRuns(runs);
menu.setDevBackground("/assets/concept_art/world/loopforge_factory_floor_1_map.png");

const factoryBackgrounds = [
    "/assets/concept_art/world/loopforge_factory_entrance_1.png",
    "/assets/concept_art/world/loopforge_factory_entrance_2.png",
    "/assets/concept_art/world/loopforge_factory_entrance_3.png",
];

const viewerExit = document.createElement("button");
viewerExit.className = "viewer-exit";
viewerExit.type = "button";
viewerExit.textContent = "Exit to menu";
viewerExit.addEventListener("click", () => {
    void transitionTo(() => {
        viewer.stop();
        viewer.setVisible(false);
        menuRoot.style.display = "block";
        menu.setScreen("dev");
    });
});
viewerRoot.appendChild(viewerExit);

function handleMenuAction(action: MenuAction): void {
    switch (action.type) {
        case "GO_FACTORY": {
            const bg = factoryBackgrounds[Math.floor(Math.random() * factoryBackgrounds.length)];
            void transitionTo(() => {
                menu.setFactoryBackground(bg);
                menu.setScreen("factory");
            });
            return;
        }
        case "OPEN_DEV": {
            void transitionTo(() => {
                menu.setScreen("dev");
            });
            return;
        }
        case "OPEN_CINEMATIC": {
            void transitionTo(() => {
                menu.setScreen("cinematic");
            });
            return;
        }
        case "OPEN_LIVE_SIM4": {
            void transitionTo(() => {
                viewer.setVisible(true);
                menuRoot.style.display = "none";
                viewer.startLive({ kernelKind: "sim4" });
            });
            return;
        }
        case "OPEN_LIVE_SIM_SIM": {
            void transitionTo(() => {
                viewer.setVisible(true);
                menuRoot.style.display = "none";
                viewer.startLive({ kernelKind: "sim_sim" });
            });
            return;
        }
        case "ABOUT_FACTORY": {
            void transitionTo(() => {
                menu.setScreen("about_factory");
            });
            return;
        }
        case "ABOUT_PROJECT": {
            void transitionTo(() => {
                menu.setScreen("about_project");
            });
            return;
        }
        case "CONTACT": {
            void transitionTo(() => {
                menu.setScreen("contact");
            });
            return;
        }
        case "BACK_MAIN": {
            void transitionTo(() => {
                menu.setScreen("main");
            });
            return;
        }
        case "RUN_SELECTED": {
            void transitionTo(() => {
                viewer.setVisible(true);
                menuRoot.style.display = "none";
                void viewer.startOffline(action.run.baseUrl);
            });
            return;
        }
        case "SOUND_TOGGLE": {
            return;
        }
        default:
            return;
    }
}

function transitionTo(action: () => void): Promise<void> {
    fadeLayer.classList.add("is-active");
    return new Promise((resolve) => {
        window.setTimeout(() => {
            action();
            fadeLayer.classList.remove("is-active");
            window.setTimeout(resolve, 520);
        }, 520);
    });
}
