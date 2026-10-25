/* Arbor — shared front-end helpers and styles.
 *
 * Widgets are plain DOM mounted with node.addDOMWidget, which both the
 * classic canvas and the Vue (Nodes 2.0) renderer display. Colors come from
 * ComfyUI's theme variables so light and dark palettes both work.
 */

import { app } from "../../scripts/app.js";
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
.arb-cmp-stage img,.arb-cmp-stage video,.arb-cmp-stage canvas{position:absolute;max-width:none;user-select:none;
  -webkit-user-drag:none;pointer-events:none;image-rendering:auto;}
.arb-cmp-stage video{object-fit:fill;background:#000;}
.arb-cmp-stage.wipe{cursor:ew-resize;}
.arb-cmp-div{position:absolute;top:0;bottom:0;width:0;border-left:1.5px solid #fff;
  box-shadow:0 0 0 .5px rgba(0,0,0,.4);pointer-events:none;}
.arb-cmp-div.h{top:50%;left:0;right:0;bottom:auto;height:0;width:auto;border-left:0;
  border-top:1.5px solid var(--arb-line);box-shadow:none;}
.arb-cmp-div.h::after{display:none;}
.arb-cmp-div::after{content:"";position:absolute;top:50%;left:-7px;width:12px;height:12px;
  margin-top:-7px;border-radius:50%;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.45);}
.arb-cmp-tag{position:absolute;top:6px;padding:1px 6px;border-radius:4px;font-size:10px;
  background:rgba(0,0,0,.55);color:#fff;pointer-events:none;max-width:45%;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.arb-tp{display:flex;align-items:center;gap:6px;flex:0 0 auto;height:24px;}
.arb-tp-rail{position:relative;flex:1 1 auto;height:18px;cursor:pointer;touch-action:none;user-select:none;}
.arb-tp-line{position:absolute;left:0;right:0;top:8px;height:3px;border-radius:2px;background:var(--arb-line);}
.arb-tp-fill{position:absolute;left:0;top:0;bottom:0;border-radius:2px;background:var(--arb-accent);}
.arb-tp-knob{position:absolute;top:3px;width:12px;height:12px;margin-left:-6px;border-radius:50%;
  background:var(--arb-fg);box-shadow:0 1px 4px rgba(0,0,0,.4);}
.arb-tp-time{font:10.5px/1 "JetBrains Mono","Cascadia Code",Consolas,monospace;color:var(--arb-sub);
  white-space:nowrap;flex:0 0 auto;}
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

/* ------------------------------------------------------------- load media */
.arb-btn-main{color:var(--arb-fg);border-color:color-mix(in srgb,var(--arb-accent) 60%,var(--arb-line));
  background:var(--arb-accent-soft);}
.arb-btn:disabled{opacity:.45;cursor:default;}
.arb-media-body{position:relative;flex:1 1 auto;min-height:60px;overflow:auto;border-radius:8px;padding:4px;
  background:var(--arb-bg);border:1px solid var(--arb-line);display:flex;flex-direction:column;gap:6px;
  scrollbar-width:thin;scrollbar-color:var(--arb-line) transparent;}
.arb-media-group{border-radius:6px;padding:4px;border:1px solid transparent;}
.arb-media-group.on{border-color:color-mix(in srgb,var(--arb-accent) 45%,transparent);}
.arb-media-hd{display:flex;align-items:center;gap:6px;padding:0 2px 4px;}
.arb-media-name{flex:0 1 160px;min-width:40px;background:transparent;border:0;border-bottom:1px dashed var(--arb-line);
  color:var(--arb-fg);font:600 12px/1.4 inherit;padding:1px 2px;outline:none;}
.arb-media-name:focus{border-bottom-color:var(--arb-accent);}
.arb-media-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:4px;min-height:40px;
  border-radius:5px;}
.arb-media-grid.over{background:var(--arb-accent-soft);}
.arb-media-hint{grid-column:1/-1;color:var(--arb-sub);font-size:11px;padding:10px;text-align:center;}
.arb-media-tile{position:relative;aspect-ratio:1;border-radius:5px;overflow:hidden;cursor:grab;
  background:var(--arb-hover);border:1px solid var(--arb-line);}
.arb-media-tile img{width:100%;height:100%;object-fit:cover;display:block;pointer-events:none;}
.arb-media-tile.over{outline:2px solid var(--arb-accent);}
.arb-media-fn{position:absolute;left:0;right:0;bottom:0;padding:1px 4px;font-size:10px;color:#fff;
  background:rgba(0,0,0,.55);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.arb-media-tile.k-audio .arb-media-fn,.arb-media-tile.noimg .arb-media-fn{position:static;background:none;
  color:var(--arb-fg);white-space:normal;word-break:break-all;padding:20px 4px 2px;}
.arb-media-badge{position:absolute;top:3px;right:4px;font-size:11px;color:#fff;text-shadow:0 0 3px #000;}
.arb-media-tile.k-audio .arb-media-badge{color:var(--arb-accent);text-shadow:none;font-size:14px;left:5px;right:auto;}
.arb-media-x{border:0;background:rgba(0,0,0,.6);color:#fff;width:16px;height:16px;border-radius:50%;padding:0;
  font-size:12px;line-height:16px;cursor:pointer;display:none;}
.arb-media-tile .arb-media-x{position:absolute;top:3px;right:3px;}
.arb-media-tile:hover .arb-media-x,.arb-media-hd:hover .arb-media-x{display:inline-block;}
.arb-media-hd .arb-media-x{background:var(--arb-hover);color:var(--arb-sub);}
.arb-media-ta{flex:1 1 auto;min-height:60px;resize:none;border-radius:8px;border:1px solid var(--arb-line);
  background:var(--arb-bg);color:var(--arb-fg);padding:6px 9px;outline:none;
  font:11.5px/1.6 "JetBrains Mono","Cascadia Code",Consolas,monospace;}

/* folder row (Load Folder): a text widget with a folder icon at its end — a pill on the classic
   canvas, label | box like the other widgets in Nodes 2.0 (.v2) */
.arb.arb-path{flex-direction:row;align-items:center;gap:6px;height:24px;padding:0 3px 0 11px;border-radius:12px;
  background:var(--arb-bg);border:1px solid var(--arb-line);}
.arb-path-label{color:var(--arb-sub);font-size:12px;white-space:nowrap;flex:0 0 auto;overflow:hidden;text-overflow:ellipsis;}
.arb-path-box{flex:1 1 auto;min-width:0;display:flex;align-items:center;gap:4px;height:100%;}
.arb-path-in{flex:1 1 auto;min-width:0;height:20px;border:0;outline:none;background:transparent;color:var(--arb-fg);
  font:12px/20px inherit;text-align:right;text-overflow:ellipsis;}
.arb-path-in:focus{text-align:left;}
.arb-path-btn{flex:0 0 auto;width:20px;height:20px;padding:0;border:0;border-radius:50%;background:transparent;
  color:var(--arb-sub);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}
.arb-path-btn:hover{color:var(--arb-fg);background:var(--arb-hover);}
.arb-path-btn svg{width:14px;height:14px;}
.arb.arb-path.v2{height:auto;padding:0;border:0;border-radius:0;background:transparent;gap:8px;}
.arb-path.v2 .arb-path-label{width:var(--lw,80px);color:var(--lc,rgb(160,160,160));font-weight:var(--lwt,400);}
.arb-path.v2 .arb-path-box{height:var(--bh,32px);padding:0 6px 0 16px;border-radius:6px;
  background:var(--bbg,#313235);}
.arb-path.v2 .arb-path-in{text-align:left;color:var(--bfg,#fff);}
.arb-path.v2 .arb-path-box:focus-within{box-shadow:0 0 0 1px var(--color-border-default,#555);}

/* ------------------------------------------------------------- number slider */
.arb-num{gap:4px;justify-content:center;}
.arb-num-bar{position:relative;flex:0 0 auto;height:30px;border-radius:8px;overflow:hidden;cursor:ew-resize;
  touch-action:none;user-select:none;outline:none;background:var(--arb-bg);border:1px solid var(--arb-line);
  transition:border-color .12s;}
.arb-num-bar:hover{border-color:color-mix(in srgb,var(--arb-fg) 28%,var(--arb-line));}
.arb-num-bar:focus-visible,.arb-num-bar.drag{border-color:var(--arb-accent);}
.arb-num-fill{position:absolute;left:0;top:0;bottom:0;pointer-events:none;
  background:color-mix(in srgb,var(--arb-accent) 34%,transparent);}
.arb-num-bar:hover .arb-num-fill{background:color-mix(in srgb,var(--arb-accent) 40%,transparent);}
.arb-num-bar.drag .arb-num-fill{background:color-mix(in srgb,var(--arb-accent) 46%,transparent);}
.arb-num-val{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;
  font:600 13.5px/1 "JetBrains Mono","Cascadia Code",Consolas,monospace;letter-spacing:-.01em;
  white-space:nowrap;overflow:hidden;}
.arb-num-val.editing{pointer-events:auto;padding:3px;}
.arb-num-bar.int::after{content:attr(data-tag);position:absolute;right:6px;top:50%;transform:translateY(-50%);
  font:600 9px/1 "JetBrains Mono",Consolas,monospace;letter-spacing:.04em;color:var(--arb-sub);
  padding:2px 4px;border-radius:4px;border:1px solid var(--arb-line);pointer-events:none;}
.arb-num-foot{display:flex;align-items:center;justify-content:space-between;gap:6px;min-width:0;padding:0 2px;}
.arb-num-field{font:10.5px/1 "JetBrains Mono","Cascadia Code",Consolas,monospace;color:var(--arb-sub);
  cursor:text;padding:3px 5px;border-radius:4px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.arb-num-field:hover{background:var(--arb-hover);color:var(--arb-fg);}
.arb-num-field.editing{padding:0;flex:0 1 90px;}
.arb-num-step{opacity:.8;}
.arb-num-input{width:100%;min-width:40px;height:100%;box-sizing:border-box;font:inherit;text-align:center;
  color:var(--arb-fg);background:var(--arb-bg);border:1px solid var(--arb-accent);border-radius:5px;
  padding:2px 4px;outline:none;}

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
.arb-name{color:var(--arb-fg);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.arb-name:empty{display:none;}
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
.arb-ed-idx.t-name{color:var(--arb-accent);}
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
.arb-val.t-dict,.arb-val.t-list,.arb-val.t-object,.arb-val.t-audio,.arb-val.t-video{color:var(--arb-sub);}
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

/* Hide a widget that only stores state (both canvas and Vue nodes respect these flags). */
export function hideWidget(w) {
  if (!w) return;
  w.hidden = true;
  w.options ||= {};
  w.options.hidden = true;
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

/* ------------------------------------------------------------- i18n
 * UI text follows ComfyUI's own language setting (Comfy.Locale); node names,
 * inputs and tooltips come from locales/<lang>/nodeDefs.json the same way.
 * Languages without a table here fall back to English. */
const STRINGS = {
  en: {
    flip: "Flip", wipe: "Wipe", real: "Real", fit: "Fit",
    chooseA: "Choose A",
    allGroups: "All", chooseGroup: "Show one top-level branch of the connected trees — or all of them. Plain lists show with every branch",
    scaleTip: "Real: keep relative sizes · Fit: fill the stage",
    openTip: "Open the current file in a new tab",
    sliderEmpty: "Connect images, videos or audio and run to compare",
    playTip: "Play (Space)", pauseTip: "Pause (Space)", loopTip: "Loop",
    muteTip: "Sound on / off — in Wipe you hear the side that shows more, or the half under the pointer",
    addMedia: "Add…", addMediaTip: "System dialog: pick files — or go into a folder and press Add without picking any to add the whole folder (each subfolder a group). Files are used where they are",
    folderPickTip: "Choose the folder with the system dialog",
    saveFolderTip: "Choose where to save with the system dialog — outside the output folder only while ComfyUI listens on this computer alone", dialogSaveFolder: "Save into this folder",
    dialogAdd: "Add pictures, videos or audio — or this whole folder", dialogOk: "Add", thisFolder: "(add this folder)",
    dialogFolder: "Choose a folder",
    dialogRemote: "The system file dialog opens on the computer running ComfyUI — from this one, type the path instead",
    addGroup: "+ Group", viewList: "List", viewText: "Text", groupName: "Group name",
    removeGroup: "Remove group", remove: "Remove", groupEmpty: "Empty — Add… puts files into the selected group",
    mediaEmpty: "Add… to pick pictures, videos or audio — or a whole folder\nEach group becomes a named branch",
    mediaTextPh: "# Group name\nfile.png\nfolder/clip.mp4\nC:/absolute/path/voice.wav\n\nAn empty line starts a new group",
    file_one: "{n} file", file_other: "{n} files", group_one: "{n} group", group_other: "{n} groups",
    live: "Live — updates as you edit, no need to run",
    lines: "Lines", text: "Text",
    linesTip: "Each line is an item · an empty line starts a new branch",
    textTip: "The whole text is one item",
    typedOn: "Typed values on: 7 → INT, 3.5 → FLOAT, true → BOOLEAN. Click to keep every line as text",
    typedOff: "Typed values off: every line stays text. Click to read numbers and true/false",
    collapseAll: "Collapse / expand all branches",
    largeView: "Open large view",
    copyAll: "Copy everything as text",
    copyItem: "Copy this item",
    done: "Done",
    phLines: "Type data — one item per line\n\nAn empty line starts a new branch",
    phText: "Type text — the whole text is one item",
    runToInspect: "Run to inspect the input",
    blocked: "Run to inspect\n{name} can't preview live",
    noData: "No data",
    truncated: "Display truncated — copy to get everything",
    moreItems: "… {n} more",
    emptyBranch: "empty",
    more: "more", less: "less",
    chars: "{n} chars", cutChars: "{n} chars, cut at {m}", linesCount: "{n} lines",
    branch_one: "{n} branch", branch_other: "{n} branches",
    item_one: "{n} item", item_other: "{n} items",
    depth: "depth {n}", listOf: "List · {items}", value: "Value", emptyValue: "Empty",
    largeGraph: "a large graph", missingLink: "a missing link",
    barTip: "Drag to set · click to type · Shift = fine · scroll or ← → to step",
    stepTip: "Click to set the step — 1 gives whole numbers, 0 is continuous",
    minTip: "Click to set the minimum", maxTip: "Click to set the maximum",
    stepIs: "step {s}", stepFree: "no step",
    intMode: "Connected to an INT input — the value is sent as a whole number",
  },
  zh: {
    flip: "切换", wipe: "对比", real: "原比例", fit: "填充",
    chooseA: "选择 A",
    allGroups: "全部", chooseGroup: "只看所接数据树的一个顶层分支——或全部。普通列表在每个分支里都会显示",
    scaleTip: "原比例：保持图片之间的相对大小 · 填充：每张图铺满画面",
    openTip: "在新标签页打开当前文件",
    sliderEmpty: "接入图片、视频或音频并运行后即可对比",
    playTip: "播放（空格）", pauseTip: "暂停（空格）", loopTip: "循环播放",
    muteTip: "声音开 / 关——对比模式下听到占画面更多的一侧，或鼠标所在的那一半",
    addMedia: "添加…", addMediaTip: "系统窗口：选中文件——或者进入一个文件夹、不选文件直接点「添加」，添加整个文件夹（每个子文件夹一个分组）。文件原地使用，不复制",
    folderPickTip: "用系统窗口选择文件夹",
    saveFolderTip: "用系统窗口选择保存位置——只有 ComfyUI 只在本机监听时才能存到 output 以外", dialogSaveFolder: "保存到这个文件夹",
    dialogAdd: "添加图片、视频、音频——或整个当前文件夹", dialogOk: "添加", thisFolder: "（添加当前文件夹）",
    dialogFolder: "选择文件夹",
    dialogRemote: "系统文件窗口只能在运行 ComfyUI 的电脑上打开——在这台电脑上请直接输入路径",
    addGroup: "+ 分组", viewList: "列表", viewText: "文本", groupName: "分组名",
    removeGroup: "删除分组", remove: "移除", groupEmpty: "空分组——点「添加…」把文件放进选中的分组",
    mediaEmpty: "点「添加…」选择图片、视频、音频或整个文件夹\n每个分组成为一个有名字的分支",
    mediaTextPh: "# 分组名\nfile.png\nfolder/clip.mp4\nC:/绝对路径/voice.wav\n\n空一行开始新分组",
    file_one: "{n} 个文件", file_other: "{n} 个文件", group_one: "{n} 个分组", group_other: "{n} 个分组",
    live: "实时 — 编辑时自动更新，无需运行",
    lines: "逐行", text: "整段",
    linesTip: "每行是一项 · 空一行开始新分支",
    textTip: "整段文字作为一项",
    typedOn: "识别数值：7 → INT，3.5 → FLOAT，true → BOOLEAN。点击改为全部保留文本",
    typedOff: "不识别数值：每行都保留为文本。点击改为识别数字和 true/false",
    collapseAll: "折叠 / 展开所有分支",
    largeView: "打开大窗口",
    copyAll: "复制全部文本",
    copyItem: "复制这一项",
    done: "完成",
    phLines: "输入数据 — 每行一项\n\n空一行开始新分支",
    phText: "输入文本 — 整段文字作为一项",
    runToInspect: "运行后查看输入",
    blocked: "运行后查看\n{name} 不支持实时预览",
    noData: "没有数据",
    truncated: "显示已截断 — 复制可获得全部内容",
    moreItems: "… 还有 {n} 项",
    emptyBranch: "空",
    more: "展开", less: "收起",
    chars: "{n} 字", cutChars: "共 {n} 字，显示前 {m} 字", linesCount: "{n} 行",
    branch_one: "{n} 个分支", branch_other: "{n} 个分支",
    item_one: "{n} 项", item_other: "{n} 项",
    depth: "深度 {n}", listOf: "列表 · {items}", value: "单个值", emptyValue: "空",
    largeGraph: "节点过多的工作流", missingLink: "缺失的连线",
    barTip: "拖动取值 · 单击输入 · 按住 Shift 微调 · 滚轮或 ← → 按步长加减",
    stepTip: "点击设置步长 — 1 为整数，0 为连续取值",
    minTip: "点击设置最小值", maxTip: "点击设置最大值",
    stepIs: "步长 {s}", stepFree: "无步长",
    intMode: "已连接到整数参数——数值会取整后传出",
  },
};

export function lang() {
  let l = "en";
  try { l = app.ui?.settings?.getSettingValue?.("Comfy.Locale") || "en"; } catch {}
  return STRINGS[l] ? l : "en";
}

export function t(key, vars) {
  const s = STRINGS[lang()][key] ?? STRINGS.en[key] ?? key;
  return vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : s;
}

/* "{n} items" with the right plural form */
export function tn(key, n) {
  return t(`${key}_${n === 1 ? "one" : "other"}`, { n: n.toLocaleString("en-US") });
}

const localeListeners = new Set();
let lastLang = null;
export function onLocaleChange(fn) {
  localeListeners.add(fn);
  return () => localeListeners.delete(fn);
}
setInterval(() => {
  const l = lang();
  if (lastLang !== null && l !== lastLang) {
    for (const fn of localeListeners) {
      try { fn(l); } catch (e) { console.warn("[Arbor] locale change", e); }
    }
  }
  lastLang = l;
}, 800);

/* Tell ComfyUI the workflow changed (unsaved marker, undo history) after an
 * edit made from our own DOM, which its keyboard / mouse tracking can't see. */
let changeTimer = 0;
export function markChanged(node) {
  node?.graph?.setDirtyCanvas?.(true, false);
  clearTimeout(changeTimer);
  changeTimer = setTimeout(() => {
    try {
      const ct = app.extensionManager?.workflow?.activeWorkflow?.changeTracker;
      (ct?.captureCanvasState ?? ct?.checkState)?.call(ct);
    } catch {}
  }, 300);
}

/* Keep typing inside an editable element: plain keys and text-editing
 * shortcuts stay local, every other Ctrl/⌘/Alt shortcut (save, queue, ...)
 * still reaches ComfyUI. */
const EDIT_KEYS = new Set(["a", "c", "v", "x", "z", "y", "arrowleft", "arrowright", "arrowup",
  "arrowdown", "home", "end", "backspace", "delete"]);
export function isolateKeys(elm) {
  for (const ev of ["keydown", "keyup", "keypress"]) {
    elm.addEventListener(ev, (e) => {
      const mod = e.ctrlKey || e.metaKey || e.altKey;
      if (mod && !EDIT_KEYS.has(String(e.key).toLowerCase())) return;
      e.stopPropagation();
    });
  }
  for (const ev of ["paste", "copy", "cut"]) elm.addEventListener(ev, (e) => e.stopPropagation());
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

/* ------------------------------------------------------------- large view (modal) */

export function openModal(title, buildBody, onClose) {
  const overlay = el("div", "arb arb-modal-wrap");
  const box = overlay.appendChild(el("div", "arb-modal"));
  const hd = box.appendChild(el("div", "arb-bar arb-modal-hd"));
  hd.appendChild(el("span", "arb-modal-title")).textContent = title;
  const extra = hd.appendChild(el("span", "arb-sub"));
  hd.appendChild(el("span", "arb-sp"));
  const close = hd.appendChild(el("button", "arb-btn"));
  close.textContent = t("done");
  const body = box.appendChild(el("div", "arb-modal-body"));
  const done = () => {
    overlay.remove();
    window.removeEventListener("keydown", onKey, true);
    onClose?.();
  };
  const onKey = (e) => {
    if (e.key === "Escape") { e.stopPropagation(); e.preventDefault(); done(); }
  };
  close.addEventListener("click", done);
  overlay.addEventListener("pointerdown", (e) => { if (e.target === overlay) done(); });
  for (const ev of ["pointerdown", "mousedown", "wheel", "dblclick"]) {
    box.addEventListener(ev, (e) => e.stopPropagation(), { passive: true });
  }
  window.addEventListener("keydown", onKey, true);
  document.body.appendChild(overlay);
  buildBody(body, extra);
  return done;
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
  play: `<svg viewBox="0 0 16 16" fill="currentColor"><path d="M5 3.2v9.6a.6.6 0 0 0 .9.5l7.4-4.8a.6.6 0 0 0 0-1L5.9 2.7a.6.6 0 0 0-.9.5z"/></svg>`,
  pause: `<svg viewBox="0 0 16 16" fill="currentColor"><rect x="4" y="3" width="3" height="10" rx=".8"/><rect x="9" y="3" width="3" height="10" rx=".8"/></svg>`,
  loop: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 7.5v-1a2 2 0 0 1 2-2h8M11 2.5l2 2-2 2M13 8.5v1a2 2 0 0 1-2 2H3M5 13.5l-2-2 2-2"/></svg>`,
  sound: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M2.5 6v4H5l3.5 3V3L5 6z"/><path d="M11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.8a6 6 0 0 1 0 8.4"/></svg>`,
  muted: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M2.5 6v4H5l3.5 3V3L5 6z"/><path d="M11 6l3.5 4M14.5 6L11 10"/></svg>`,
  folder: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M1.8 4.2a1 1 0 0 1 1-1h3.3l1.4 1.5h5.7a1 1 0 0 1 1 1v6.6a1 1 0 0 1-1 1H2.8a1 1 0 0 1-1-1z"/></svg>`,
  open: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M9 2.5h4.5V7M13.5 2.5 7.5 8.5M12 9.5v3a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3"/></svg>`,
};
