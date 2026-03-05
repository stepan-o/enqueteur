import * as PIXI from "pixi.js";
import type { UiAudio } from "../audio";

export type IconButtonState = "base" | "hover" | "select";

export type IconButtonTextures = {
    base: PIXI.Texture;
    hover: PIXI.Texture;
    select: PIXI.Texture;
};

export type IconButtonHandle = {
    container: PIXI.Container;
    setSelected: (selected: boolean) => void;
    setHovered: (hovered: boolean, options?: { playAudio?: boolean }) => void;
    setEnabled: (enabled: boolean) => void;
    destroy: () => void;
};

type CreateIconButtonArgs = {
    textures: IconButtonTextures;
    sizePx: number;
    onClick?: () => void;
    isToggle?: boolean;
    getIsSelected?: () => boolean;
    audio?: UiAudio;
};

const ICON_BUTTON_TUNING = {
    alpha: {
        base: 0.95,
        hover: 1,
        select: 1,
    },
    scale: {
        base: 1,
        hover: 1.04,
        selectSettle: 1.02,
        press: 0.96,
        pop: 1.06,
    },
    durationMs: {
        hoverIn: 140,
        dismiss: 120,
        press: 55,
        pop: 95,
        settle: 80,
        clickHold: 300,
        ringPulse: 220,
    },
    ring: {
        color: 0x84b9ca,
        strokePx: 1.5,
        startScale: 0.95,
        endScale: 1.4,
        startAlpha: 0.34,
        endAlpha: 0,
    },
} as const;

type AnimationValues = {
    scale: number;
    alpha: number;
    ringScale: number;
    ringAlpha: number;
};

type AnimationStage = {
    target: Partial<AnimationValues>;
    durationMs: number;
    ease?: (t: number) => number;
};

export function createIconButton(args: CreateIconButtonArgs): IconButtonHandle {
    const textures = args.textures;
    const uiAudio = args.audio;
    const container = new PIXI.Container();
    const sprite = new PIXI.Sprite(textures.base ?? PIXI.Texture.WHITE);
    const ring = new PIXI.Graphics();
    const hitArea = new PIXI.Graphics();

    const baseSize = fitToSquare(textures.base ?? PIXI.Texture.WHITE, args.sizePx);
    const boxW = Math.max(1, Math.ceil(baseSize.width));
    const boxH = Math.max(1, Math.ceil(baseSize.height));
    const centerX = boxW * 0.5;
    const centerY = boxH * 0.5;

    sprite.anchor.set(0.5, 0.5);
    sprite.position.set(centerX, centerY);
    sprite.alpha = ICON_BUTTON_TUNING.alpha.base;

    redrawRing(ring, Math.max(boxW, boxH) * 0.56);
    ring.position.set(centerX, centerY);
    ring.visible = false;

    hitArea.rect(0, 0, boxW, boxH);
    hitArea.fill({ color: 0xffffff, alpha: 0.001 });

    container.addChild(hitArea, ring, sprite);
    container.eventMode = "static";
    container.cursor = "pointer";
    container.hitArea = new PIXI.Rectangle(0, 0, boxW, boxH);

    const fitByState: Record<IconButtonState, number> = {
        base: fitScaleToBox(textures.base ?? PIXI.Texture.WHITE, boxW, boxH),
        hover: fitScaleToBox(textures.hover ?? textures.base ?? PIXI.Texture.WHITE, boxW, boxH),
        select: fitScaleToBox(textures.select ?? textures.base ?? PIXI.Texture.WHITE, boxW, boxH),
    };

    let enabled = true;
    let hovered = false;
    let externallyHovered = false;
    let internalSelected = false;
    let currentState: IconButtonState = "base";
    let currentValues: AnimationValues = {
        scale: ICON_BUTTON_TUNING.scale.base,
        alpha: ICON_BUTTON_TUNING.alpha.base,
        ringScale: ICON_BUTTON_TUNING.ring.startScale,
        ringAlpha: 0,
    };

    let animationNonce = 0;
    let rafId: number | null = null;
    let clickHoldTimeoutId: number | null = null;

    const clearClickHold = (): void => {
        if (clickHoldTimeoutId !== null) {
            window.clearTimeout(clickHoldTimeoutId);
            clickHoldTimeoutId = null;
        }
    };

    const cancelAnimations = (): void => {
        animationNonce += 1;
        if (rafId !== null) {
            window.cancelAnimationFrame(rafId);
            rafId = null;
        }
    };

    const isSelected = (): boolean => {
        const externalSelected = args.getIsSelected?.() ?? false;
        return externalSelected || internalSelected;
    };
    const isHovered = (): boolean => hovered || externallyHovered;

    const applyVisual = (): void => {
        const fitScale = fitByState[currentState] ?? fitByState.base;
        sprite.scale.set(fitScale * currentValues.scale, fitScale * currentValues.scale);
        sprite.alpha = currentValues.alpha;
        ring.visible = currentValues.ringAlpha > 0.005;
        ring.scale.set(currentValues.ringScale, currentValues.ringScale);
        ring.alpha = currentValues.ringAlpha;
    };

    const setTextureState = (state: IconButtonState): void => {
        currentState = state;
        const texture = state === "hover" ? textures.hover : state === "select" ? textures.select : textures.base;
        sprite.texture = texture ?? textures.base ?? PIXI.Texture.WHITE;
        applyVisual();
    };

    const runAnimation = (stages: AnimationStage[]): void => {
        cancelAnimations();
        const nonce = animationNonce;
        let stageIndex = 0;
        const runStage = (): void => {
            if (nonce !== animationNonce) return;
            if (stageIndex >= stages.length) {
                rafId = null;
                return;
            }
            const stage = stages[stageIndex];
            const startValues = { ...currentValues };
            const targetValues: AnimationValues = {
                scale: stage.target.scale ?? startValues.scale,
                alpha: stage.target.alpha ?? startValues.alpha,
                ringScale: stage.target.ringScale ?? startValues.ringScale,
                ringAlpha: stage.target.ringAlpha ?? startValues.ringAlpha,
            };
            const duration = Math.max(1, stage.durationMs);
            const ease = stage.ease ?? easeOutCubic;
            const startAt = performance.now();
            const step = (now: number): void => {
                if (nonce !== animationNonce) return;
                const t = Math.max(0, Math.min(1, (now - startAt) / duration));
                const k = ease(t);
                currentValues = {
                    scale: lerp(startValues.scale, targetValues.scale, k),
                    alpha: lerp(startValues.alpha, targetValues.alpha, k),
                    ringScale: lerp(startValues.ringScale, targetValues.ringScale, k),
                    ringAlpha: lerp(startValues.ringAlpha, targetValues.ringAlpha, k),
                };
                applyVisual();
                if (t >= 1) {
                    stageIndex += 1;
                    runStage();
                    return;
                }
                rafId = window.requestAnimationFrame(step);
            };
            rafId = window.requestAnimationFrame(step);
        };
        runStage();
    };

    const animateHover = (): void => {
        setTextureState("hover");
        runAnimation([
            {
                target: {
                    scale: ICON_BUTTON_TUNING.scale.hover,
                    alpha: ICON_BUTTON_TUNING.alpha.hover,
                    ringAlpha: 0,
                },
                durationMs: ICON_BUTTON_TUNING.durationMs.hoverIn,
            },
        ]);
    };

    const animateDismiss = (): void => {
        setTextureState("base");
        runAnimation([
            {
                target: {
                    scale: ICON_BUTTON_TUNING.scale.base,
                    alpha: ICON_BUTTON_TUNING.alpha.base,
                    ringScale: ICON_BUTTON_TUNING.ring.startScale,
                    ringAlpha: 0,
                },
                durationMs: ICON_BUTTON_TUNING.durationMs.dismiss,
            },
        ]);
    };

    const animateSelect = (): void => {
        setTextureState("select");
        runAnimation([
            {
                target: {
                    scale: ICON_BUTTON_TUNING.scale.press,
                    alpha: ICON_BUTTON_TUNING.alpha.select,
                    ringScale: ICON_BUTTON_TUNING.ring.startScale,
                    ringAlpha: ICON_BUTTON_TUNING.ring.startAlpha,
                },
                durationMs: ICON_BUTTON_TUNING.durationMs.press,
            },
            {
                target: {
                    scale: ICON_BUTTON_TUNING.scale.pop,
                    ringScale: ICON_BUTTON_TUNING.ring.endScale,
                    ringAlpha: ICON_BUTTON_TUNING.ring.endAlpha,
                },
                durationMs: ICON_BUTTON_TUNING.durationMs.pop,
            },
            {
                target: {
                    scale: ICON_BUTTON_TUNING.scale.selectSettle,
                    alpha: ICON_BUTTON_TUNING.alpha.select,
                },
                durationMs: ICON_BUTTON_TUNING.durationMs.settle,
            },
        ]);
    };

    const syncStateFromFlags = (withAnimation: boolean): void => {
        clearClickHold();
        if (!enabled) {
            currentValues = {
                scale: ICON_BUTTON_TUNING.scale.base,
                alpha: ICON_BUTTON_TUNING.alpha.base,
                ringScale: ICON_BUTTON_TUNING.ring.startScale,
                ringAlpha: 0,
            };
            setTextureState("base");
            cancelAnimations();
            return;
        }
        if (isSelected()) {
            if (withAnimation) {
                animateSelect();
            } else {
                cancelAnimations();
                currentValues = {
                    scale: ICON_BUTTON_TUNING.scale.selectSettle,
                    alpha: ICON_BUTTON_TUNING.alpha.select,
                    ringScale: ICON_BUTTON_TUNING.ring.startScale,
                    ringAlpha: 0,
                };
                setTextureState("select");
            }
            return;
        }
        if (isHovered()) {
            if (withAnimation) {
                animateHover();
            } else {
                cancelAnimations();
                currentValues = {
                    scale: ICON_BUTTON_TUNING.scale.hover,
                    alpha: ICON_BUTTON_TUNING.alpha.hover,
                    ringScale: ICON_BUTTON_TUNING.ring.startScale,
                    ringAlpha: 0,
                };
                setTextureState("hover");
            }
            return;
        }
        if (withAnimation) {
            animateDismiss();
        } else {
            cancelAnimations();
            currentValues = {
                scale: ICON_BUTTON_TUNING.scale.base,
                alpha: ICON_BUTTON_TUNING.alpha.base,
                ringScale: ICON_BUTTON_TUNING.ring.startScale,
                ringAlpha: 0,
            };
            setTextureState("base");
        }
    };

    const handlePointerTap = (): void => {
        if (!enabled) return;
        clearClickHold();
        if (args.isToggle && !args.getIsSelected) {
            internalSelected = !internalSelected;
            syncStateFromFlags(true);
        } else if (!isSelected()) {
            animateSelect();
            clickHoldTimeoutId = window.setTimeout(() => {
                clickHoldTimeoutId = null;
                syncStateFromFlags(true);
            }, ICON_BUTTON_TUNING.durationMs.clickHold);
        }
        args.onClick?.();
    };

    container.on("pointerover", () => {
        if (!enabled) return;
        if (hovered) return;
        hovered = true;
        uiAudio?.play("hover");
        if (!isSelected()) animateHover();
    });
    container.on("pointerout", () => {
        if (!hovered) return;
        hovered = false;
        clearClickHold();
        if (!enabled) return;
        if (!isSelected() && !externallyHovered) {
            animateDismiss();
        }
    });
    container.on("pointerdown", () => {
        if (!enabled) return;
        uiAudio?.play("select");
        animateSelect();
    });
    container.on("pointertap", handlePointerTap);

    syncStateFromFlags(false);

    return {
        container,
        setSelected: (selected: boolean) => {
            if (selected !== internalSelected) {
                uiAudio?.play(selected ? "select" : "dismiss");
            }
            internalSelected = selected;
            syncStateFromFlags(true);
        },
        setHovered: (nextHovered: boolean, options?: { playAudio?: boolean }) => {
            if (nextHovered === externallyHovered) return;
            externallyHovered = nextHovered;
            if (nextHovered && enabled && !isSelected() && options?.playAudio !== false) {
                uiAudio?.play("hover");
            }
            if (!isHovered()) {
                clearClickHold();
            }
            syncStateFromFlags(true);
        },
        setEnabled: (isEnabled: boolean) => {
            enabled = isEnabled;
            container.cursor = enabled ? "pointer" : "default";
            container.eventMode = enabled ? "static" : "none";
            syncStateFromFlags(false);
        },
        destroy: () => {
            clearClickHold();
            cancelAnimations();
            container.removeAllListeners();
            container.destroy({ children: true });
        },
    };
}

function redrawRing(ring: PIXI.Graphics, radius: number): void {
    ring.clear();
    ring.circle(0, 0, Math.max(2, radius));
    ring.stroke({ width: ICON_BUTTON_TUNING.ring.strokePx, color: ICON_BUTTON_TUNING.ring.color, alpha: 0.78 });
}

function fitScaleToBox(texture: PIXI.Texture, boxW: number, boxH: number): number {
    const texW = Math.max(1, texture.width);
    const texH = Math.max(1, texture.height);
    return Math.min(boxW / texW, boxH / texH);
}

function fitToSquare(texture: PIXI.Texture, sizePx: number): { width: number; height: number } {
    const texW = Math.max(1, texture.width);
    const texH = Math.max(1, texture.height);
    const scale = Math.min(sizePx / texW, sizePx / texH);
    return { width: texW * scale, height: texH * scale };
}

function lerp(a: number, b: number, t: number): number {
    return a + ((b - a) * t);
}

function easeOutCubic(t: number): number {
    const inv = 1 - t;
    return 1 - (inv * inv * inv);
}
