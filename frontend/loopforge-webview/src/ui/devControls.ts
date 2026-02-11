// src/ui/devControls.ts
import type { WorldStore } from "../state/worldStore";
import type { ViewerStore } from "../state/viewerStore";

type FloorFilter = "all" | 0 | 1;
type CameraMode = "free" | "auto";

type DevControlsOpts = {
  store?: WorldStore;
  viewerStore?: ViewerStore;
  onFloorChange: (floor: FloorFilter) => void;
  onRestart: () => void;
  onCameraModeChange?: (mode: CameraMode) => void;
  onRotate?: (deltaQuarterTurns: number) => void;
  onPlaybackToggle?: (paused: boolean) => void;
  onSpeedChange?: (speed: number) => void;
  onSeek?: (tick: number) => void;
};

export function mountDevControls(opts: DevControlsOpts): HTMLElement {
  const root = document.createElement("div");
  root.style.position = "absolute";
  root.style.left = "16px";
  root.style.bottom = "16px";
  root.style.zIndex = "20";
  root.style.pointerEvents = "auto";
  root.style.fontFamily = "Bricolage Grotesque, sans-serif";
  root.style.color = "#1f242b";

  const panel = document.createElement("div");
  panel.style.padding = "12px";
  panel.style.borderRadius = "12px";
  panel.style.background = "rgba(247, 242, 233, 0.9)";
  panel.style.border = "2px solid rgba(31, 36, 43, 0.65)";
  panel.style.boxShadow = "0 12px 30px rgba(24, 33, 40, 0.18)";
  panel.style.display = "flex";
  panel.style.flexDirection = "column";
  panel.style.gap = "10px";
  panel.style.minWidth = "240px";

  const title = document.createElement("div");
  title.textContent = "Dev Controls";
  title.style.fontWeight = "700";
  title.style.fontSize = "13px";
  panel.appendChild(title);

  const floorRow = document.createElement("div");
  floorRow.style.display = "flex";
  floorRow.style.gap = "6px";
  floorRow.style.alignItems = "center";

  const floorLabel = document.createElement("div");
  floorLabel.textContent = "Floor";
  floorLabel.style.fontSize = "12px";
  floorLabel.style.minWidth = "48px";
  floorRow.appendChild(floorLabel);

  const btnAll = makeMiniButton("All");
  const btn0 = makeMiniButton("F0");
  const btn1 = makeMiniButton("F1");

  let active: FloorFilter = 0;
  const setActive = (value: FloorFilter) => {
    active = value;
    [btnAll, btn0, btn1].forEach((b) => (b.dataset.active = "false"));
    if (value === "all") btnAll.dataset.active = "true";
    if (value === 0) btn0.dataset.active = "true";
    if (value === 1) btn1.dataset.active = "true";
    opts.onFloorChange(value);
  };

  btnAll.addEventListener("click", () => setActive("all"));
  btn0.addEventListener("click", () => setActive(0));
  btn1.addEventListener("click", () => setActive(1));
  setActive(active);

  floorRow.appendChild(btnAll);
  floorRow.appendChild(btn0);
  floorRow.appendChild(btn1);
  panel.appendChild(floorRow);

  const cameraRow = document.createElement("div");
  cameraRow.style.display = "flex";
  cameraRow.style.gap = "6px";
  cameraRow.style.alignItems = "center";

  const cameraLabel = document.createElement("div");
  cameraLabel.textContent = "Camera";
  cameraLabel.style.fontSize = "12px";
  cameraLabel.style.minWidth = "48px";
  cameraRow.appendChild(cameraLabel);

  const camFree = makeMiniButton("Free");
  const camAuto = makeMiniButton("Auto");
  let camMode: CameraMode = "free";
  const setCamMode = (mode: CameraMode) => {
    camMode = mode;
    [camFree, camAuto].forEach((b) => (b.dataset.active = "false"));
    if (mode === "free") camFree.dataset.active = "true";
    if (mode === "auto") camAuto.dataset.active = "true";
    opts.onCameraModeChange?.(mode);
  };
  camFree.addEventListener("click", () => setCamMode("free"));
  camAuto.addEventListener("click", () => setCamMode("auto"));
  setCamMode(camMode);

  cameraRow.appendChild(camFree);
  cameraRow.appendChild(camAuto);
  panel.appendChild(cameraRow);

  const rotateRow = document.createElement("div");
  rotateRow.style.display = "flex";
  rotateRow.style.gap = "6px";
  rotateRow.style.alignItems = "center";

  const rotateLabel = document.createElement("div");
  rotateLabel.textContent = "View";
  rotateLabel.style.fontSize = "12px";
  rotateLabel.style.minWidth = "48px";
  rotateRow.appendChild(rotateLabel);

  const rotateLeft = makeMiniButton("Rotate -90");
  const rotateRight = makeMiniButton("Rotate +90");
  rotateLeft.addEventListener("click", () => opts.onRotate?.(-1));
  rotateRight.addEventListener("click", () => opts.onRotate?.(1));
  rotateRow.appendChild(rotateLeft);
  rotateRow.appendChild(rotateRight);
  panel.appendChild(rotateRow);

  const cameraHint = document.createElement("div");
  cameraHint.textContent = "Tip: click an agent to follow";
  cameraHint.style.fontSize = "11px";
  cameraHint.style.opacity = "0.7";
  panel.appendChild(cameraHint);

  const playbackRow = document.createElement("div");
  playbackRow.style.display = "flex";
  playbackRow.style.gap = "8px";
  playbackRow.style.alignItems = "center";

  const playPause = makeMiniButton("Pause");
  let playing = true;
  playPause.addEventListener("click", () => {
    playing = !playing;
    playPause.textContent = playing ? "Pause" : "Play";
    opts.onPlaybackToggle?.(!playing);
  });
  playbackRow.appendChild(playPause);

  const restart = makeMiniButton("Restart Playback");
  restart.style.flex = "1";
  restart.addEventListener("click", () => opts.onRestart());
  playbackRow.appendChild(restart);

  panel.appendChild(playbackRow);

  const timelineRow = document.createElement("div");
  timelineRow.style.display = "flex";
  timelineRow.style.flexDirection = "column";
  timelineRow.style.gap = "6px";

  const tickLabel = document.createElement("div");
  tickLabel.textContent = "Tick 0";
  tickLabel.style.fontSize = "11px";
  tickLabel.style.opacity = "0.85";

  const slider = document.createElement("input");
  slider.type = "range";
  slider.min = "0";
  slider.max = "0";
  slider.step = "1";
  slider.value = "0";
  slider.style.width = "100%";
  slider.style.cursor = "pointer";
  const datalistId = `keyframes-${Math.floor(Math.random() * 1e6)}`;
  slider.setAttribute("list", datalistId);

  const datalist = document.createElement("datalist");
  datalist.id = datalistId;

  let dragging = false;
  slider.addEventListener("pointerdown", () => {
    dragging = true;
  });
  slider.addEventListener("pointerup", () => {
    dragging = false;
    opts.onSeek?.(Number(slider.value));
  });
  slider.addEventListener("change", () => {
    if (!dragging) opts.onSeek?.(Number(slider.value));
  });
  slider.addEventListener("input", () => {
    const tick = Number(slider.value);
    tickLabel.textContent = `Tick ${tick}`;
  });

  timelineRow.appendChild(tickLabel);
  timelineRow.appendChild(slider);
  timelineRow.appendChild(datalist);
  panel.appendChild(timelineRow);

  const highlightRow = document.createElement("div");
  highlightRow.style.display = "flex";
  highlightRow.style.gap = "6px";
  highlightRow.style.alignItems = "center";

  const highlightLabel = document.createElement("div");
  highlightLabel.textContent = "Highlights";
  highlightLabel.style.fontSize = "12px";
  highlightLabel.style.minWidth = "72px";
  highlightRow.appendChild(highlightLabel);

  const highlightSelect = document.createElement("select");
  highlightSelect.style.flex = "1";
  highlightSelect.style.padding = "4px 6px";
  highlightSelect.style.borderRadius = "8px";
  highlightSelect.style.border = "2px solid rgba(31, 36, 43, 0.35)";
  highlightSelect.style.background = "rgba(247, 242, 233, 0.9)";
  highlightSelect.style.fontSize = "11px";

  const highlightButton = makeMiniButton("Jump");
  highlightButton.addEventListener("click", () => {
    const tick = Number(highlightSelect.value);
    if (Number.isFinite(tick)) opts.onSeek?.(tick);
  });

  highlightRow.appendChild(highlightSelect);
  highlightRow.appendChild(highlightButton);
  panel.appendChild(highlightRow);

  const speedRow = document.createElement("div");
  speedRow.style.display = "flex";
  speedRow.style.gap = "6px";
  speedRow.style.alignItems = "center";

  const speedLabel = document.createElement("div");
  speedLabel.textContent = "Speed";
  speedLabel.style.fontSize = "12px";
  speedLabel.style.minWidth = "48px";
  speedRow.appendChild(speedLabel);

  const speeds = [0.5, 1, 2, 4];
  const speedButtons = speeds.map((s) => makeMiniButton(`${s}x`));
  let activeSpeed = 1;
  const setSpeed = (value: number) => {
    activeSpeed = value;
    speedButtons.forEach((b) => (b.dataset.active = "false"));
    const idx = speeds.indexOf(value);
    if (idx >= 0) speedButtons[idx].dataset.active = "true";
    opts.onSpeedChange?.(value);
  };
  speedButtons.forEach((btn, idx) => {
    btn.addEventListener("click", () => setSpeed(speeds[idx]));
    speedRow.appendChild(btn);
  });
  setSpeed(activeSpeed);
  panel.appendChild(speedRow);

  const placeholder = document.createElement("div");
  placeholder.textContent = "Scrub + timeline controls";
  placeholder.style.fontSize = "11px";
  placeholder.style.opacity = "0.7";
  panel.appendChild(placeholder);

  root.appendChild(panel);

  if (opts.store) {
    opts.store.subscribe((s) => {
      if (!dragging) {
        slider.value = String(s.tick);
        tickLabel.textContent = `Tick ${s.tick}`;
      }
    });
  }

  if (opts.viewerStore) {
    opts.viewerStore.subscribe((v) => {
      slider.min = String(v.playbackStartTick);
      slider.max = String(v.playbackEndTick);
      updateKeyframeMarks(datalist, v.keyframeTicks);
      updateHighlightOptions(highlightSelect, v.highlights);
    });
  }

  return root;
}

function makeMiniButton(label: string): HTMLButtonElement {
  const btn = document.createElement("button");
  btn.textContent = label;
  btn.style.padding = "6px 10px";
  btn.style.borderRadius = "10px";
  btn.style.border = "2px solid rgba(31, 36, 43, 0.65)";
  btn.style.background = "rgba(247, 242, 233, 0.9)";
  btn.style.cursor = "pointer";
  btn.style.fontSize = "12px";
  btn.style.fontWeight = "600";
  btn.dataset.active = "false";
  btn.addEventListener("mouseenter", () => {
    btn.style.boxShadow = "0 0 0 2px rgba(90, 169, 178, 0.3)";
  });
  btn.addEventListener("mouseleave", () => {
    btn.style.boxShadow = "none";
  });
  const observer = new MutationObserver(() => {
    if (btn.dataset.active === "true") {
      btn.style.background = "rgba(90, 169, 178, 0.2)";
    } else {
      btn.style.background = "rgba(247, 242, 233, 0.9)";
    }
  });
  observer.observe(btn, { attributes: true, attributeFilter: ["data-active"] });
  return btn;
}

function updateKeyframeMarks(list: HTMLDataListElement, ticks: number[]): void {
  while (list.firstChild) list.removeChild(list.firstChild);
  const cleaned = compressKeyframes(ticks, 60);
  cleaned.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = String(t);
    list.appendChild(opt);
  });
}

function compressKeyframes(ticks: number[], maxCount: number): number[] {
  const unique = Array.from(new Set(ticks.filter((t) => Number.isFinite(t)))).sort((a, b) => a - b);
  if (unique.length <= maxCount) return unique;
  const step = Math.ceil(unique.length / maxCount);
  return unique.filter((_, idx) => idx % step === 0 || idx === unique.length - 1);
}

function updateHighlightOptions(
  select: HTMLSelectElement,
  highlights: Array<{ tick: number; label: string }>
): void {
  const current = select.value;
  while (select.firstChild) select.removeChild(select.firstChild);
  if (highlights.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No highlights yet";
    select.appendChild(opt);
    return;
  }
  highlights.forEach((h) => {
    const opt = document.createElement("option");
    opt.value = String(h.tick);
    opt.textContent = `${h.tick} · ${h.label}`;
    select.appendChild(opt);
  });
  if (current) select.value = current;
}
