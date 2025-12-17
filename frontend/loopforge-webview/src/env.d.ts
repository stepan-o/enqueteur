// src/env.d.ts
interface ImportMetaEnv {
    readonly VITE_KVP_WS_URL?: string;
}
interface ImportMeta {
    readonly env: ImportMetaEnv;
}