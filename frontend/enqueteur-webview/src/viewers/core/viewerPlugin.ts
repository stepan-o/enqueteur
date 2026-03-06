import type { KernelHello } from "../../state/worldStore";

export type ViewerPlugin = {
    id: string;
    engineName: string;
    supportedSchemaVersions: readonly string[];
    activate: () => void;
    deactivate: () => void;
    onKernelHello: (hello: KernelHello) => void;
    onFullSnapshot: (payload: unknown) => void;
    onFrameDiff: (payload: unknown) => void;
};

export class ViewerPluginRegistry {
    private readonly pluginsByEngine = new Map<string, Map<string, ViewerPlugin>>();

    register(plugin: ViewerPlugin): void {
        let bySchema = this.pluginsByEngine.get(plugin.engineName);
        if (!bySchema) {
            bySchema = new Map<string, ViewerPlugin>();
            this.pluginsByEngine.set(plugin.engineName, bySchema);
        }
        for (const schemaVersion of plugin.supportedSchemaVersions) {
            bySchema.set(schemaVersion, plugin);
        }
    }

    resolve(engineName: string, schemaVersion: string): ViewerPlugin | null {
        const bySchema = this.pluginsByEngine.get(engineName);
        if (!bySchema) return null;
        return bySchema.get(schemaVersion) ?? null;
    }

    supportedSchemaVersions(): string[] {
        const out = new Set<string>();
        for (const bySchema of this.pluginsByEngine.values()) {
            for (const schemaVersion of bySchema.keys()) out.add(schemaVersion);
        }
        return Array.from(out.values()).sort();
    }

    describeMappings(): string {
        const rows: string[] = [];
        for (const [engineName, bySchema] of this.pluginsByEngine.entries()) {
            rows.push(`${engineName}:[${Array.from(bySchema.keys()).sort().join(",")}]`);
        }
        return rows.sort().join(" ");
    }
}

