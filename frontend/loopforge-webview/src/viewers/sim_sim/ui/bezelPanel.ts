import {
    CONSOLE_SKIN,
    borderColorForTone,
    glassColorForTone,
    glowForTone,
    type ConsoleSkinTone,
} from "./skin";
import {
    GLASS_GLARE_URL,
    GUNMETAL_TILE_URL,
    textureToPublicUrl,
    type ConsoleAssets,
} from "./assets";

export type BezelPanelHandle = {
    root: HTMLDivElement;
    contentEl: HTMLDivElement;
    setTitle: (title: string) => void;
    setChips: (chips: string[]) => void;
    setTone: (tone: ConsoleSkinTone) => void;
};

export type BezelPanelOpts = {
    title?: string;
    chips?: string[];
    tone?: ConsoleSkinTone;
    pointerEvents?: "none" | "auto";
    assets?: ConsoleAssets;
    tileTint?: string;
};

export function createBezelPanel(opts: BezelPanelOpts = {}): BezelPanelHandle {
    const gunmetalUrl = opts.assets
        ? textureToPublicUrl(opts.assets.gunmetalTile, GUNMETAL_TILE_URL)
        : GUNMETAL_TILE_URL;
    const glassGlareUrl = opts.assets
        ? textureToPublicUrl(opts.assets.glassGlare, GLASS_GLARE_URL)
        : GLASS_GLARE_URL;
    const tileTint = opts.tileTint ?? "rgba(10, 16, 24, 0.22)";

    const root = document.createElement("div");
    root.style.position = "absolute";
    root.style.overflow = "hidden";
    root.style.borderRadius = `${CONSOLE_SKIN.radii.bezelPx}px`;
    root.style.pointerEvents = opts.pointerEvents ?? "none";

    const bezel = document.createElement("div");
    bezel.style.position = "absolute";
    bezel.style.inset = "0";
    bezel.style.borderRadius = `${CONSOLE_SKIN.radii.bezelPx}px`;
    bezel.style.border = `${CONSOLE_SKIN.stroke.bezelPx}px solid ${borderColorForTone(opts.tone ?? "neutral")}`;
    bezel.style.background = "rgba(7, 12, 18, 0.94)";
    bezel.style.boxShadow = glowForTone(opts.tone ?? "neutral");

    const bezelTexture = document.createElement("div");
    bezelTexture.style.position = "absolute";
    bezelTexture.style.inset = "0";
    bezelTexture.style.borderRadius = `${CONSOLE_SKIN.radii.bezelPx}px`;
    bezelTexture.style.pointerEvents = "none";
    bezelTexture.style.backgroundImage = `url("${gunmetalUrl}")`;
    bezelTexture.style.backgroundRepeat = "repeat";
    bezelTexture.style.backgroundSize = "420px 420px";
    bezelTexture.style.opacity = "0.92";
    bezelTexture.style.filter = "contrast(1.55) brightness(1.22) saturate(0.86)";
    bezel.appendChild(bezelTexture);

    const bezelTintLayer = document.createElement("div");
    bezelTintLayer.style.position = "absolute";
    bezelTintLayer.style.inset = "0";
    bezelTintLayer.style.borderRadius = `${CONSOLE_SKIN.radii.bezelPx}px`;
    bezelTintLayer.style.pointerEvents = "none";
    bezelTintLayer.style.background = [
        `linear-gradient(0deg, ${tileTint}, ${tileTint})`,
        "linear-gradient(162deg, rgba(16, 24, 34, 0.16), rgba(10, 16, 24, 0.22) 58%, rgba(6, 10, 16, 0.34))",
    ].join(", ");
    bezel.appendChild(bezelTintLayer);
    root.appendChild(bezel);

    const glass = document.createElement("div");
    glass.style.position = "absolute";
    glass.style.inset = "6px";
    glass.style.borderRadius = `${CONSOLE_SKIN.radii.glassPx}px`;
    glass.style.border = `${CONSOLE_SKIN.stroke.glassPx}px solid rgba(154, 166, 182, 0.26)`;
    glass.style.background = glassColorForTone(opts.tone ?? "neutral");
    glass.style.overflow = "hidden";

    const glassTexture = document.createElement("div");
    glassTexture.style.position = "absolute";
    glassTexture.style.inset = "0";
    glassTexture.style.pointerEvents = "none";
    glassTexture.style.backgroundImage = `url("${gunmetalUrl}")`;
    glassTexture.style.backgroundRepeat = "repeat";
    glassTexture.style.backgroundSize = "360px 360px";
    glassTexture.style.opacity = "0.58";
    glassTexture.style.filter = "contrast(1.45) brightness(1.16) saturate(0.84)";
    glassTexture.style.mixBlendMode = "normal";
    glass.appendChild(glassTexture);
    root.appendChild(glass);

    const glare = document.createElement("div");
    glare.style.position = "absolute";
    glare.style.inset = "0";
    glare.style.pointerEvents = "none";
    glare.style.opacity = "0.3";
    glare.style.backgroundImage = [
        "linear-gradient(156deg, rgba(255, 255, 255, 0.32) 0%, rgba(255, 255, 255, 0.14) 22%, rgba(255, 255, 255, 0.03) 52%)",
        `url("${glassGlareUrl}")`,
    ].join(", ");
    glare.style.backgroundRepeat = "no-repeat, no-repeat";
    glare.style.backgroundPosition = "center center, center center";
    glare.style.backgroundSize = "100% 100%, 125% 125%";
    glare.style.mixBlendMode = "screen";
    glass.appendChild(glare);

    const titleEl = document.createElement("div");
    titleEl.style.position = "absolute";
    titleEl.style.left = "12px";
    titleEl.style.top = "10px";
    titleEl.style.fontSize = `${CONSOLE_SKIN.typography.stripHeaderPx}px`;
    titleEl.style.fontWeight = "700";
    titleEl.style.letterSpacing = "0.08em";
    titleEl.style.textTransform = "uppercase";
    titleEl.style.color = CONSOLE_SKIN.colors.textMuted;
    titleEl.style.pointerEvents = "none";
    titleEl.textContent = opts.title ?? "";
    if (titleEl.textContent.length > 0) {
        glass.appendChild(titleEl);
    }

    const chipsEl = document.createElement("div");
    chipsEl.style.position = "absolute";
    chipsEl.style.top = "8px";
    chipsEl.style.right = "10px";
    chipsEl.style.display = "flex";
    chipsEl.style.alignItems = "center";
    chipsEl.style.flexWrap = "wrap";
    chipsEl.style.gap = "6px";
    chipsEl.style.pointerEvents = "none";
    glass.appendChild(chipsEl);

    const contentEl = document.createElement("div");
    contentEl.style.position = "absolute";
    contentEl.style.inset = "30px 10px 10px 10px";
    contentEl.style.minHeight = "0";
    contentEl.style.overflow = "hidden";
    contentEl.style.pointerEvents = opts.pointerEvents ?? "none";
    glass.appendChild(contentEl);

    const setTitle = (title: string): void => {
        titleEl.textContent = title;
        if (title.trim().length === 0) {
            if (titleEl.parentElement) titleEl.remove();
            return;
        }
        if (!titleEl.parentElement) glass.appendChild(titleEl);
    };

    const setChips = (chips: string[]): void => {
        chipsEl.innerHTML = "";
        for (const chipText of chips) {
            const chip = document.createElement("span");
            chip.textContent = chipText;
            chip.style.display = "inline-flex";
            chip.style.alignItems = "center";
            chip.style.height = "18px";
            chip.style.padding = "0 7px";
            chip.style.borderRadius = "999px";
            chip.style.border = "1px solid rgba(195, 154, 82, 0.72)";
            chip.style.background = "rgba(36, 27, 13, 0.72)";
            chip.style.color = CONSOLE_SKIN.colors.textPrimary;
            chip.style.fontSize = `${CONSOLE_SKIN.typography.microLabelPx}px`;
            chip.style.lineHeight = "1";
            chip.style.letterSpacing = "0.04em";
            chip.style.textTransform = "uppercase";
            chipsEl.appendChild(chip);
        }
        chipsEl.style.display = chips.length > 0 ? "flex" : "none";
    };

    const setTone = (tone: ConsoleSkinTone): void => {
        bezel.style.borderColor = borderColorForTone(tone);
        bezel.style.boxShadow = glowForTone(tone);
        glass.style.background = glassColorForTone(tone);
    };

    setChips(opts.chips ?? []);

    return {
        root,
        contentEl,
        setTitle,
        setChips,
        setTone,
    };
}
