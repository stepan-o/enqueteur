import type { FrameDiffPayload, FullSnapshotPayload, KernelHello, WorldStore } from "../../state/worldStore";
import type { ViewerPlugin } from "../core/viewerPlugin";

type Sim4ViewerPluginOpts = {
    store: WorldStore;
    engineName?: string;
    onActivate?: () => void;
    onDeactivate?: () => void;
};

export function createSim4ViewerPlugin(opts: Sim4ViewerPluginOpts): ViewerPlugin {
    return {
        id: "sim4-schema1",
        engineName: opts.engineName ?? "Sim4",
        supportedSchemaVersions: ["1"],
        activate: () => {
            opts.onActivate?.();
        },
        deactivate: () => {
            opts.onDeactivate?.();
        },
        onKernelHello: (hello: KernelHello) => {
            opts.store.setKernelHello(hello);
        },
        onFullSnapshot: (payload: unknown) => {
            opts.store.applySnapshot(payload as FullSnapshotPayload);
        },
        onFrameDiff: (payload: unknown) => {
            opts.store.applyDiff(payload as FrameDiffPayload);
        },
    };
}
