import * as PIXI from "pixi.js";

export const GUNMETAL_TILE_URL = "/assets/ui/chrome/low-res/gunmetal_tile.png";
export const GLASS_GLARE_URL = "/assets/ui/chrome/low-res/glass_glare.png";
export const NOISE_TILE_URL = "/assets/ui/fx/low-res/noise_tile.png";

export type ConsoleAssets = {
    gunmetalTile: PIXI.Texture;
    glassGlare: PIXI.Texture;
    noiseTile: PIXI.Texture;
};

let consoleAssetsPromise: Promise<ConsoleAssets> | null = null;

export async function loadConsoleAssets(): Promise<ConsoleAssets> {
    if (consoleAssetsPromise) return consoleAssetsPromise;

    consoleAssetsPromise = (async () => {
        try {
            const [gunmetalTile, glassGlare, noiseTile] = await Promise.all([
                PIXI.Assets.load<PIXI.Texture>(GUNMETAL_TILE_URL),
                PIXI.Assets.load<PIXI.Texture>(GLASS_GLARE_URL),
                PIXI.Assets.load<PIXI.Texture>(NOISE_TILE_URL),
            ]);
            return { gunmetalTile, glassGlare, noiseTile };
        } catch (error) {
            consoleAssetsPromise = null;
            throw error;
        }
    })();

    return consoleAssetsPromise;
}

export function textureToPublicUrl(texture: PIXI.Texture, fallbackUrl: string): string {
    const textureAny = texture as {
        source?: {
            resource?: unknown;
        };
    };
    const resource = textureAny.source?.resource;
    if (resource && typeof resource === "object") {
        const maybeSrc = (resource as { src?: unknown }).src;
        if (typeof maybeSrc === "string" && maybeSrc.length > 0) return maybeSrc;
        const maybeUrl = (resource as { url?: unknown }).url;
        if (typeof maybeUrl === "string" && maybeUrl.length > 0) return maybeUrl;
    }
    return fallbackUrl;
}
