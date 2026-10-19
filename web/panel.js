/* Arbor · Panel — a Grasshopper-style data panel.
 *
 * Connected: a viewer. Trees render as collapsible branches ({0;1} N=3)
 * with indexed items; plain values and lists render flat; images show a
 * thumbnail (click to open).
 * Unconnected: an editor. Each line is an item, an empty line starts a new
 * branch. The text lives in the node's own (hidden) `text` widget so it is
 * saved with the workflow; two toolbar toggles drive the hidden
 * `parse_numbers` and `multiline` widgets.
 */

import { app } from "../../scripts/app.js";
import { injectStyle, el, viewURL, isolatePointer, chain, ICONS } from "./arbor_common.js";

const NODE = "Arbor_Panel";
const AUTO_COLLAPSE = 24; // collapse every branch when the tree has more than this
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

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

class PanelView {
  constructor(node) {
    this.node = node;
    this.data = null;
    this.closed = new Set();
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
    this.stats = el("span", "arb-sub", "");
    this.numBtn = el("button", "arb-btn arb-txt", "1.0");
    this.numBtn.title = "Parse numbers: lines like 7 or 3.5 become INT / FLOAT";
    this.numBtn.addEventListener("click", () => this.flip("parse_numbers"));
    this.mlBtn = el("button", "arb-btn arb-txt", "¶");
    this.mlBtn.title = "Multiline: the whole text is one item";
    this.mlBtn.addEventListener("click", () => this.flip("multiline"));
    this.toggleBtn = el("button", "arb-btn", ICONS.collapse);
    this.toggleBtn.title = "Collapse / expand all branches";
    this.toggleBtn.addEventListener("click", () => this.toggleAll());
    this.copyBtn = el("button", "arb-btn", ICONS.copy);
    this.copyBtn.title = "Copy as text";
    this.copyBtn.addEventListener("click", () => this.copy());
    bar.append(this.stats, el("span", "arb-sp"), this.numBtn, this.mlBtn, this.toggleBtn, this.copyBtn);

    this.body = el("div", "arb-pnl-body");
    // wheel scrolls the list instead of zooming the canvas while it can scroll
    this.body.addEventListener("wheel", (e) => {
      const b = this.body;
      if (b.scrollHeight > b.clientHeight + 1) e.stopPropagation();
    }, { passive: true });

    this.editor = el("textarea", "arb-pnl-edit");
    this.editor.spellcheck = false;
    this.editor.placeholder = "Type data — one item per line\n\nAn empty line starts a new branch";
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

  flip(name) {
    const w = this.w(name);
    if (!w) return;
    w.value = !w.value;
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

  setData(data) {
    this.data = data;
    this.closed.clear();
    if (data.kind === "tree" && data.branches.length > AUTO_COLLAPSE) {
      data.branches.forEach((b) => this.closed.add(b.path));
    }
    this.update();
  }

  update() {
    const viewing = this.connected;
    this.root.classList.toggle("editing", !viewing);
    this.editor.style.display = viewing ? "none" : "";
    this.body.style.display = viewing ? "" : "none";
    this.numBtn.style.display = this.mlBtn.style.display = viewing ? "none" : "";
    this.numBtn.classList.toggle("on", !!this.w("parse_numbers")?.value);
    this.mlBtn.classList.toggle("on", !!this.w("multiline")?.value);
    this.toggleBtn.style.display = viewing && this.data?.kind === "tree" ? "" : "none";
    if (viewing) this.render();
    this.renderStats();
  }

  renderStats() {
    if (!this.connected) {
      const c = countText(this.editor.value, !!this.w("multiline")?.value);
      this.stats.textContent = c.items
        ? `${plural(c.branches, "branch", "branches")} · ${plural(c.items, "item", "items")}`
        : "Text input";
      return;
    }
    const d = this.data;
    if (!d || d.source !== "input") {
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
    if (!d || d.source !== "input") {
      body.appendChild(el("div", "arb-empty", "Run to inspect the input"));
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
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const view = new PanelView(this);
      this.__arborPanel = view;
      this.addDOMWidget("arbor_panel", "arbor-panel", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 140,
      });
      view.sync();
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 300), Math.max(h, 260)]);
    });

    chain(nodeType.prototype, "onConfigure", function () {
      this.__arborPanel?.sync();
    });

    chain(nodeType.prototype, "onConnectionsChange", function () {
      this.__arborPanel?.update();
    });

    chain(nodeType.prototype, "onExecuted", function (output) {
      const data = output?.arbor_panel?.[0];
      if (data) this.__arborPanel?.setData(data);
    });
  },
});
