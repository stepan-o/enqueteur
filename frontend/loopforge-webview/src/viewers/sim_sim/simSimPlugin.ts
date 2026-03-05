import type { KernelHello } from "../../state/worldStore";
import type { ViewerPlugin } from "../core/viewerPlugin";
import { SIM_SIM_SCHEMA_VERSION, SimSimStore, type SimSimFrameDiffPayload, type SimSimSnapshotPayload } from "./simSimStore";

type SimSimViewerPluginOpts = {
    store: SimSimStore;
    onActivate?: () => void;
    onDeactivate?: () => void;
};

export function createSimSimViewerPlugin(opts: SimSimViewerPluginOpts): ViewerPlugin {
    return {
        id: "sim-sim-schema1",
        engineName: "sim_sim",
        supportedSchemaVersions: [SIM_SIM_SCHEMA_VERSION],
        activate: () => {
            opts.onActivate?.();
        },
        deactivate: () => {
            opts.onDeactivate?.();
        },
        onKernelHello: (hello: KernelHello) => {
            opts.store.setKernelHello(hello);
            opts.store.clearDesync();
        },
        onFullSnapshot: (payload: unknown) => {
            opts.store.applySnapshot(payload as SimSimSnapshotPayload);
        },
        onFrameDiff: (payload: unknown) => {
            opts.store.applyDiff(payload as SimSimFrameDiffPayload);
        },
    };
}

