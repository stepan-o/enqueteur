// src/env.d.ts
interface ImportMetaEnv {
    readonly VITE_KVP_WS_URL?: string;
    readonly VITE_KVP_WS_URL_SIM4?: string;
    readonly VITE_KVP_WS_URL_SIM_SIM?: string;
    readonly VITE_WEBVIEW_MODE?: "live" | "offline";
    readonly VITE_WEBVIEW_RUN_BASE?: string;
    readonly VITE_WEBVIEW_RUN_BASE_MBAM_A?: string;
    readonly VITE_WEBVIEW_RUN_BASE_MBAM_B?: string;
    readonly VITE_WEBVIEW_RUN_BASE_MBAM_C?: string;
    readonly VITE_WEBVIEW_SPEED?: string;
    readonly VITE_WEBVIEW_MOCK?: string;
    readonly VITE_WEBVIEW_DISABLE_WS?: string;
}
interface ImportMeta {
    readonly env: ImportMetaEnv;
}
