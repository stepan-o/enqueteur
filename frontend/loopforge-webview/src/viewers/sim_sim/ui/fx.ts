import * as PIXI from "pixi.js";

export type ClarityMode = "crisp" | "normal" | "noisy";

export type GlobalNoiseOverlay = {
    sprite: PIXI.TilingSprite;
    setClarity: (mode: ClarityMode, pct?: number) => void;
    resize: (width: number, height: number) => void;
    destroy: () => void;
};

export function createGlobalNoiseOverlay(app: PIXI.Application, noiseTile: PIXI.Texture): GlobalNoiseOverlay {
    const sprite = new PIXI.TilingSprite({
        texture: noiseTile,
        width: Math.max(1, app.renderer.width),
        height: Math.max(1, app.renderer.height),
    });
    sprite.position.set(0, 0);
    sprite.eventMode = "none";
    sprite.blendMode = "normal";
    sprite.alpha = 0.16;

    app.stage.addChild(sprite);

    const setClarity = (mode: ClarityMode, pct = 0.5): void => {
        const t = clamp01(pct);
        const [minAlpha, maxAlpha] =
            mode === "crisp"
                ? [0.09, 0.13]
                : mode === "noisy"
                  ? [0.22, 0.34]
                  : [0.14, 0.2];
        sprite.alpha = minAlpha + ((maxAlpha - minAlpha) * t);
    };

    const resize = (width: number, height: number): void => {
        sprite.width = Math.max(1, Math.floor(width));
        sprite.height = Math.max(1, Math.floor(height));
    };

    const destroy = (): void => {
        if (sprite.parent) sprite.parent.removeChild(sprite);
        sprite.destroy();
    };

    return {
        sprite,
        setClarity,
        resize,
        destroy,
    };
}

function clamp01(value: number): number {
    if (!Number.isFinite(value)) return 0.5;
    return Math.max(0, Math.min(1, value));
}
