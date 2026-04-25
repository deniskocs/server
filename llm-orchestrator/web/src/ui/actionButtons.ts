const NS = "http://www.w3.org/2000/svg";
/** Tight 16×16 artboard, 12px output — small & minimal. */
const VB = "0 0 16 16";
const PX = "12";

function path(d: string, stroke?: boolean) {
  const o = document.createElementNS(NS, "path");
  o.setAttribute("d", d);
  if (stroke) {
    o.setAttribute("fill", "none");
    o.setAttribute("stroke", "currentColor");
    o.setAttribute("stroke-width", "1.15");
    o.setAttribute("stroke-linecap", "round");
    o.setAttribute("stroke-linejoin", "round");
  } else {
    o.setAttribute("fill", "currentColor");
  }
  return o;
}

function makeSvg(children: SVGElement[]): SVGSVGElement {
  const s = document.createElementNS(NS, "svg");
  s.setAttribute("viewBox", VB);
  s.setAttribute("class", "action-btn__svg");
  s.setAttribute("width", PX);
  s.setAttribute("height", PX);
  s.setAttribute("aria-hidden", "true");
  for (const c of children) s.append(c);
  return s;
}

function iconPlay() {
  return makeSvg([path("M4 2.5l9 5.5-9 5.5V2.5z", false)]);
}

function iconStop() {
  return makeSvg([path("M4 4h8v8H4V4z", false)]);
}

function iconLoad() {
  return makeSvg([
    path("M2.5 12.5H14M8 2.5v6m0 0l2-2M8 8.5L6 6.5", true),
  ]);
}

function iconTrash() {
  return makeSvg([
    path("M2.5 4h11M5.5 4V3h5v1M4.5 5h7l-1 8h-5l-1-8M6.5 7.5v3M9.5 7.5v3", true),
  ]);
}

function iconViewConfig() {
  return makeSvg([
    path("M3 1.5h10v12H3v-12zM4.5 4.5h7M4.5 7h5.5M4.5 9.5h4", true),
  ]);
}

type Variant = "viewConfig" | "load" | "play" | "stop" | "trashModel" | "trashConfig";

const hints: Record<Variant, { title: string; label: string }> = {
  viewConfig: { title: "Edit config (open editor, save to disk)", label: "Edit config" },
  load: { title: "Download model weights to disk", label: "Download" },
  play: { title: "Start model with this config", label: "Play" },
  stop: { title: "Stop running model", label: "Stop" },
  trashModel: { title: "Delete model from disk (weights)", label: "Delete model" },
  trashConfig: { title: "Delete this config file", label: "Delete config" },
};

const glyph: Record<Variant, () => SVGSVGElement> = {
  viewConfig: iconViewConfig,
  load: iconLoad,
  play: iconPlay,
  stop: iconStop,
  trashModel: iconTrash,
  trashConfig: iconTrash,
};

const classFor: Record<Variant, string> = {
  viewConfig: "btn-ic btn-ic--view",
  load: "btn-ic btn-ic--load",
  play: "btn-ic btn-ic--play",
  stop: "btn-ic btn-ic--stop",
  trashModel: "btn-ic btn-ic--trash-model",
  trashConfig: "btn-ic btn-ic--trash-config",
};

export function createActionButton(
  v: Variant,
  options?: { disabled?: boolean; busy?: boolean }
): HTMLButtonElement {
  const b = document.createElement("button");
  b.type = "button";
  b.className = classFor[v];
  b.disabled = options?.disabled ?? false;
  const h = hints[v];
  b.title = h.title;
  b.setAttribute("aria-label", h.label);
  if (options?.busy) b.setAttribute("aria-busy", "true");
  b.append(glyph[v]());
  return b;
}
