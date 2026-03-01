import * as PIXI from "pixi.js";
import type { RoomArtKey } from "./roomArt";

export const GUNMETAL_TILE_URL = "/assets/ui/chrome/low-res/gunmetal_tile.png";
export const GLASS_GLARE_URL = "/assets/ui/chrome/low-res/glass_glare.png";
export const NOISE_TILE_URL = "/assets/ui/fx/low-res/noise_tile.png";
export const ROOM_CARD_SECURITY_URL = "/assets/cards/rooms/security.png";
export const ROOM_CARD_NEURAL_LATTICE_FORGE_URL = "/assets/cards/rooms/neural_lattice_forge.png";
export const ROOM_CARD_BURNIN_THEATRE_URL = "/assets/cards/rooms/burnin_theatre.png";
export const ROOM_CARD_COGNITION_SUBSTRATE_BREWERY_URL = "/assets/cards/rooms/cognition_substrate_brewery.png";
export const ROOM_CARD_SYNAPSE_WEAVING_GALLERY_URL = "/assets/cards/rooms/synapse_weaving_gallery.png";
export const ROOM_CARD_CORTEX_ASSEMBLY_LINE_URL = "/assets/cards/rooms/cortex_assembly_line.png";

export type ConsoleRoomCards = Record<RoomArtKey, PIXI.Texture>;

export type ConsoleAssets = {
    gunmetalTile: PIXI.Texture;
    glassGlare: PIXI.Texture;
    noiseTile: PIXI.Texture;
    roomCards: ConsoleRoomCards;
};

let consoleAssetsPromise: Promise<ConsoleAssets> | null = null;

export async function loadConsoleAssets(): Promise<ConsoleAssets> {
    if (consoleAssetsPromise) return consoleAssetsPromise;

    consoleAssetsPromise = (async () => {
        try {
            const [
                gunmetalTile,
                glassGlare,
                noiseTile,
                security,
                neuralLatticeForge,
                burninTheatre,
                cognitionSubstrateBrewery,
                synapseWeavingGallery,
                cortexAssemblyLine,
            ] = await Promise.all([
                PIXI.Assets.load<PIXI.Texture>(GUNMETAL_TILE_URL),
                PIXI.Assets.load<PIXI.Texture>(GLASS_GLARE_URL),
                PIXI.Assets.load<PIXI.Texture>(NOISE_TILE_URL),
                PIXI.Assets.load<PIXI.Texture>(ROOM_CARD_SECURITY_URL),
                PIXI.Assets.load<PIXI.Texture>(ROOM_CARD_NEURAL_LATTICE_FORGE_URL),
                PIXI.Assets.load<PIXI.Texture>(ROOM_CARD_BURNIN_THEATRE_URL),
                PIXI.Assets.load<PIXI.Texture>(ROOM_CARD_COGNITION_SUBSTRATE_BREWERY_URL),
                PIXI.Assets.load<PIXI.Texture>(ROOM_CARD_SYNAPSE_WEAVING_GALLERY_URL),
                PIXI.Assets.load<PIXI.Texture>(ROOM_CARD_CORTEX_ASSEMBLY_LINE_URL),
            ]);
            return {
                gunmetalTile,
                glassGlare,
                noiseTile,
                roomCards: {
                    security,
                    neural_lattice_forge: neuralLatticeForge,
                    burnin_theatre: burninTheatre,
                    cognition_substrate_brewery: cognitionSubstrateBrewery,
                    synapse_weaving_gallery: synapseWeavingGallery,
                    cortex_assembly_line: cortexAssemblyLine,
                },
            };
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
