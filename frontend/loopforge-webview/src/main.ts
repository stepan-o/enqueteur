import "./styles/app.css";
import { boot } from "./app/boot";

const app = document.getElementById("app");
if (!app) throw new Error("#app not found");

boot({
    mountEl: app,
    wsUrl: import.meta.env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp",
    offlineBaseUrl: import.meta.env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min",
    mode: (import.meta.env.VITE_WEBVIEW_MODE ?? "offline") as "live" | "offline",
});
