import * as PIXI from "pixi.js";
import type { UiAssets, UiIconVariants } from "./assets";
import type { UiAudio } from "./audio";
import { createIconButton, type IconButtonHandle, type IconButtonTextures } from "./components/IconButton";
import type { Rect } from "./layout";
import type { ConsoleSkin } from "./skin";

export type TopStripUiPhase = "planning" | "resolving" | "decision_gate" | "end_of_day" | "recap";
export type TopStripSignalMode = "crisp" | "normal" | "noisy";

export type TopStripLayout = {
    strip: Rect;
    clusters: {
        left: Rect;
        center: Rect;
        right: Rect;
    };
};

export type TopStripViewModel = {
    day: number | null | undefined;
    timeLabel: string | null | undefined;
    cash: number | null | undefined;
    workforceDumb: number | null | undefined;
    workforceSmart: number | null | undefined;
    phase: TopStripUiPhase;
    doctrineLabel: string;
    signalPercent?: number | null;
    signalMode?: TopStripSignalMode;
    turn?: {
        tick?: number | null;
        cash?: {
            delta?: number | null;
            gained?: number | null;
            spent?: number | null;
        };
        workers?: {
            dumbAdded?: number | null;
            smartAdded?: number | null;
            dumbLost?: number | null;
            smartLost?: number | null;
            casualtiesByRoom?: Array<{ roomName: string; casualties: number }>;
        };
    };
};

export const TOP_STRIP_TUNING = {
    icons: {
        cashPx: 110,
        workersDumbPx: 70,
        workersSmartPx: 80,
        signalPx: 50,
    },
    meter: {
        w: 196,
        h: 10,
        minW: 120,
    },
    runContext: {
        dayLabelY: -1,
        rowCenterYInCluster: 34,
        clusterInsetX: 18,
        iconToTextGap: 10,
        cashIconToTextGap: 5,
        blockGap: 50,
    },
    rightCluster: {
        signalRowCenterYInCluster: 48,
        signalIconToMeterGap: 10,
        targetCenterXRatioInStrip: 0.8,
    },
    phaseDot: {
        gapX: 8,
        baselineAdjustY: 1,
        radiusPx: 4.5,
        strokePx: 1,
    },
    pulseByPhase: {
        planning: { hz: 0.9 },
        resolving: { hz: 1.6 },
        decision_gate: { hz: 1.1 },
        end_of_day: { hz: 0.7 },
        recap: { hz: 0.7 },
    },
} as const;

type TextureCropRatio = {
    x: number;
    y: number;
    w: number;
    h: number;
};

const ICON_CROP_RATIOS = {
    cash: { x: 0.2, y: 0.33, w: 0.64, h: 0.32 },
    workersDumb: { x: 0.22, y: 0.19, w: 0.56, h: 0.52 },
    workersSmart: { x: 0.15, y: 0.16, w: 0.7, h: 0.58 },
    signal: { x: 0.24, y: 0.2, w: 0.52, h: 0.52 },
} as const satisfies Record<"cash" | "workersDumb" | "workersSmart" | "signal", TextureCropRatio>;

const PHASE_DOT_COLORS: Record<TopStripUiPhase, number> = {
    planning: 0xff3b30,
    resolving: 0xff7a1a,
    decision_gate: 0xffc247,
    end_of_day: 0x6dbbff,
    recap: 0xa6b0bd,
};
const INFO_HOVER_TONE = 0x4ce8ff;
const INFO_SELECT_TONE = 0xffa347;

type TopStripInfoKey = "cash" | "workers_dumb" | "workers_smart" | "signal";
type TopStripInfoTone = "normal" | "muted" | "positive" | "negative";
type TopStripInfoLine = { text: string; tone?: TopStripInfoTone };
type TopStripInfo = { title: string; hover: string; lines: TopStripInfoLine[] };

export class SimSimTopStrip {
    public readonly container = new PIXI.Container();

    private readonly maskedPlate = new PIXI.Container();
    private readonly plateSprite: PIXI.Sprite;
    private readonly readabilityOverlay = new PIXI.Graphics();
    private readonly borderFrame = new PIXI.Graphics();
    private readonly plateMask = new PIXI.Graphics();

    private readonly leftCluster = new PIXI.Container();
    private readonly centerCluster = new PIXI.Container();
    private readonly rightCluster = new PIXI.Container();

    private readonly dayShiftText: PIXI.Text;
    private readonly cashIcon: IconButtonHandle;
    private readonly cashValueText: PIXI.Text;
    private readonly workersDumbIcon: IconButtonHandle;
    private readonly workersDumbText: PIXI.Text;
    private readonly workersSmartIcon: IconButtonHandle;
    private readonly workersSmartText: PIXI.Text;

    private readonly phaseDot = new PIXI.Graphics();
    private readonly phaseText: PIXI.Text;
    private readonly phasePrefixText: PIXI.Text;

    private readonly doctrineText: PIXI.Text;
    private readonly signalIcon: IconButtonHandle;
    private readonly signalFill = new PIXI.Graphics();
    private readonly signalTrack = new PIXI.Graphics();
    private readonly signalPctText: PIXI.Text;
    private meterWidthPx: number = TOP_STRIP_TUNING.meter.w;

    private readonly exitButton = new PIXI.Container();
    private readonly exitButtonBg = new PIXI.Graphics();
    private readonly exitButtonText: PIXI.Text;

    private readonly hoverInfo = new PIXI.Container();
    private readonly hoverInfoBg = new PIXI.Graphics();
    private readonly hoverInfoText: PIXI.Text;
    private readonly detailInfo = new PIXI.Container();
    private readonly detailInfoBg = new PIXI.Graphics();
    private readonly detailInfoTitle: PIXI.Text;
    private readonly detailInfoLines = new PIXI.Container();
    private detailInfoKey: TopStripInfoKey | null = null;
    private detailAnchorX = 0;
    private readonly infoHoverCount: Record<TopStripInfoKey, number> = {
        cash: 0,
        workers_dumb: 0,
        workers_smart: 0,
        signal: 0,
    };

    private layout: TopStripLayout;
    private readonly skin: ConsoleSkin;
    private phase: TopStripUiPhase = "planning";
    private elapsedMs = 0;
    private readonly ticker: PIXI.Ticker;
    private readonly onExit?: () => void;
    private lastModel: TopStripViewModel = {
        day: null,
        timeLabel: null,
        cash: null,
        workforceDumb: null,
        workforceSmart: null,
        phase: "planning",
        doctrineLabel: "UNSET",
        signalPercent: 0,
        signalMode: "normal",
        turn: undefined,
    };
    private readonly onGlobalPointerDown = (): void => {
        this.dismissDetailInfo();
    };

    constructor(args: {
        layout: TopStripLayout;
        skin: ConsoleSkin;
        assets: UiAssets;
        audio?: UiAudio;
        ticker: PIXI.Ticker;
        onExit?: () => void;
    }) {
        this.layout = args.layout;
        this.skin = args.skin;
        this.ticker = args.ticker;
        this.onExit = args.onExit;

        this.plateSprite = new PIXI.Sprite(args.assets.chrome.topStripPlate ?? PIXI.Texture.WHITE);
        this.plateSprite.anchor.set(0.5, 0.5);
        this.maskedPlate.mask = this.plateMask;
        this.maskedPlate.addChild(this.plateSprite, this.readabilityOverlay);
        this.container.addChild(this.maskedPlate, this.plateMask, this.borderFrame);

        const labelStyle = new PIXI.TextStyle({
            fontFamily: "Bricolage Grotesque, sans-serif",
            fontSize: this.skin.typography.microLabelPx + 1,
            fill: this.skin.colors.textMuted,
            letterSpacing: 0.8,
            fontWeight: "700",
        });
        const valueStyle = new PIXI.TextStyle({
            fontFamily: "Bricolage Grotesque, sans-serif",
            fontSize: 26,
            fill: this.skin.colors.textPrimary,
            letterSpacing: 0.4,
            fontWeight: "800",
        });
        const smallValueStyle = new PIXI.TextStyle({
            fontFamily: "Bricolage Grotesque, sans-serif",
            fontSize: 26,
            fill: this.skin.colors.textPrimary,
            letterSpacing: 0.2,
            fontWeight: "700",
        });

        this.dayShiftText = new PIXI.Text({ text: "DAY - — --:--", style: labelStyle });
        this.cashIcon = createIconButton({
            textures: cropIconVariantTextures(args.assets.icons.cash, ICON_CROP_RATIOS.cash),
            sizePx: TOP_STRIP_TUNING.icons.cashPx,
            audio: args.audio,
        });
        this.cashValueText = new PIXI.Text({ text: "$--", style: valueStyle });
        this.workersDumbIcon = createIconButton({
            textures: cropIconVariantTextures(args.assets.icons.workersDumb, ICON_CROP_RATIOS.workersDumb),
            sizePx: TOP_STRIP_TUNING.icons.workersDumbPx,
            audio: args.audio,
        });
        this.workersDumbText = new PIXI.Text({ text: "--", style: smallValueStyle.clone() });
        this.workersSmartIcon = createIconButton({
            textures: cropIconVariantTextures(args.assets.icons.workersSmart, ICON_CROP_RATIOS.workersSmart),
            sizePx: TOP_STRIP_TUNING.icons.workersSmartPx,
            audio: args.audio,
        });
        this.workersSmartText = new PIXI.Text({ text: "--", style: smallValueStyle.clone() });

        this.leftCluster.addChild(
            this.dayShiftText,
            this.cashIcon.container,
            this.cashValueText,
            this.workersDumbIcon.container,
            this.workersDumbText,
            this.workersSmartIcon.container,
            this.workersSmartText
        );

        this.phaseDot.alpha = 1;
        this.phasePrefixText = new PIXI.Text({
            text: "PHASE",
            style: new PIXI.TextStyle({
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: this.skin.typography.microLabelPx,
                fill: this.skin.colors.textMuted,
                letterSpacing: 1.4,
                fontWeight: "700",
            }),
        });
        this.phaseText = new PIXI.Text({
            text: "PLANNING",
            style: new PIXI.TextStyle({
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 17,
                fill: this.skin.colors.textPrimary,
                letterSpacing: 0.8,
                fontWeight: "800",
            }),
        });
        this.centerCluster.addChild(this.phasePrefixText, this.phaseText, this.phaseDot);
        this.redrawPhaseDot();

        this.doctrineText = new PIXI.Text({
            text: "DOCTRINE: UNSET",
            style: new PIXI.TextStyle({
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 13,
                fill: this.skin.colors.textPrimary,
                letterSpacing: 0.4,
                fontWeight: "700",
            }),
        });
        this.signalIcon = createIconButton({
            textures: cropIconVariantTextures(args.assets.icons.signal, ICON_CROP_RATIOS.signal),
            sizePx: TOP_STRIP_TUNING.icons.signalPx,
            audio: args.audio,
        });
        this.signalPctText = new PIXI.Text({
            text: "0%",
            style: new PIXI.TextStyle({
                fontFamily: "Chivo Mono, monospace",
                fontSize: 13,
                fill: this.skin.colors.textMuted,
                letterSpacing: 0.5,
                fontWeight: "700",
            }),
        });
        this.rightCluster.addChild(this.doctrineText, this.signalIcon.container, this.signalTrack, this.signalFill, this.signalPctText);

        this.exitButtonText = new PIXI.Text({
            text: "EXIT",
            style: new PIXI.TextStyle({
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 11,
                fill: this.skin.colors.textPrimary,
                letterSpacing: 1,
                fontWeight: "800",
            }),
        });
        this.exitButton.eventMode = "static";
        this.exitButton.cursor = "pointer";
        this.exitButton.on("pointertap", () => this.onExit?.());
        this.exitButton.on("pointerover", () => {
            this.exitButtonBg.alpha = 1;
        });
        this.exitButton.on("pointerout", () => {
            this.exitButtonBg.alpha = 0.92;
        });
        this.exitButton.addChild(this.exitButtonBg, this.exitButtonText);
        this.rightCluster.addChild(this.exitButton);

        this.hoverInfoText = new PIXI.Text({
            text: "",
            style: new PIXI.TextStyle({
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 11,
                fill: this.skin.colors.textPrimary,
                letterSpacing: 0.2,
                fontWeight: "600",
                wordWrap: true,
                wordWrapWidth: 230,
            }),
        });
        this.hoverInfo.visible = false;
        this.hoverInfo.addChild(this.hoverInfoBg, this.hoverInfoText);

        this.detailInfoTitle = new PIXI.Text({
            text: "",
            style: new PIXI.TextStyle({
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 12,
                fill: this.skin.colors.textPrimary,
                letterSpacing: 0.5,
                fontWeight: "800",
            }),
        });
        this.detailInfo.visible = false;
        this.detailInfo.eventMode = "static";
        this.detailInfo.cursor = "pointer";
        this.detailInfo.on("pointertap", () => {
            this.dismissDetailInfo();
        });
        this.detailInfo.addChild(this.detailInfoBg, this.detailInfoTitle, this.detailInfoLines);

        this.enableInfoInteractions({
            key: "cash",
            icon: this.cashIcon,
            anchorIcon: this.cashIcon.container,
            targets: [this.cashIcon.container, this.cashValueText],
        });
        this.enableInfoInteractions({
            key: "workers_dumb",
            icon: this.workersDumbIcon,
            anchorIcon: this.workersDumbIcon.container,
            targets: [this.workersDumbIcon.container, this.workersDumbText],
        });
        this.enableInfoInteractions({
            key: "workers_smart",
            icon: this.workersSmartIcon,
            anchorIcon: this.workersSmartIcon.container,
            targets: [this.workersSmartIcon.container, this.workersSmartText],
        });
        this.enableInfoInteractions({
            key: "signal",
            icon: this.signalIcon,
            anchorIcon: this.signalIcon.container,
            targets: [this.signalIcon.container, this.signalPctText],
        });
        this.updateInfoValueTone();

        this.container.addChild(this.leftCluster, this.centerCluster, this.rightCluster, this.detailInfo, this.hoverInfo);
        window.addEventListener("pointerdown", this.onGlobalPointerDown);
        this.setLayout(args.layout);
        this.update({
            day: null,
            timeLabel: null,
            cash: null,
            workforceDumb: null,
            workforceSmart: null,
            phase: "planning",
            doctrineLabel: "UNSET",
            signalPercent: 0,
        });
        this.ticker.add(this.onTick);
    }

    setLayout(layout: TopStripLayout): void {
        this.layout = layout;
        const strip = layout.strip;
        this.container.position.set(strip.x, strip.y);
        this.redrawChrome();
        this.layoutClusters();
    }

    update(model: TopStripViewModel): void {
        this.lastModel = {
            day: model.day,
            timeLabel: model.timeLabel,
            cash: model.cash,
            workforceDumb: model.workforceDumb,
            workforceSmart: model.workforceSmart,
            phase: model.phase,
            doctrineLabel: model.doctrineLabel,
            signalPercent: model.signalPercent,
            signalMode: model.signalMode,
            turn: model.turn,
        };
        this.phase = model.phase;
        const day = Number.isFinite(model.day) ? Math.max(0, Math.floor(model.day as number)) : null;
        const timeLabel = model.timeLabel?.trim() ? model.timeLabel.trim() : "--:--";
        this.dayShiftText.text = `DAY ${day ?? "-"} — ${timeLabel}`;

        this.cashValueText.text = formatCash(model.cash);
        this.workersDumbText.text = formatCount(model.workforceDumb);
        this.workersSmartText.text = formatCount(model.workforceSmart);

        this.phaseText.text = phaseLabel(model.phase);
        this.redrawPhaseDot();

        this.doctrineText.text = `DOCTRINE: ${model.doctrineLabel || "UNSET"}`;
        this.doctrineText.style.wordWrap = true;
        this.doctrineText.style.wordWrapWidth = 380;

        const signalPct = deriveSignalPercent(model.signalPercent, model.signalMode);
        this.signalPctText.text = `${signalPct}%`;
        this.layoutClusters();
        this.redrawSignalFill(signalPct);
        if (this.detailInfo.visible && this.detailInfoKey) {
            this.showDetailInfo(this.detailInfoKey);
        }
    }

    destroy(): void {
        this.ticker.remove(this.onTick);
        window.removeEventListener("pointerdown", this.onGlobalPointerDown);
        this.cashIcon.destroy();
        this.workersDumbIcon.destroy();
        this.workersSmartIcon.destroy();
        this.signalIcon.destroy();
        this.container.destroy({ children: true });
    }

    private readonly onTick = (ticker: PIXI.Ticker): void => {
        this.elapsedMs += ticker.deltaMS;
        const pulse = TOP_STRIP_TUNING.pulseByPhase[this.phase];
        const t = (this.elapsedMs / 1000) * pulse.hz * Math.PI * 2;
        const wave = (Math.sin(t) + 1) * 0.5;
        this.phaseDot.alpha = wave;
    };

    private redrawChrome(): void {
        const strip = this.layout.strip;
        fitSpriteCover(this.plateSprite, strip.w, strip.h);

        this.plateMask.clear();
        this.plateMask.roundRect(0, 0, strip.w, strip.h, this.skin.radii.bezelPx);
        this.plateMask.fill({ color: 0xffffff, alpha: 1 });

        this.readabilityOverlay.clear();
        this.readabilityOverlay.roundRect(0, 0, strip.w, strip.h, this.skin.radii.bezelPx);
        this.readabilityOverlay.fill({ color: 0x070b10, alpha: 0.34 });

        this.borderFrame.clear();
        this.borderFrame.roundRect(0, 0, strip.w, strip.h, this.skin.radii.bezelPx);
        this.borderFrame.fill({ color: 0x0e141b, alpha: 0.2 });
        this.borderFrame.stroke({
            width: this.skin.stroke.bezelPx,
            color: 0x84b9ca,
            alpha: 0.46,
        });
    }

    private layoutClusters(): void {
        const strip = this.layout.strip;
        const left = toLocalRect(this.layout.clusters.left, strip);
        const center = toLocalRect(this.layout.clusters.center, strip);
        const right = toLocalRect(this.layout.clusters.right, strip);

        this.leftCluster.position.set(left.x + TOP_STRIP_TUNING.runContext.clusterInsetX, left.y);
        this.centerCluster.position.set(center.x, center.y);
        this.rightCluster.position.set(right.x, right.y);

        this.dayShiftText.position.set(0, TOP_STRIP_TUNING.runContext.dayLabelY);
        this.layoutRunContextRows();
        this.dayShiftText.x = this.cashIcon.container.x;

        this.layoutPhaseRow();

        const leftContentRight = Math.max(
            this.dayShiftText.x + this.dayShiftText.width,
            this.workersSmartText.x + this.workersSmartText.width
        );
        const phaseCenterX = center.x + this.phaseText.x + (this.phaseText.width * 0.5);
        const desiredLeftCenterX = phaseCenterX * 0.5;
        const clampedLeftX = clampInt(
            desiredLeftCenterX - (leftContentRight * 0.5),
            left.x + TOP_STRIP_TUNING.runContext.clusterInsetX,
            Math.max(left.x + TOP_STRIP_TUNING.runContext.clusterInsetX, phaseCenterX - leftContentRight - 32)
        );
        this.leftCluster.x = clampedLeftX;

        const buttonW = 92;
        const buttonH = 34;
        const rightWidth = Math.max(200, right.w);
        this.exitButton.position.set(rightWidth - buttonW, 16);
        this.exitButtonBg.clear();
        this.exitButtonBg.roundRect(0, 0, buttonW, buttonH, 8);
        this.exitButtonBg.fill({ color: 0x2d2416, alpha: 0.92 });
        this.exitButtonBg.stroke({ width: 1.2, color: 0xc39a52, alpha: 0.82 });
        this.exitButtonText.position.set((buttonW - this.exitButtonText.width) * 0.5, (buttonH - this.exitButtonText.height) * 0.5);

        const signalGap = TOP_STRIP_TUNING.rightCluster.signalIconToMeterGap;
        const maxContentRight = this.exitButton.x - 20;
        const meterMaxW = maxContentRight - (this.signalIcon.container.width + signalGap + 12 + this.signalPctText.width);
        const boundedMeterMaxW = Math.max(1, meterMaxW);
        this.meterWidthPx =
            boundedMeterMaxW < TOP_STRIP_TUNING.meter.minW
                ? boundedMeterMaxW
                : Math.min(TOP_STRIP_TUNING.meter.w, boundedMeterMaxW);

        const signalRowW = this.signalIcon.container.width + signalGap + this.meterWidthPx + 12 + this.signalPctText.width;
        const doctrineW = this.doctrineText.width;
        const contentW = Math.max(signalRowW, doctrineW);
        const targetCenterLocal = (strip.w * TOP_STRIP_TUNING.rightCluster.targetCenterXRatioInStrip) - this.rightCluster.x;
        const contentX = clampInt(targetCenterLocal - (contentW * 0.5), 0, Math.max(0, maxContentRight - contentW));

        const signalRowH = Math.max(this.signalIcon.container.height, this.signalPctText.height, TOP_STRIP_TUNING.meter.h);
        const groupGapY = 6;
        const groupH = this.doctrineText.height + groupGapY + signalRowH;
        const centerYLocal = (strip.h * 0.5) - this.rightCluster.y;
        const groupTopY = centerYLocal - (groupH * 0.5);
        this.doctrineText.position.set(contentX + ((contentW - doctrineW) * 0.5), groupTopY);

        const signalRowX = contentX + ((contentW - signalRowW) * 0.5);
        const signalRowCenterY = groupTopY + this.doctrineText.height + groupGapY + (signalRowH * 0.5);
        this.signalIcon.container.position.set(signalRowX, signalRowCenterY - (this.signalIcon.container.height * 0.5));
        const signalTrackX = signalRowX + this.signalIcon.container.width + signalGap;
        const signalTrackY = signalRowCenterY - (TOP_STRIP_TUNING.meter.h * 0.5);
        this.signalTrack.position.set(signalTrackX, signalTrackY);
        this.signalFill.position.set(signalTrackX, signalTrackY);
        this.signalPctText.position.set(signalTrackX + this.meterWidthPx + 12, signalRowCenterY - (this.signalPctText.height * 0.5));

        this.signalTrack.clear();
        this.signalTrack.roundRect(0, 0, this.meterWidthPx, TOP_STRIP_TUNING.meter.h, TOP_STRIP_TUNING.meter.h * 0.5);
        this.signalTrack.fill({ color: 0x0b1218, alpha: 0.92 });
        this.signalTrack.stroke({ width: 1, color: 0x6e8a98, alpha: 0.52 });

        this.positionDetailPanel();
    }

    private layoutPhaseRow(): void {
        const strip = this.layout.strip;
        const centerLocalX = (strip.w * 0.5) - this.centerCluster.x;
        const centerLocalY = (strip.h * 0.5) - this.centerCluster.y;

        const phaseGapX = 16;
        const dotDiameter = TOP_STRIP_TUNING.phaseDot.radiusPx * 2;
        const rowW = this.phasePrefixText.width + phaseGapX + this.phaseText.width + TOP_STRIP_TUNING.phaseDot.gapX + dotDiameter;
        const rowX = centerLocalX - (rowW * 0.5);

        this.phasePrefixText.position.set(rowX, centerLocalY - (this.phasePrefixText.height * 0.5));
        this.phaseText.position.set(
            this.phasePrefixText.x + this.phasePrefixText.width + phaseGapX,
            centerLocalY - (this.phaseText.height * 0.5)
        );
        this.phaseDot.x = this.phaseText.x + this.phaseText.width + TOP_STRIP_TUNING.phaseDot.gapX + TOP_STRIP_TUNING.phaseDot.radiusPx;
        this.phaseDot.y = centerLocalY + TOP_STRIP_TUNING.phaseDot.baselineAdjustY;
    }

    private layoutRunContextRows(): void {
        const rowCenterY = TOP_STRIP_TUNING.runContext.rowCenterYInCluster;
        const iconToTextGap = TOP_STRIP_TUNING.runContext.iconToTextGap;
        const cashGap = TOP_STRIP_TUNING.runContext.cashIconToTextGap;
        const blockGap = TOP_STRIP_TUNING.runContext.blockGap;

        this.cashIcon.container.position.set(0, rowCenterY - (this.cashIcon.container.height * 0.5));
        this.cashValueText.position.set(
            this.cashIcon.container.x + this.cashIcon.container.width + cashGap,
            rowCenterY - (this.cashValueText.height * 0.5)
        );

        const dumbIconX = this.cashValueText.x + this.cashValueText.width + blockGap;
        this.workersDumbIcon.container.position.set(dumbIconX, rowCenterY - (this.workersDumbIcon.container.height * 0.5));
        this.workersDumbText.position.set(
            this.workersDumbIcon.container.x + this.workersDumbIcon.container.width + iconToTextGap,
            rowCenterY - (this.workersDumbText.height * 0.5)
        );

        const smartIconX = this.workersDumbText.x + this.workersDumbText.width + blockGap;
        this.workersSmartIcon.container.position.set(smartIconX, rowCenterY - (this.workersSmartIcon.container.height * 0.5));
        this.workersSmartText.position.set(
            this.workersSmartIcon.container.x + this.workersSmartIcon.container.width + iconToTextGap,
            rowCenterY - (this.workersSmartText.height * 0.5)
        );
    }

    private redrawPhaseDot(): void {
        const color = PHASE_DOT_COLORS[this.phase] ?? PHASE_DOT_COLORS.planning;
        this.phaseDot.clear();
        this.phaseDot.circle(0, 0, TOP_STRIP_TUNING.phaseDot.radiusPx);
        this.phaseDot.fill({ color, alpha: 1 });
        this.phaseDot.stroke({ width: TOP_STRIP_TUNING.phaseDot.strokePx, color: 0x140a09, alpha: 0.85 });
    }

    private redrawSignalFill(signalPct: number): void {
        const fillW = Math.max(0, Math.min(this.meterWidthPx, Math.round((this.meterWidthPx * signalPct) / 100)));
        const color = signalPct >= 85 ? 0x79ccb6 : signalPct >= 65 ? 0x7ec7dc : signalPct >= 50 ? 0xd99a49 : 0xaf4b46;
        this.signalFill.clear();
        if (fillW <= 0) return;
        this.signalFill.roundRect(0, 0, fillW, TOP_STRIP_TUNING.meter.h, TOP_STRIP_TUNING.meter.h * 0.5);
        this.signalFill.fill({ color, alpha: 0.9 });
    }

    private enableInfoInteractions(args: {
        key: TopStripInfoKey;
        icon: IconButtonHandle;
        anchorIcon: PIXI.Container;
        targets: Array<PIXI.Container | PIXI.Text>;
    }): void {
        const { key, icon, anchorIcon, targets } = args;
        for (const target of targets) {
            const isAnchorIcon = target === anchorIcon;
            target.eventMode = "static";
            target.cursor = "pointer";
            target.on("pointerenter", () => {
                this.infoHoverCount[key] += 1;
                this.showHoverInfo(anchorIcon, key);
                if (!isAnchorIcon) {
                    icon.setHovered(true, { playAudio: true });
                }
                this.updateInfoValueTone();
            });
            target.on("pointerleave", () => {
                this.infoHoverCount[key] = Math.max(0, this.infoHoverCount[key] - 1);
                if (!isAnchorIcon) {
                    icon.setHovered(false, { playAudio: false });
                }
                if (this.infoHoverCount[key] <= 0) {
                    this.hoverInfo.visible = false;
                }
                this.updateInfoValueTone();
            });
            target.on("pointertap", () => {
                this.hoverInfo.visible = false;
                if (this.detailInfo.visible && this.detailInfoKey === key) {
                    this.dismissDetailInfo();
                    return;
                }
                this.showDetailInfo(key, anchorIcon);
            });
        }
    }

    private showHoverInfo(icon: PIXI.Container, key: TopStripInfoKey): void {
        const info = this.getInfo(key);
        this.hoverInfoText.text = info.hover;
        const padX = 8;
        const padY = 6;
        const panelW = this.hoverInfoText.width + (padX * 2);
        const panelH = this.hoverInfoText.height + (padY * 2);

        this.hoverInfoBg.clear();
        this.hoverInfoBg.roundRect(0, 0, panelW, panelH, 7);
        this.hoverInfoBg.fill({ color: 0x070c13, alpha: 0.96 });
        this.hoverInfoBg.stroke({ width: 1, color: 0x84b9ca, alpha: 0.48 });
        this.hoverInfoText.position.set(padX, padY);

        const global = icon.getGlobalPosition(new PIXI.Point());
        const local = this.container.toLocal(global);
        const stripW = this.layout.strip.w;
        const iconCenterX = local.x + (icon.width * 0.5);
        const x = clampInt(iconCenterX - (panelW * 0.5), 0, stripW - panelW);
        const clampedY = Math.max(0, Math.round(local.y + icon.height + 8));
        this.hoverInfo.position.set(x, clampedY);
        this.hoverInfo.visible = true;
    }

    private showDetailInfo(key: TopStripInfoKey, icon?: PIXI.Container): void {
        this.setActiveInfoKey(key);
        if (icon) {
            const global = icon.getGlobalPosition(new PIXI.Point());
            const local = this.container.toLocal(global);
            this.detailAnchorX = local.x + (icon.width * 0.5);
        }
        const info = this.getInfo(key);
        this.detailInfoTitle.text = info.title;

        const width = 380;
        const padX = 12;
        const padY = 10;
        this.detailInfoTitle.position.set(padX, padY);
        const lines: TopStripInfoLine[] = [...info.lines, { text: "" }, { text: "Click anywhere to close.", tone: "muted" }];
        const linesHeight = this.renderDetailLines(lines, width - (padX * 2), padX, padY + 20);

        const height = Math.max(80, (padY + 20) + linesHeight + padY);
        this.detailInfoBg.clear();
        this.detailInfoBg.roundRect(0, 0, width, height, 10);
        this.detailInfoBg.fill({ color: 0x070c13, alpha: 0.97 });
        this.detailInfoBg.stroke({ width: 1.2, color: 0x84b9ca, alpha: 0.5 });

        this.detailInfo.visible = true;
        this.positionDetailPanel();
    }

    private renderDetailLines(lines: TopStripInfoLine[], wrapWidth: number, x: number, y: number): number {
        this.detailInfoLines.removeChildren();
        let offsetY = 0;
        for (const line of lines) {
            const tone = line.tone ?? "normal";
            const text = new PIXI.Text({
                text: line.text,
                style: new PIXI.TextStyle({
                    fontFamily: "Bricolage Grotesque, sans-serif",
                    fontSize: 11,
                    fill: detailToneColor(tone),
                    letterSpacing: 0.2,
                    fontWeight: tone === "normal" ? "600" : "500",
                    wordWrap: true,
                    wordWrapWidth: wrapWidth,
                    lineHeight: 16,
                }),
            });
            text.position.set(x, y + offsetY);
            this.detailInfoLines.addChild(text);
            offsetY += line.text.length === 0 ? 8 : Math.max(14, text.height + 2);
        }
        return offsetY;
    }

    private positionDetailPanel(): void {
        const stripW = this.layout.strip.w;
        const panelW = this.detailInfoBg.width;
        if (panelW <= 0) return;
        const panelX = clampInt(this.detailAnchorX - (panelW * 0.5), 0, stripW - panelW);
        this.detailInfo.position.set(panelX, this.layout.strip.h + 8);
    }

    private setActiveInfoKey(key: TopStripInfoKey | null): void {
        this.detailInfoKey = key;
        this.cashIcon.setSelected(key === "cash");
        this.workersDumbIcon.setSelected(key === "workers_dumb");
        this.workersSmartIcon.setSelected(key === "workers_smart");
        this.signalIcon.setSelected(key === "signal");
        this.updateInfoValueTone();
    }

    private dismissDetailInfo(): void {
        if (!this.detailInfo.visible && this.detailInfoKey === null) return;
        this.detailInfo.visible = false;
        this.setActiveInfoKey(null);
    }

    private updateInfoValueTone(): void {
        this.applyInfoValueTone(this.cashValueText, "cash");
        this.applyInfoValueTone(this.workersDumbText, "workers_dumb");
        this.applyInfoValueTone(this.workersSmartText, "workers_smart");
        this.applyInfoValueTone(this.signalPctText, "signal");
    }

    private applyInfoValueTone(text: PIXI.Text, key: TopStripInfoKey): void {
        const isSelected = this.detailInfoKey === key;
        const isHovered = this.infoHoverCount[key] > 0;
        const nextColor = isSelected ? INFO_SELECT_TONE : isHovered ? INFO_HOVER_TONE : this.skin.colors.textPrimary;
        text.style.fill = nextColor;
    }

    private getInfo(key: TopStripInfoKey): TopStripInfo {
        const signalPct = deriveSignalPercent(this.lastModel.signalPercent, this.lastModel.signalMode);
        const cashTurn = this.lastModel.turn?.cash;
        const workerTurn = this.lastModel.turn?.workers;
        if (key === "cash") {
            const gained = asNonNegativeInt(cashTurn?.gained);
            const spent = asNonNegativeInt(cashTurn?.spent);
            const delta = Number.isFinite(cashTurn?.delta)
                ? Math.round(cashTurn?.delta as number)
                : (gained - spent);
            return {
                title: "Cash",
                hover: "Liquid funds available for decisions.",
                lines: [
                    { text: `Total: ${formatCash(this.lastModel.cash)}` },
                    { text: `Gained last turn: +$${gained.toLocaleString("en-US")}`, tone: gained > 0 ? "positive" : "muted" },
                    { text: `Spent last turn: -$${spent.toLocaleString("en-US")}`, tone: spent > 0 ? "negative" : "muted" },
                    {
                        text: `Net change: ${formatSignedDollar(delta)}`,
                        tone: delta > 0 ? "positive" : delta < 0 ? "negative" : "muted",
                    },
                ],
            };
        }
        if (key === "workers_dumb") {
            const added = asNonNegativeInt(workerTurn?.dumbAdded);
            const lost = asNonNegativeInt(workerTurn?.dumbLost);
            const casualtiesByRoom = workerTurn?.casualtiesByRoom ?? [];
            const roomLines = casualtiesByRoom.length > 0
                ? casualtiesByRoom.slice(0, 4).map<TopStripInfoLine>((entry) => ({
                      text: `- ${entry.casualties} ${entry.roomName}`,
                      tone: "negative",
                  }))
                : [{ text: "No room casualties reported last turn.", tone: "muted" } satisfies TopStripInfoLine];
            return {
                title: "Dumb Workforce",
                hover: "Base operators for routine output.",
                lines: [
                    { text: `Total: ${formatCount(this.lastModel.workforceDumb)}` },
                    { text: `Added last turn: +${added}`, tone: added > 0 ? "positive" : "muted" },
                    { text: `Casualties last turn: -${lost}`, tone: lost > 0 ? "negative" : "muted" },
                    { text: "Casualties by room:", tone: "muted" },
                    ...roomLines,
                ],
            };
        }
        if (key === "workers_smart") {
            const added = asNonNegativeInt(workerTurn?.smartAdded);
            const lost = asNonNegativeInt(workerTurn?.smartLost);
            return {
                title: "Smart Workforce",
                hover: "Specialized operators for high-precision work.",
                lines: [
                    { text: `Total: ${formatCount(this.lastModel.workforceSmart)}` },
                    { text: `Added last turn: +${added}`, tone: added > 0 ? "positive" : "muted" },
                    { text: `Casualties last turn: -${lost}`, tone: lost > 0 ? "negative" : "muted" },
                ],
            };
        }
        const mode = (this.lastModel.signalMode ?? "normal").toUpperCase();
        return {
            title: "Signal Clarity",
            hover: "Directive clarity and transmission quality.",
            lines: [{ text: `Current signal: ${signalPct}%` }, { text: `Mode: ${mode}`, tone: "muted" }],
        };
    }
}

function detailToneColor(tone: TopStripInfoTone): number {
    if (tone === "positive") return 0x76d6a1;
    if (tone === "negative") return 0xe77b4b;
    if (tone === "muted") return 0xa6b8c5;
    return 0xf3efe3;
}

function cropIconVariantTextures(variants: UiIconVariants | undefined, crop: TextureCropRatio): IconButtonTextures {
    const base = cropTextureByRatio(variants?.base, crop) ?? PIXI.Texture.WHITE;
    const hover = cropTextureByRatio(variants?.hover, crop) ?? base;
    const select = cropTextureByRatio(variants?.select, crop) ?? base;
    return { base, hover, select };
}

function cropTextureByRatio(texture: PIXI.Texture | undefined, crop: TextureCropRatio): PIXI.Texture | undefined {
    if (!texture || texture === PIXI.Texture.WHITE) return texture;
    const texW = Math.max(1, texture.width);
    const texH = Math.max(1, texture.height);
    const x = clampInt(texW * crop.x, 0, texW - 1);
    const y = clampInt(texH * crop.y, 0, texH - 1);
    const w = clampInt(texW * crop.w, 1, texW - x);
    const h = clampInt(texH * crop.h, 1, texH - y);
    return new PIXI.Texture({
        source: texture.source,
        frame: new PIXI.Rectangle(x, y, w, h),
    });
}

function fitSpriteCover(sprite: PIXI.Sprite, width: number, height: number): void {
    const texW = Math.max(1, sprite.texture.width);
    const texH = Math.max(1, sprite.texture.height);
    const scale = Math.max(width / texW, height / texH);
    sprite.scale.set(scale, scale);
    sprite.position.set(width * 0.5, height * 0.5);
}

function phaseLabel(phase: TopStripUiPhase): string {
    if (phase === "decision_gate") return "DECISION GATE";
    if (phase === "end_of_day") return "END OF DAY";
    if (phase === "planning") return "PLANNING";
    if (phase === "resolving") return "RESOLVING";
    return "RECAP";
}

function formatCash(value: number | null | undefined): string {
    if (!Number.isFinite(value)) return "$--";
    const amount = Math.max(0, Math.floor(value as number));
    return `$${amount.toLocaleString("en-US")}`;
}

function formatCount(value: number | null | undefined): string {
    if (!Number.isFinite(value)) return "--";
    return String(Math.max(0, Math.floor(value as number)));
}

function asNonNegativeInt(value: number | null | undefined): number {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.floor(value as number));
}

function formatSignedDollar(value: number): string {
    const abs = Math.abs(Math.round(value));
    const sign = value >= 0 ? "+" : "-";
    return `${sign}$${abs.toLocaleString("en-US")}`;
}

function deriveSignalPercent(raw: number | null | undefined, mode: TopStripSignalMode | undefined): number {
    if (Number.isFinite(raw)) return clampInt(raw as number, 0, 100);
    if (mode === "crisp") return 90;
    if (mode === "noisy") return 50;
    return 72;
}

function toLocalRect(rect: Rect, parent: Rect): Rect {
    return {
        x: rect.x - parent.x,
        y: rect.y - parent.y,
        w: rect.w,
        h: rect.h,
    };
}

function clampInt(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, Math.round(value)));
}
