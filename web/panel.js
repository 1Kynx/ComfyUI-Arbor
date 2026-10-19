/* Arbor · Panel — a Grasshopper-style data viewer.
 *
 * Trees render as collapsible branches ({0;1} N=3) with indexed items; plain
 * values and lists render flat. Images show a thumbnail (click to open).
 */

import { app } from "../../scripts/app.js";
import { injectStyle, el, viewURL, isolatePointer, chain, ICONS } from "./arbor_common.js";

const NODE = "Arbor_Panel";
const AUTO_COLLAPSE = 24; // collapse every branch when the tree has more than this

class PanelView {
  constructor(node) {
    this.node = node;
    this.data = null;
    this.closed = new Set();
    this.build();
  }

  build() {
    const root = (this.root = el("div", "arb arb-pnl"));
    const bar = el("div", "arb-bar");
    this.stats = el("span", "arb-sub", "");
    this.toggleBtn = el("button", "arb-btn", ICONS.collapse);
    this.toggleBtn.title = "Collapse / expand all branches";
    this.toggleBtn.addEventListener("click", () => this.toggleAll());
    this.copyBtn = el("button", "arb-btn", ICONS.copy);
    this.copyBtn.title = "Copy as text";
    this.copyBtn.addEventListener("click", () => this.copy());
    bar.append(this.stats, el("span", "arb-sp"), this.toggleBtn, this.copyBtn);

    this.body = el("div", "arb-pnl-body");
    this.body.appendChild(el("div", "arb-empty", "Connect anything and run"));
    // wheel scrolls the list instead of zooming the canvas while it can scroll
    this.body.addEventListener("wheel", (e) => {
      const b = this.body;
      if (b.scrollHeight > b.clientHeight + 1) e.stopPropagation();
    }, { passive: true });

    root.append(bar, this.body);
    isolatePointer(root);
  }

  setData(data) {
    this.data = data;
    this.closed.clear();
    if (data.kind === "tree" && data.branches.length > AUTO_COLLAPSE) {
      data.branches.forEach((b) => this.closed.add(b.path));
    }
    this.render();
  }

  render() {
    const d = this.data;
    const body = this.body;
    body.replaceChildren();
    if (!d) return;
    const s = d.stats;
    const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
    this.stats.textContent = d.kind === "tree"
      ? `${plural(s.branches, "branch", "branches")} · ${plural(s.items, "item", "items")} · depth ${s.depth}`
      : d.kind === "list" ? `List · ${plural(s.items, "item", "items")}` : s.items ? "Value" : "Empty";
    this.toggleBtn.style.display = d.kind === "tree" ? "" : "none";
    this.root.classList.toggle("flat", d.kind !== "tree");

    if (!s.items && !d.branches.length) {
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
    if (s.truncated) body.appendChild(el("div", "arb-more", "Display truncated — copy to get everything"));
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
    if (!this.data) return;
    try {
      await navigator.clipboard.writeText(this.data.text);
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
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 300), Math.max(h, 260)]);
    });

    chain(nodeType.prototype, "onExecuted", function (output) {
      const data = output?.arbor_panel?.[0];
      if (data) this.__arborPanel?.setData(data);
    });
  },
});
