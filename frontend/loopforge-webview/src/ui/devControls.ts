// src/ui/devControls.ts

type FloorFilter = "all" | 0 | 1;

type DevControlsOpts = {
  onFloorChange: (floor: FloorFilter) => void;
  onRestart: () => void;
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

  const playbackRow = document.createElement("div");
  playbackRow.style.display = "flex";
  playbackRow.style.gap = "8px";
  playbackRow.style.alignItems = "center";

  const restart = makeMiniButton("Restart Playback");
  restart.style.flex = "1";
  restart.addEventListener("click", () => opts.onRestart());
  playbackRow.appendChild(restart);

  panel.appendChild(playbackRow);

  const placeholder = document.createElement("div");
  placeholder.textContent = "Timeline controls coming next";
  placeholder.style.fontSize = "11px";
  placeholder.style.opacity = "0.7";
  panel.appendChild(placeholder);

  root.appendChild(panel);
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
