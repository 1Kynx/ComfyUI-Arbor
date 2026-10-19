/* Arbor · Panel — a Grasshopper-style data panel.
 *
 * Connected: a viewer. Trees render as collapsible branches ({0;1} N=3)
 * with indexed items; plain values and lists render flat; images show a
 * thumbnail (click to open). When everything upstream is a cheap data node
 * (see arbor/live.py) the view updates live as you edit — no queueing;
 * otherwise it shows the result of the last run.
 * Unconnected: an editor. In Lines mode each line is an item and an empty
 * line starts a new branch; in Text mode the whole text is one item. The
 * text and both options live in the node's own hidden widgets, so they are
 * saved with the workflow.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { injectStyle, el, viewURL, isolatePointer, chain, ICONS } from "./arbor_common.js";

const NODE = "Arbor_Panel";
const AUTO_COLLAPSE = 24; // start collapsed when the tree has more branches than this
const LIVE_MS = 350;
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

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
    if (seen.size > 200) return { blocked: "a large graph" };
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
      if (!src) return { blocked: "a missing link" };
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

/* ------------------------------------------------------------ editor helpers */

/* mirror of nodes_panel.parse_text, for the live item count */
function countText(text, multiline) {
  if (multiline) return { branches: 1, items: 1 };
  let branches = 0, items = 0;
  for (const block of text.replace(/\r\n/g, "\n").split(/\n[ \t]*\n/)) {
    const n = block.split("\n").filter((l) => l.trim() !== "").length;
    if (n) { branches++; items += n; }
  }
  return { branches, items };
}

function hideWidget(w) {
  if (!w) return;
  w.hidden = true;
  w.options ||= {};
  w.options.hidden = true;
}

/* ------------------------------------------------------------ view */

class PanelView {
  constructor(node) {
    this.node = node;
    this.data = null;
    this.closed = new Set();
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

  build() {
    const root = (this.root = el("div", "arb arb-pnl"));
    const bar = el("div", "arb-bar");
    this.dot = el("span", "arb-live");
    this.dot.title = "Live — updates as you edit, no need to run";
    this.stats = el("span", "arb-sub", "");

    this.modeSeg = el("div", "arb-seg",
      `<button data-m="lines" title="Each line is an item · an empty line starts a new branch">Lines</button>` +
      `<button data-m="text" title="The whole text is one item">Text</button>`);
    this.modeSeg.addEventListener("click", (e) => {
      const m = e.target?.dataset?.m;
      if (m) this.set("multiline", m === "text");
    });
    this.typeBtn = el("button", "arb-btn arb-type");
    this.typeBtn.addEventListener("click", () => this.set("parse_numbers", !this.w("parse_numbers")?.value));

    this.toggleBtn = el("button", "arb-btn", ICONS.collapse);
    this.toggleBtn.title = "Collapse / expand all branches";
    this.toggleBtn.addEventListener("click", () => this.toggleAll());
    this.copyBtn = el("button", "arb-btn", ICONS.copy);
    this.copyBtn.title = "Copy as text";
    this.copyBtn.addEventListener("click", () => this.copy());
    bar.append(this.dot, this.stats, el("span", "arb-sp"), this.modeSeg, this.typeBtn,
      this.toggleBtn, this.copyBtn);

    this.body = el("div", "arb-pnl-body");
    // wheel scrolls the list instead of zooming the canvas while it can scroll
    this.body.addEventListener("wheel", (e) => {
      const b = this.body;
      if (b.scrollHeight > b.clientHeight + 1) e.stopPropagation();
    }, { passive: true });

    this.editor = el("textarea", "arb-pnl-edit");
    this.editor.spellcheck = false;
    this.editor.addEventListener("input", () => {
      const w = this.w("text");
      if (w) w.value = this.editor.value;
      this.node.graph?.setDirtyCanvas?.(true, false);
      this.renderStats();
    });
    // keep typing / clipboard inside the editor (no canvas shortcuts, no node paste)
    for (const ev of ["keydown", "keyup", "keypress", "paste", "copy", "cut"]) {
      this.editor.addEventListener(ev, (e) => e.stopPropagation());
    }
    this.editor.addEventListener("wheel", (e) => {
      const t = this.editor;
      if (t.scrollHeight > t.clientHeight + 1) e.stopPropagation();
    }, { passive: true });

    root.append(bar, this.body, this.editor);
    isolatePointer(root);
  }

  set(name, value) {
    const w = this.w(name);
    if (!w || w.value === value) return;
    w.value = value;
    this.node.graph?.setDirtyCanvas?.(true, false);
    this.update();
  }

  /* pull widget state into the DOM (after create / load) */
  sync() {
    for (const n of ["text", "parse_numbers", "multiline"]) hideWidget(this.w(n));
    const t = this.w("text")?.value ?? "";
    if (this.editor.value !== t) this.editor.value = t;
    this.update();
  }

  setData(data, live = false) {
    const first = !this.data;
    this.data = data;
    this.live = live;
    this.liveError = null;
    if (first && data.kind === "tree" && data.branches.length > AUTO_COLLAPSE) {
      data.branches.forEach((b) => this.closed.add(b.path));
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
    const multiline = !!this.w("multiline")?.value;
    const numbers = !!this.w("parse_numbers")?.value;
    this.root.classList.toggle("editing", !viewing);
    this.editor.style.display = viewing ? "none" : "";
    this.body.style.display = viewing ? "" : "none";

    this.modeSeg.style.display = viewing ? "none" : "";
    for (const b of this.modeSeg.children) b.classList.toggle("on", (b.dataset.m === "text") === multiline);
    this.typeBtn.style.display = viewing || multiline ? "none" : "";
    this.typeBtn.textContent = numbers ? "123" : "abc";
    this.typeBtn.classList.toggle("on", numbers);
    this.typeBtn.title = numbers
      ? "Numbers on: 7 → INT, 3.5 → FLOAT. Click to keep every line as text"
      : "Numbers off: every line stays text. Click to read numbers";
    this.editor.placeholder = multiline
      ? "Type text — the whole text is one item"
      : "Type data — one item per line\n\nAn empty line starts a new branch";

    this.toggleBtn.style.display = viewing && this.data?.kind === "tree" && !this.liveError ? "" : "none";
    this.dot.style.display = viewing && this.live && !this.liveError ? "" : "none";
    if (viewing) this.render();
    this.renderStats();
  }

  renderStats() {
    if (!this.connected) {
      const c = countText(this.editor.value, !!this.w("multiline")?.value);
      this.stats.textContent = c.items
        ? `${plural(c.branches, "branch", "branches")} · ${plural(c.items, "item", "items")}`
        : "";
      return;
    }
    const d = this.data;
    if (!d || d.source !== "input" || this.liveError) {
      this.stats.textContent = "";
      return;
    }
    const s = d.stats;
    this.stats.textContent = d.kind === "tree"
      ? `${plural(s.branches, "branch", "branches")} · ${plural(s.items, "item", "items")} · depth ${s.depth}`
      : d.kind === "list" ? `List · ${plural(s.items, "item", "items")}` : s.items ? "Value" : "Empty";
  }

  render() {
    const d = this.data;
    const body = this.body;
    body.replaceChildren();
    if (this.liveError) {
      const e = el("div", "arb-err");
      e.textContent = this.liveError;
      body.appendChild(e);
      return;
    }
    if (!d || d.source !== "input") {
      const msg = this.blockedBy
        ? `Run to inspect\n${this.blockedBy} can't preview live`
        : "Run to inspect the input";
      body.appendChild(el("div", "arb-empty")).textContent = msg;
      return;
    }
    this.root.classList.toggle("flat", d.kind !== "tree");
    if (!d.stats.items && !d.branches.length) {
      body.appendChild(el("div", "arb-empty", "No data"));
      return;
    }
    for (const br of d.branches) {
      const wrap = el("div", "arb-br" + (this.closed.has(br.path) ? " closed" : ""));
      if (d.kind === "tree") {
        const hd = el("div", "arb-br-hd");
        hd.innerHTML = `<span class="arb-caret">▾</span><span class="arb-path"></span><span class="arb-n"></span>`;
        hd.children[1].textContent = br.path;
        hd.children[2].textContent = `N=${br.n}`;
        hd.addEventListener("click", () => {
          wrap.classList.toggle("closed");
          if (wrap.classList.contains("closed")) this.closed.add(br.path);
          else this.closed.delete(br.path);
        });
        wrap.appendChild(hd);
      }
      const list = el("div", "arb-br-items");
      br.items.forEach((it, j) => list.appendChild(this.row(it, j)));
      if (br.items.length < br.n) list.appendChild(el("div", "arb-more", `… ${br.n - br.items.length} more`));
      if (!br.n) list.appendChild(el("div", "arb-more", "empty"));
      wrap.appendChild(list);
      body.appendChild(wrap);
    }
    if (d.stats.truncated) body.appendChild(el("div", "arb-more", "Display truncated — copy to get everything"));
  }

  row(it, j) {
    const r = el("div", "arb-row");
    r.appendChild(el("span", "arb-idx", String(j)));
    const v = el("span", `arb-val t-${it.t}`);
    if (it.img) {
      const img = el("img", "arb-thumb");
      img.src = viewURL(it.img);
      img.title = it.v;
      img.addEventListener("click", () => window.open(viewURL(it.img), "_blank"));
      v.appendChild(img);
      v.appendChild(el("span", "", ""));
      v.lastChild.textContent = it.v;
    } else {
      v.textContent = it.t === "str" && it.v === "" ? '""' : it.v;
    }
    r.appendChild(v);
    return r;
  }

  toggleAll() {
    const d = this.data;
    if (!d) return;
    const allClosed = d.branches.every((b) => this.closed.has(b.path));
    this.closed.clear();
    if (!allClosed) d.branches.forEach((b) => this.closed.add(b.path));
    this.render();
  }

  async copy() {
    const text = this.connected ? this.data?.text : this.editor.value;
    if (text == null) return;
    try {
      await navigator.clipboard.writeText(text);
      this.copyBtn.classList.add("on");
      setTimeout(() => this.copyBtn.classList.remove("on"), 700);
    } catch (e) {
      console.warn("[Arbor] copy failed", e);
    }
  }
}

app.registerExtension({
  name: "Arbor.Panel",
  async setup() {
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
