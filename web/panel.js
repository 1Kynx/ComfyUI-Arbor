/* Arbor · Panel — a Grasshopper-style data panel.
 *
 * Connected: a viewer. Trees render as collapsible branches ({0;1} N=3)
 * with indexed items; plain values and lists render flat; images show a
 * thumbnail. Long text folds to a few lines (click "more" to unfold), every
 * item has a copy button, and ⤢ opens a large view. When everything
 * upstream is a cheap data node (see arbor/live.py) the view updates live
 * as you edit — no queueing; otherwise it shows the result of the last run.
 *
 * Unconnected: an editor. In Lines mode each line is an item and an empty
 * line starts a new branch; a gutter shows every line's branch path and
 * item index (coloured by the type it will become). In Text mode the whole
 * text is one item. Long lines wrap; ⤢ opens a large editor. The text and
 * both options live in the node's own hidden widgets, so they are saved
 * with the workflow.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { injectStyle, el, viewURL, isolatePointer, isolateKeys, markChanged, chain, ICONS, t, tn, onLocaleChange } from "./arbor_common.js";

const NODE = "Arbor_Panel";
const AUTO_COLLAPSE = 24; // start collapsed when the tree has more branches than this
const LIVE_MS = 350;
const FOLD_CHARS = 280;   // fold items longer than this...
const FOLD_LINES = 4;     // ...or with more lines than this
const fmtInt = (n) => n.toLocaleString("en-US");

/* ------------------------------------------------------------ live preview */

let liveTypes = null;
const views = new Set();

async function loadLiveTypes() {
  try {
    const r = await api.fetchApi("/arbor/live_types");
    liveTypes = r.ok ? new Set(await r.json()) : new Set();
  } catch {
    liveTypes = new Set();
  }
}

function getLink(graph, id) {
  return graph.links?.get?.(id) ?? graph.links?.[id] ?? graph.getLink?.(id);
}

/* API-style prompt of the panel and everything upstream of it, or the name
 * of the first node that may not run live. */
function upstreamPrompt(panel) {
  const graph = panel.graph;
  const prompt = {};
  const seen = new Set();
  const stack = [panel];
  while (stack.length) {
    const n = stack.pop();
    if (seen.has(n.id)) continue;
    seen.add(n.id);
    if (seen.size > 200) return { blocked: t("largeGraph") };
    const ct = n.comfyClass || n.type;
    if (!liveTypes.has(ct) || n.mode === 2 || n.mode === 4) return { blocked: n.title || ct };
    const inputs = {};
    for (const w of n.widgets || []) {
      if (w.name?.startsWith("arbor_") || w.options?.serialize === false) continue;
      inputs[w.name] = w.value;
    }
    for (const inp of n.inputs || []) {
      if (inp.link == null) continue;
      const l = getLink(graph, inp.link);
      const src = l && graph.getNodeById(l.origin_id);
      if (!src) return { blocked: t("missingLink") };
      inputs[inp.name] = [String(l.origin_id), l.origin_slot];
      stack.push(src);
    }
    prompt[String(n.id)] = { class_type: ct, inputs };
  }
  return { prompt };
}

function liveTick() {
  if (!liveTypes || document.hidden) return;
  for (const v of views) {
    try { v.liveTick(); } catch (e) { console.warn("[Arbor] live preview", e); }
  }
}

/* ------------------------------------------------------------ text model */

const NUM_RE = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

/* type a typed line will become (mirror of nodes_panel.parse_value) */
function lineType(line, numbers) {
  if (!numbers) return "str";
  const t = line.trim();
  if (/^(true|false)$/i.test(t) && (t === t.toLowerCase() || t === t.toUpperCase() || /^[TF][a-z]+$/.test(t))) return "bool";
  if (/^[+-]?\d+$/.test(t)) return "int";
  if (NUM_RE.test(t)) return "float";
  return "str";
}

/* per-line gutter info + counts (mirror of nodes_panel.parse_text) */
function analyse(text, multiline, numbers) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  if (multiline) {
    return { lines: lines.map(() => null), branches: text ? 1 : 0, items: text ? 1 : 0 };
  }
  const out = [];
  let branch = -1, idx = 0, open = false, items = 0;
  for (const line of lines) {
    if (/^[ \t]*$/.test(line)) { // separator, exactly like the server's \n[ \t]*\n split
      open = false;
      out.push(null);
      continue;
    }
    if (line.trim() === "") { // other whitespace: not an item, but no new branch either
      out.push(null);
      continue;
    }
    if (!open) { branch++; idx = 0; open = true; }
    out.push({ path: idx === 0 ? `{${branch}}` : "", i: idx, t: lineType(line, numbers) });
    idx++;
    items++;
  }
  return { lines: out, branches: branch + 1, items };
}

function hideWidget(w) {
  if (!w) return;
  w.hidden = true;
  w.options ||= {};
  w.options.hidden = true;
}

function stopWheelWhenScrollable(elm) {
  elm.addEventListener("wheel", (e) => {
    if (elm.scrollHeight > elm.clientHeight + 1) e.stopPropagation();
  }, { passive: true });
}

async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    btn?.classList.add("on");
    setTimeout(() => btn?.classList.remove("on"), 700);
  } catch (e) {
    console.warn("[Arbor] copy failed", e);
  }
}

/* ------------------------------------------------------------ editor */

/* A textarea over a backdrop that mirrors its wrapped lines, so the gutter
 * labels line up with logical lines even when long lines wrap. */
class TextEditor {
  constructor({ get, set, options, onChange }) {
    this.get = get;
    this.set = set;
    this.options = options; // () => ({multiline, numbers})
    this.onChange = onChange;
    const root = (this.root = el("div", "arb-ed"));
    this.back = el("div", "arb-ed-back");
    this.ta = el("textarea", "arb-ed-ta");
    this.ta.spellcheck = false;
    root.append(this.back, this.ta);
    this.ta.addEventListener("input", () => {
      this.set(this.ta.value);
      this.paint();
      this.onChange?.();
    });
    this.ta.addEventListener("scroll", () => { this.back.scrollTop = this.ta.scrollTop; });
    isolateKeys(this.ta);
    stopWheelWhenScrollable(this.ta);
    this.load();
  }

  load() {
    const t = this.get() ?? "";
    if (this.ta.value !== t) this.ta.value = t;
    this.paint();
  }

  paint() {
    const { multiline, numbers } = this.options();
    this.root.classList.toggle("plain", multiline);
    this.ta.placeholder = t(multiline ? "phText" : "phLines");
    const text = this.ta.value;
    const info = analyse(text, multiline, numbers);
    const frag = document.createDocumentFragment();
    text.split("\n").forEach((line, k) => {
      const row = el("div", "arb-ed-line");
      row.textContent = line || "​";
      const g = info.lines[k];
      if (g) {
        if (g.path) row.appendChild(el("span", "arb-ed-path")).textContent = g.path;
        row.appendChild(el("span", `arb-ed-idx t-${g.t}`)).textContent = String(g.i);
      }
      frag.appendChild(row);
    });
    this.back.replaceChildren(frag);
    this.back.scrollTop = this.ta.scrollTop;
    this.info = info;
  }
}

/* ------------------------------------------------------------ viewer */

function renderData(body, d, state, opts = {}) {
  body.replaceChildren();
  for (const br of d.branches) {
    const wrap = el("div", "arb-br" + (state.closed.has(br.path) ? " closed" : ""));
    if (d.kind === "tree") {
      const hd = el("div", "arb-br-hd");
      hd.innerHTML = `<span class="arb-caret">▾</span><span class="arb-path"></span><span class="arb-n"></span>`;
      hd.children[1].textContent = br.path;
      hd.children[2].textContent = `N=${br.n}`;
      hd.addEventListener("click", () => {
        wrap.classList.toggle("closed");
        if (wrap.classList.contains("closed")) state.closed.add(br.path);
        else state.closed.delete(br.path);
      });
      wrap.appendChild(hd);
    }
    const list = el("div", "arb-br-items");
    br.items.forEach((it, j) => list.appendChild(renderRow(it, j, `${br.path}#${j}`, state, opts)));
    if (br.items.length < br.n) list.appendChild(el("div", "arb-more")).textContent = t("moreItems", { n: br.n - br.items.length });
    if (!br.n) list.appendChild(el("div", "arb-more")).textContent = t("emptyBranch");
    wrap.appendChild(list);
    body.appendChild(wrap);
  }
  if (d.stats.truncated) body.appendChild(el("div", "arb-more")).textContent = t("truncated");
}

function renderRow(it, j, key, state, opts) {
  const r = el("div", "arb-row");
  r.appendChild(el("span", "arb-idx", String(j)));
  const v = el("div", `arb-val t-${it.t}`);
  if (it.img) {
    const img = el("img", "arb-thumb");
    img.src = viewURL(it.img);
    img.title = it.v;
    img.addEventListener("click", () => window.open(viewURL(it.img), "_blank"));
    v.appendChild(img);
    v.appendChild(el("span", "", "")).textContent = it.v;
  } else {
    const text = it.t === "str" && it.v === "" ? '""' : it.v;
    const lines = text.split("\n").length;
    const long = !opts.unfold && (text.length > FOLD_CHARS || lines > FOLD_LINES);
    const body = v.appendChild(el("div", "arb-txt"));
    body.textContent = text;
    if (long || it.len) {
      const open = state.open.has(key);
      body.classList.toggle("fold", long && !open);
      const meta = el("div", "arb-fold");
      const count = it.len ? t("cutChars", { n: fmtInt(it.len), m: fmtInt(text.length) }) : t("chars", { n: fmtInt(text.length) });
      if (long) {
        const btn = meta.appendChild(el("button", "arb-link"));
        btn.textContent = t(open ? "less" : "more");
        btn.addEventListener("click", () => {
          if (state.open.has(key)) state.open.delete(key);
          else state.open.add(key);
          const nowOpen = state.open.has(key);
          body.classList.toggle("fold", !nowOpen);
          btn.textContent = t(nowOpen ? "less" : "more");
        });
      }
      meta.appendChild(el("span", "", "")).textContent = (lines > 1 ? `${t("linesCount", { n: lines })} · ` : "") + count;
      v.appendChild(meta);
    }
  }
  r.appendChild(v);
  if (!it.img) {
    const cp = el("button", "arb-row-copy", ICONS.copy);
    cp.title = t("copyItem");
    cp.addEventListener("click", (e) => { e.stopPropagation(); copyText(it.v, cp); });
    r.appendChild(cp);
  }
  return r;
}

/* ------------------------------------------------------------ large view */

function openModal(title, buildBody, onClose) {
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

/* ------------------------------------------------------------ panel */

class PanelView {
  constructor(node) {
    this.node = node;
    this.data = null;
    this.state = { closed: new Set(), open: new Set() };
    this.live = false;       // current data came from the live preview
    this.blockedBy = null;   // upstream node that prevents live preview
    this.liveError = null;
    this.liveSig = null;
    this.inflight = false;
    this.build();
  }

  w(name) {
    return this.node.widgets?.find((w) => w.name === name);
  }

  get connected() {
    return this.node.inputs?.find((i) => i.name === "data")?.link != null;
  }

  get opts() {
    return { multiline: !!this.w("multiline")?.value, numbers: !!this.w("parse_numbers")?.value };
  }

  build() {
    const root = (this.root = el("div", "arb arb-pnl"));
    const bar = el("div", "arb-bar");
    this.dot = el("span", "arb-live");
    this.stats = el("span", "arb-sub", "");

    this.modeSeg = el("div", "arb-seg", `<button data-m="lines"></button><button data-m="text"></button>`);
    this.modeSeg.addEventListener("click", (e) => {
      const m = e.target?.dataset?.m;
      if (m) this.set("multiline", m === "text");
    });
    this.typeBtn = el("button", "arb-btn arb-type");
    this.typeBtn.addEventListener("click", () => this.set("parse_numbers", !this.w("parse_numbers")?.value));

    this.toggleBtn = el("button", "arb-btn", ICONS.collapse);
    this.toggleBtn.addEventListener("click", () => this.toggleAll());
    this.bigBtn = el("button", "arb-btn", ICONS.expand4);
    this.bigBtn.addEventListener("click", () => this.openLarge());
    this.copyBtn = el("button", "arb-btn", ICONS.copy);
    this.copyBtn.addEventListener("click", () => {
      const text = this.connected ? this.data?.text : this.w("text")?.value;
      if (text != null) copyText(text, this.copyBtn);
    });
    bar.append(this.dot, this.stats, el("span", "arb-sp"), this.modeSeg, this.typeBtn,
      this.toggleBtn, this.bigBtn, this.copyBtn);

    this.body = el("div", "arb-pnl-body");
    stopWheelWhenScrollable(this.body);

    this.editor = new TextEditor({
      get: () => this.w("text")?.value ?? "",
      set: (t) => {
        const w = this.w("text");
        if (w) w.value = t;
        markChanged(this.node);
      },
      options: () => this.opts,
      onChange: () => this.renderStats(),
    });

    root.append(bar, this.body, this.editor.root);
    isolatePointer(root);
  }

  /* static labels in the current UI language */
  relabel() {
    this.dot.title = t("live");
    const [lines, text] = this.modeSeg.children;
    lines.textContent = t("lines");
    lines.title = t("linesTip");
    text.textContent = t("text");
    text.title = t("textTip");
    this.toggleBtn.title = t("collapseAll");
    this.bigBtn.title = t("largeView");
    this.copyBtn.title = t("copyAll");
  }

  set(name, value) {
    const w = this.w(name);
    if (!w || w.value === value) return;
    w.value = value;
    markChanged(this.node);
    this.update();
  }

  /* pull widget state into the DOM (after create / load) */
  sync() {
    for (const n of ["text", "parse_numbers", "multiline"]) hideWidget(this.w(n));
    this.editor.load();
    this.update();
  }

  setData(data, live = false) {
    const first = !this.data;
    this.data = data;
    this.live = live;
    this.liveError = null;
    if (first && data.kind === "tree" && data.branches.length > AUTO_COLLAPSE) {
      data.branches.forEach((b) => this.state.closed.add(b.path));
    }
    this.update();
  }

  liveTick() {
    if (!this.connected || !this.node.graph) {
      this.liveSig = null;
      return;
    }
    const r = upstreamPrompt(this.node);
    if (r.blocked) {
      if (this.blockedBy !== r.blocked || this.live) {
        this.blockedBy = r.blocked;
        this.liveSig = null;
        this.live = false;
        if (this.data?.live) this.data = null; // a stale live result would mislead
        this.update();
      }
      return;
    }
    const sig = JSON.stringify(r.prompt);
    if (sig === this.liveSig || this.inflight) return;
    this.liveSig = sig;
    this.blockedBy = null;
    this.inflight = true;
    api.fetchApi("/arbor/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: r.prompt, target: String(this.node.id) }),
    })
      .then((res) => res.json())
      .then((res) => {
        if (sig !== this.liveSig) return;
        if (res.ok) {
          this.setData(res.payload, true);
        } else if (res.unsupported) {
          this.blockedBy = res.unsupported;
          this.live = false;
          this.update();
        } else {
          this.liveError = res.error;
          this.live = true;
          this.update();
        }
      })
      .catch(() => { this.liveSig = null; })
      .finally(() => { this.inflight = false; });
  }

  update() {
    const viewing = this.connected;
    const { multiline, numbers } = this.opts;
    this.root.classList.toggle("editing", !viewing);
    this.editor.root.style.display = viewing ? "none" : "";
    this.body.style.display = viewing ? "" : "none";

    this.modeSeg.style.display = viewing ? "none" : "";
    for (const b of this.modeSeg.children) b.classList.toggle("on", (b.dataset.m === "text") === multiline);
    this.typeBtn.style.display = viewing || multiline ? "none" : "";
    this.typeBtn.textContent = numbers ? "123" : "abc";
    this.typeBtn.classList.toggle("on", numbers);
    this.typeBtn.title = t(numbers ? "typedOn" : "typedOff");

    this.toggleBtn.style.display = viewing && this.data?.kind === "tree" && !this.liveError ? "" : "none";
    this.dot.style.display = viewing && this.live && !this.liveError ? "" : "none";
    if (viewing) this.render();
    else this.editor.paint();
    this.renderStats();
  }

  renderStats() {
    if (!this.connected) {
      const c = this.editor.info || analyse(this.w("text")?.value ?? "", this.opts.multiline, this.opts.numbers);
      this.stats.textContent = c.items ? `${tn("branch", c.branches)} · ${tn("item", c.items)}` : "";
      return;
    }
    const d = this.data;
    if (!d || d.source !== "input" || this.liveError) {
      this.stats.textContent = "";
      return;
    }
    this.stats.textContent = statsText(d);
  }

  render() {
    const d = this.data;
    const body = this.body;
    body.replaceChildren();
    if (this.liveError) {
      body.appendChild(el("div", "arb-err")).textContent = this.liveError;
      return;
    }
    if (!d || d.source !== "input") {
      body.appendChild(el("div", "arb-empty")).textContent = this.blockedBy
        ? t("blocked", { name: this.blockedBy })
        : t("runToInspect");
      return;
    }
    this.root.classList.toggle("flat", d.kind !== "tree");
    if (!d.stats.items && !d.branches.length) {
      body.appendChild(el("div", "arb-empty")).textContent = t("noData");
      return;
    }
    renderData(body, d, this.state);
  }

  toggleAll() {
    const d = this.data;
    if (!d) return;
    const allClosed = d.branches.every((b) => this.state.closed.has(b.path));
    this.state.closed.clear();
    if (!allClosed) d.branches.forEach((b) => this.state.closed.add(b.path));
    this.render();
  }

  openLarge() {
    const title = this.node.title || "Panel";
    if (!this.connected) {
      openModal(title, (body, extra) => {
        const big = new TextEditor({
          get: () => this.w("text")?.value ?? "",
          set: (t) => {
            const w = this.w("text");
            if (w) w.value = t;
            markChanged(this.node);
          },
          options: () => this.opts,
          onChange: () => {
            const c = big.info;
            extra.textContent = `${tn("branch", c.branches)} · ${tn("item", c.items)}`;
          },
        });
        big.root.classList.add("big");
        body.appendChild(big.root);
        big.onChange();
        setTimeout(() => big.ta.focus(), 0);
      }, () => { this.editor.load(); this.renderStats(); });
      return;
    }
    if (!this.data || this.data.source !== "input") return;
    openModal(title, (body, extra) => {
      extra.textContent = statsText(this.data);
      const list = body.appendChild(el("div", "arb-pnl-body big"));
      renderData(list, this.data, this.state, { unfold: true });
    }, () => this.render());
  }
}

function statsText(d) {
  const s = d.stats;
  return d.kind === "tree"
    ? `${tn("branch", s.branches)} · ${tn("item", s.items)} · ${t("depth", { n: s.depth })}`
    : d.kind === "list" ? t("listOf", { items: tn("item", s.items) }) : t(s.items ? "value" : "emptyValue");
}

app.registerExtension({
  name: "Arbor.Panel",
  async setup() {
    onLocaleChange(() => views.forEach((v) => { v.relabel(); v.update(); }));
    await loadLiveTypes();
    setInterval(liveTick, LIVE_MS);
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const view = new PanelView(this);
      this.__arborPanel = view;
      views.add(view);
      view.relabel();
      this.addDOMWidget("arbor_panel", "arbor-panel", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 140,
      });
      view.sync();
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 300), Math.max(h, 260)]);
    });

    chain(nodeType.prototype, "onRemoved", function () {
      views.delete(this.__arborPanel);
    });

    chain(nodeType.prototype, "onConfigure", function () {
      this.__arborPanel?.sync();
    });

    chain(nodeType.prototype, "onConnectionsChange", function () {
      const v = this.__arborPanel;
      if (!v) return;
      v.liveSig = null;
      v.update();
    });

    chain(nodeType.prototype, "onExecuted", function (output) {
      const data = output?.arbor_panel?.[0];
      const v = this.__arborPanel;
      // a run of a live-capable graph matches the live view, so it stays "live"
      if (data && data.source === "input") v?.setData(data, v.liveSig != null && !v.blockedBy);
    });
  },
});
