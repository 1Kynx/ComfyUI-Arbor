/* Arbor — shared front-end helpers and styles.
 *
 * Widgets are plain DOM mounted with node.addDOMWidget, which both the
 * classic canvas and the Vue (Nodes 2.0) renderer display. Colors come from
 * ComfyUI's theme variables so light and dark palettes both work.
 */

import { api } from "../../scripts/api.js";

const STYLE_ID = "arbor-style";

const CSS = `
.arb{--arb-bg:var(--comfy-input-bg,#1b1b1f);--arb-fg:var(--input-text,#e4e4e7);
  --arb-sub:var(--descrip-text,#8b8b95);--arb-line:var(--border-color,#36363d);
  --arb-hover:color-mix(in srgb,var(--arb-fg) 8%,transparent);
  --arb-accent:#5fbf9a;--arb-accent-soft:color-mix(in srgb,#5fbf9a 16%,transparent);
  display:flex;flex-direction:column;gap:6px;width:100%;height:100%;min-height:0;
  box-sizing:border-box;color:var(--arb-fg);font:12px/1.4 Inter,"Segoe UI",system-ui,sans-serif;}
.arb *{box-sizing:border-box;}
.arb button{font:inherit;color:inherit;}
.arb-bar{display:flex;align-items:center;gap:6px;flex:0 0 auto;min-height:24px;}
.arb-sp{flex:1 1 auto;}
.arb-sub{color:var(--arb-sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;}
.arb-seg{display:inline-flex;padding:2px;border-radius:7px;background:var(--arb-bg);
  border:1px solid var(--arb-line);flex:0 0 auto;}
.arb-seg button{border:0;background:transparent;padding:2px 9px;border-radius:5px;cursor:pointer;
  color:var(--arb-sub);font-size:11px;line-height:16px;}
.arb-seg button:hover{color:var(--arb-fg);}
.arb-seg button.on{background:var(--arb-accent-soft);color:var(--arb-fg);}
.arb-btn{border:1px solid var(--arb-line);background:var(--arb-bg);border-radius:6px;
  height:22px;min-width:22px;padding:0 7px;cursor:pointer;color:var(--arb-sub);font-size:11px;
  display:inline-flex;align-items:center;justify-content:center;gap:4px;flex:0 0 auto;}
.arb-btn:hover{color:var(--arb-fg);border-color:color-mix(in srgb,var(--arb-fg) 30%,var(--arb-line));}
.arb-btn.on{color:var(--arb-fg);background:var(--arb-accent-soft);border-color:var(--arb-accent);}
.arb-btn svg{width:13px;height:13px;}
.arb-empty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  color:var(--arb-sub);font-size:11px;text-align:center;padding:12px;pointer-events:none;white-space:pre-line;line-height:1.6;}
.arb-menu{position:fixed;z-index:10000;min-width:160px;max-height:260px;overflow:auto;padding:4px;
  border-radius:8px;border:1px solid var(--border-color,#36363d);
  background:var(--comfy-menu-bg,#232327);color:var(--input-text,#e4e4e7);
  box-shadow:0 8px 28px rgba(0,0,0,.35);font:12px/1.4 Inter,"Segoe UI",system-ui,sans-serif;}
.arb-menu div{padding:4px 8px;border-radius:5px;cursor:pointer;white-space:nowrap;
  display:flex;gap:8px;align-items:center;}
.arb-menu div:hover{background:color-mix(in srgb,currentColor 10%,transparent);}
.arb-menu div.on{color:#5fbf9a;}
.arb-menu img{width:22px;height:22px;object-fit:cover;border-radius:4px;}

/* ------------------------------------------------------------- compare */
.arb-cmp-stage{position:relative;flex:1 1 auto;min-height:120px;border-radius:8px;overflow:hidden;
  background:var(--arb-bg);border:1px solid var(--arb-line);
  background-image:linear-gradient(45deg,var(--arb-hover) 25%,transparent 25%),
    linear-gradient(-45deg,var(--arb-hover) 25%,transparent 25%),
    linear-gradient(45deg,transparent 75%,var(--arb-hover) 75%),
    linear-gradient(-45deg,transparent 75%,var(--arb-hover) 75%);
  background-size:16px 16px;background-position:0 0,0 8px,8px -8px,-8px 0;}
.arb-cmp-stage img{position:absolute;max-width:none;user-select:none;-webkit-user-drag:none;
  pointer-events:none;image-rendering:auto;}
.arb-cmp-stage.wipe{cursor:ew-resize;}
.arb-cmp-div{position:absolute;top:0;bottom:0;width:0;border-left:1.5px solid #fff;
  box-shadow:0 0 0 .5px rgba(0,0,0,.4);pointer-events:none;}
.arb-cmp-div::after{content:"";position:absolute;top:50%;left:-7px;width:12px;height:12px;
  margin-top:-7px;border-radius:50%;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.45);}
.arb-cmp-tag{position:absolute;top:6px;padding:1px 6px;border-radius:4px;font-size:10px;
  background:rgba(0,0,0,.55);color:#fff;pointer-events:none;max-width:45%;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.arb-scrub{position:relative;flex:0 0 auto;height:26px;cursor:pointer;touch-action:none;
  user-select:none;}
.arb-scrub-rail{position:absolute;left:8px;right:8px;top:12px;height:2px;border-radius:2px;
  background:var(--arb-line);}
.arb-scrub-fill{position:absolute;left:0;top:0;bottom:0;border-radius:2px;background:var(--arb-accent);}
.arb-scrub-tick{position:absolute;top:-2px;width:6px;height:6px;margin-left:-3px;border-radius:50%;
  background:var(--arb-line);}
.arb-scrub-tick.done{background:var(--arb-accent);}
.arb-scrub-tick.pin{background:transparent;border:1.5px solid var(--arb-fg);}
.arb-scrub-knob{position:absolute;top:-6px;width:14px;height:14px;margin-left:-7px;border-radius:50%;
  background:var(--arb-fg);box-shadow:0 1px 4px rgba(0,0,0,.4);transition:left .08s ease-out;}
.arb-scrub.drag .arb-scrub-knob{transition:none;}
.arb-scrub-tip{position:absolute;bottom:22px;transform:translateX(-50%);padding:2px 6px;border-radius:4px;
  background:var(--comfy-menu-bg,#232327);border:1px solid var(--arb-line);font-size:10px;
  white-space:nowrap;pointer-events:none;opacity:0;transition:opacity .1s;}
.arb-scrub:hover .arb-scrub-tip,.arb-scrub.drag .arb-scrub-tip{opacity:1;}
.arb-chip{display:inline-flex;align-items:center;gap:4px;max-width:46%;padding:1px 7px 1px 2px;
  border-radius:6px;border:1px solid var(--arb-line);background:var(--arb-bg);cursor:pointer;
  font-size:11px;color:var(--arb-fg);flex:0 1 auto;min-width:0;}
.arb-chip b{font-weight:600;color:var(--arb-bg);background:var(--arb-fg);border-radius:4px;
  padding:0 4px;font-size:10px;}
.arb-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* ------------------------------------------------------------- number slider */
.arb-num{gap:8px;outline:none;justify-content:center;}
.arb-num-top{display:flex;align-items:baseline;gap:6px;min-width:0;}
.arb-num-val{font:600 20px/1.1 "JetBrains Mono","Cascadia Code",Consolas,monospace;
  letter-spacing:-.01em;cursor:text;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.arb-num:focus-within .arb-num-val{color:var(--arb-accent);}
.arb-num-step{font:10px/1 "JetBrains Mono",Consolas,monospace;height:20px;}
.arb-num-row{display:flex;align-items:center;gap:8px;min-width:0;}
.arb-num-end{font:10.5px/1 "JetBrains Mono",Consolas,monospace;color:var(--arb-sub);cursor:text;
  padding:3px 4px;border-radius:4px;flex:0 0 auto;max-width:30%;overflow:hidden;text-overflow:ellipsis;}
.arb-num-end:hover{background:var(--arb-hover);color:var(--arb-fg);}
.arb-num-track{position:relative;flex:1 1 auto;height:22px;cursor:ew-resize;touch-action:none;}
.arb-num-track::before{content:"";position:absolute;left:0;right:0;top:10px;height:3px;border-radius:3px;
  background:var(--arb-line);}
.arb-num-fill{position:absolute;left:0;top:10px;height:3px;border-radius:3px;background:var(--arb-accent);}
.arb-num-knob{position:absolute;top:4px;width:14px;height:14px;margin-left:-7px;border-radius:50%;
  background:var(--arb-fg);box-shadow:0 1px 4px rgba(0,0,0,.4);}
.arb-num-track:hover .arb-num-knob,.arb-num-track.drag .arb-num-knob{box-shadow:0 0 0 4px var(--arb-accent-soft),0 1px 4px rgba(0,0,0,.4);}
.arb-num-input{width:100%;min-width:48px;font:inherit;color:var(--arb-fg);background:var(--arb-bg);
  border:1px solid var(--arb-accent);border-radius:4px;padding:1px 4px;outline:none;}

/* ------------------------------------------------------------- panel */
.arb-pnl-body{position:relative;flex:1 1 auto;min-height:60px;overflow:auto;contain:size;border-radius:8px;
  background:var(--arb-bg);border:1px solid var(--arb-line);padding:4px 0;
  font:11.5px/1.5 "JetBrains Mono","Cascadia Code",Consolas,monospace;
  scrollbar-width:thin;scrollbar-color:var(--arb-line) transparent;}
.arb-br-hd{display:flex;align-items:center;gap:6px;padding:2px 8px;cursor:pointer;user-select:none;
  position:sticky;top:-4px;background:var(--arb-bg);z-index:1;}
.arb-br-hd:hover{background:var(--arb-hover);}
.arb-caret{width:10px;color:var(--arb-sub);transition:transform .12s;display:inline-block;}
.arb-br.closed .arb-caret{transform:rotate(-90deg);}
.arb-br.closed .arb-br-items{display:none;}
.arb-path{color:var(--arb-accent);font-weight:600;}
.arb-n{color:var(--arb-sub);font-size:10.5px;}
.arb-row{display:flex;gap:10px;padding:0 8px 0 24px;align-items:flex-start;}
.arb-row:hover{background:var(--arb-hover);}
.arb-idx{color:var(--arb-sub);min-width:18px;text-align:right;flex:0 0 auto;user-select:none;}
.arb-row{position:relative;}
.arb-val{white-space:pre-wrap;word-break:break-word;min-width:0;flex:1 1 auto;user-select:text;}
.arb-txt.fold{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.arb-fold{display:flex;gap:8px;align-items:center;font-size:10px;color:var(--arb-sub);margin:1px 0 3px;}
.arb-link{border:0;background:none;padding:0;cursor:pointer;color:var(--arb-accent);font-size:10px;}
.arb-link:hover{text-decoration:underline;}
.arb-row-copy{position:absolute;right:6px;top:1px;width:20px;height:18px;border-radius:4px;padding:0;
  display:none;align-items:center;justify-content:center;cursor:pointer;color:var(--arb-sub);
  border:1px solid var(--arb-line);background:var(--arb-bg);}
.arb-row-copy svg{width:11px;height:11px;}
.arb-row:hover .arb-row-copy{display:inline-flex;}
.arb-row-copy:hover,.arb-row-copy.on{color:var(--arb-accent);border-color:var(--arb-accent);}

/* editor: textarea over a backdrop that mirrors its wrapped lines */
.arb-ed{position:relative;flex:1 1 auto;min-height:60px;contain:size;border-radius:8px;overflow:hidden;
  background:var(--arb-bg);border:1px solid var(--arb-line);--g:44px;}
.arb-ed:focus-within{border-color:color-mix(in srgb,var(--arb-accent) 70%,var(--arb-line));}
.arb-ed.plain{--g:9px;}
.arb-ed-back,.arb-ed-ta{position:absolute;inset:0;margin:0;padding:6px 9px 6px var(--g);
  font:11.5px/1.6 "JetBrains Mono","Cascadia Code",Consolas,monospace;tab-size:2;
  white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;overflow-y:scroll;overflow-x:hidden;
  scrollbar-width:thin;}
.arb-ed-back{color:transparent;pointer-events:none;scrollbar-color:transparent transparent;}
.arb-ed-ta{resize:none;outline:none;border:0;background:transparent;color:var(--arb-fg);
  scrollbar-color:var(--arb-line) transparent;caret-color:var(--arb-accent);}
.arb-ed-ta::placeholder{color:var(--arb-sub);opacity:.7;}
.arb-ed-line{position:relative;min-height:1.6em;}
.arb-ed-path,.arb-ed-idx{position:absolute;top:0;font-size:9.5px;line-height:18.4px;user-select:none;}
.arb-ed-path{left:calc(-1 * var(--g) + 4px);color:var(--arb-accent);font-weight:600;}
.arb-ed-idx{right:calc(100% + 7px);color:var(--arb-sub);text-align:right;}
.arb-ed-idx.t-int,.arb-ed-idx.t-float{color:#7fb4f0;}
.arb-ed-idx.t-bool{color:#c49bf0;}
.arb-ed.big{flex:1 1 auto;--g:56px;}
.arb-ed.big .arb-ed-back,.arb-ed.big .arb-ed-ta{font-size:13px;padding-top:10px;}
.arb-ed.big .arb-ed-path,.arb-ed.big .arb-ed-idx{line-height:20.8px;font-size:10.5px;}
.arb-ed.big.plain{--g:12px;}

/* large view */
.arb-modal-wrap{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.45);display:flex;
  align-items:center;justify-content:center;padding:4vh 4vw;height:auto;}
.arb-modal{display:flex;flex-direction:column;gap:8px;width:min(1100px,100%);height:100%;padding:12px 14px;
  border-radius:12px;background:var(--comfy-menu-bg,#232327);border:1px solid var(--arb-line);
  box-shadow:0 18px 60px rgba(0,0,0,.45);}
.arb-modal-title{font-weight:600;font-size:13px;}
.arb-modal-body{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;}
.arb-pnl-body.big{font-size:12.5px;}
.arb-val.t-int,.arb-val.t-float{color:#7fb4f0;}
.arb-val.t-bool{color:#c49bf0;}
.arb-val.t-null{color:var(--arb-sub);font-style:italic;}
.arb-val.t-image,.arb-val.t-mask,.arb-val.t-latent,.arb-val.t-tensor,.arb-val.t-tree,
.arb-val.t-dict,.arb-val.t-list,.arb-val.t-object{color:var(--arb-sub);}
.arb-val.t-image{display:flex;align-items:center;gap:8px;}
.arb-thumb{display:block;max-width:64px;max-height:64px;border-radius:4px;margin:2px 0;flex:0 0 auto;
  border:1px solid var(--arb-line);cursor:zoom-in;}
.arb-pnl.flat .arb-row{padding-left:8px;}
.arb-btn.arb-type{font:600 10px/1 "JetBrains Mono",Consolas,monospace;min-width:34px;letter-spacing:.02em;}
.arb-live{width:6px;height:6px;border-radius:50%;background:var(--arb-accent);flex:0 0 auto;
  box-shadow:0 0 0 3px var(--arb-accent-soft);}
.arb-err{padding:6px 9px;color:#e08a7a;white-space:pre-wrap;word-break:break-word;}
.arb-more{padding:4px 8px;color:var(--arb-sub);font-style:italic;}
`;

export function injectStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = CSS;
  document.head.appendChild(s);
}

export function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}

export function viewURL(ref) {
  const q = new URLSearchParams({
    filename: ref.filename, subfolder: ref.subfolder || "", type: ref.type || "temp",
  });
  return api.apiURL(`/view?${q.toString()}`);
}

/* Keep pointer gestures inside the widget from dragging/zooming the node. */
export function isolatePointer(element) {
  for (const ev of ["pointerdown", "mousedown", "dblclick"]) {
    element.addEventListener(ev, (e) => e.stopPropagation());
  }
}

/* Chain a prototype callback, keeping whatever was there. */
export function chain(proto, name, fn) {
  const prev = proto[name];
  proto[name] = function (...args) {
    const r = prev?.apply(this, args);
    try { fn.apply(this, args); } catch (err) { console.warn(`[Arbor] ${name} failed`, err); }
    return r;
  };
}

let openMenuEl = null;
export function closeMenu() {
  openMenuEl?.remove();
  openMenuEl = null;
}

/* Small floating menu; items: [{label, img?, on?, pick}] */
export function showMenu(anchor, items) {
  closeMenu();
  const m = el("div", "arb-menu");
  for (const it of items) {
    const row = el("div", it.on ? "on" : "");
    if (it.img) row.appendChild(Object.assign(el("img"), { src: it.img }));
    row.appendChild(el("span", "", ""));
    row.lastChild.textContent = it.label;
    row.addEventListener("pointerdown", (e) => { e.stopPropagation(); closeMenu(); it.pick(); });
    m.appendChild(row);
  }
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  const top = Math.min(r.bottom + 4, window.innerHeight - m.offsetHeight - 8);
  m.style.left = `${Math.max(8, Math.min(r.left, window.innerWidth - m.offsetWidth - 8))}px`;
  m.style.top = `${Math.max(8, top)}px`;
  openMenuEl = m;
  setTimeout(() => window.addEventListener("pointerdown", closeMenu, { once: true }), 0);
}

export const ICONS = {
  copy: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="5" y="5" width="8.5" height="8.5" rx="1.5"/><path d="M3 10.5V3.5A1 1 0 0 1 4 2.5h7"/></svg>`,
  collapse: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 6l4 4 4-4"/></svg>`,
  expand: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M6 4l4 4-4 4"/></svg>`,
  expand4: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M9.5 2.5h4v4M6.5 13.5h-4v-4M13.5 2.5 9 7M2.5 13.5 7 9"/></svg>`,
  open: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M9 2.5h4.5V7M13.5 2.5 7.5 8.5M12 9.5v3a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3"/></svg>`,
};
