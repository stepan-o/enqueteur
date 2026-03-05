import * as PIXI from "pixi.js";
import type { RoomArtKey } from "./roomArt";

export const GUNMETAL_TILE_URL = "/assets/ui/chrome/low-res/gunmetal_tile.png";
export const GLASS_GLARE_URL = "/assets/ui/chrome/low-res/glass_glare.png";
export const NOISE_TILE_URL = "/assets/ui/fx/low-res/noise_tile.png";
export const TOPSTRIP_PLATE_URL = "/assets/ui/chrome/low-res/topstrip_plate.png";
export const ICON_CASH_URL = "/assets/ui/icons/low-res/cash.png";
export const ICON_CASH_HOVER_URL = "/assets/ui/icons/low-res/cash_hover.png";
export const ICON_CASH_SELECT_URL = "/assets/ui/icons/low-res/cash_select.png";
export const ICON_WORKERS_DUMB_URL = "/assets/ui/icons/low-res/workers_dumb.png";
export const ICON_WORKERS_DUMB_HOVER_URL = "/assets/ui/icons/low-res/workers_dumb_hover.png";
export const ICON_WORKERS_DUMB_SELECT_URL = "/assets/ui/icons/low-res/workers_dumb_select.png";
export const ICON_WORKERS_SMART_URL = "/assets/ui/icons/low-res/workers_smart.png";
export const ICON_WORKERS_SMART_HOVER_URL = "/assets/ui/icons/low-res/workers_smart_hover.png";
export const ICON_WORKERS_SMART_SELECT_URL = "/assets/ui/icons/low-res/workers_smart_select.png";
export const ICON_SIGNAL_URL = "/assets/ui/icons/low-res/signal.png";
export const ICON_SIGNAL_HOVER_URL = "/assets/ui/icons/low-res/signal_hover.png";
export const ICON_SIGNAL_SELECT_URL = "/assets/ui/icons/low-res/signal_select.png";
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

export type UiIconVariants = {
    base: PIXI.Texture;
    hover: PIXI.Texture;
    select: PIXI.Texture;
};

export type UiAssets = {
    icons: {
        cash: UiIconVariants;
        workersDumb: UiIconVariants;
        workersSmart: UiIconVariants;
        signal: UiIconVariants;
    };
    chrome: {
        topStripPlate: PIXI.Texture;
    };
};

type AssetBundle = {
    console: ConsoleAssets;
    ui: UiAssets;
};

let assetBundlePromise: Promise<AssetBundle> | null = null;

async function loadAssetBundle(): Promise<AssetBundle> {
    if (assetBundlePromise) return assetBundlePromise;

    assetBundlePromise = (async () => {
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
                topStripPlate,
                cashBase,
                cashHover,
                cashSelect,
                workersDumbBase,
                workersDumbHover,
                workersDumbSelect,
                workersSmartBase,
                workersSmartHover,
                workersSmartSelect,
                signalBase,
                signalHover,
                signalSelect,
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
                PIXI.Assets.load<PIXI.Texture>(TOPSTRIP_PLATE_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_CASH_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_CASH_HOVER_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_CASH_SELECT_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_WORKERS_DUMB_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_WORKERS_DUMB_HOVER_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_WORKERS_DUMB_SELECT_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_WORKERS_SMART_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_WORKERS_SMART_HOVER_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_WORKERS_SMART_SELECT_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_SIGNAL_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_SIGNAL_HOVER_URL),
                PIXI.Assets.load<PIXI.Texture>(ICON_SIGNAL_SELECT_URL),
            ]);
            return {
                console: {
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
                },
                ui: {
                    icons: {
                        cash: {
                            base: cashBase,
                            hover: cashHover,
                            select: cashSelect,
                        },
                        workersDumb: {
                            base: workersDumbBase,
                            hover: workersDumbHover,
                            select: workersDumbSelect,
                        },
                        workersSmart: {
                            base: workersSmartBase,
                            hover: workersSmartHover,
                            select: workersSmartSelect,
                        },
                        signal: {
                            base: signalBase,
                            hover: signalHover,
                            select: signalSelect,
                        },
                    },
                    chrome: {
                        topStripPlate,
                    },
                },
            };
        } catch (error) {
            assetBundlePromise = null;
            throw error;
        }
    })();

    return assetBundlePromise;
}

export async function loadConsoleAssets(): Promise<ConsoleAssets> {
    const bundle = await loadAssetBundle();
    return bundle.console;
}

export async function loadUiAssets(): Promise<UiAssets> {
    const bundle = await loadAssetBundle();
    return bundle.ui;
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
