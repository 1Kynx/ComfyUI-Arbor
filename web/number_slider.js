/* Arbor · Number Slider — a Grasshopper-style number slider.
 *
 *   0.50                         step 0.01
 *   0 ━━━━━━━━━━●─────────────── 1
 *
 * Drag the track (hold Shift for fine control), scroll over it, or use
 * ← → when focused. Double-click the value to type it; click min / max to
 * edit the range; click the step chip to change precision. The four values
 * live in the node's own hidden widgets, so they save with the workflow and
 * downstream live Panels update while you drag.
 */

import { app } from "../../scripts/app.js";
import { injectStyle, el, isolatePointer, isolateKeys, markChanged, chain } from "./arbor_common.js";

const NODE = "Arbor_NumberSlider";
const MAX_DECIMALS = 4;

function hideWidget(w) {
  if (!w) return;
  w.hidden = true;
  w.options ||= {};
  w.options.hidden = true;
}

class SliderView {
  constructor(node) {
    this.node = node;
    this.build();
  }

  w(name) {
    return this.node.widgets?.find((w) => w.name === name);
  }

  get state() {
    let lo = Number(this.w("min")?.value ?? 0);
    let hi = Number(this.w("max")?.value ?? 1);
    if (lo > hi) [lo, hi] = [hi, lo];
    const d = Math.max(0, Math.min(MAX_DECIMALS, Math.round(Number(this.w("decimals")?.value ?? 2))));
    const v = Math.min(hi, Math.max(lo, Number(this.w("value")?.value ?? lo)));
    return { lo, hi, d, v };
  }

  build() {
    const root = (this.root = el("div", "arb arb-num"));
    root.tabIndex = 0;

    const top = el("div", "arb-num-top");
    this.valueEl = el("div", "arb-num-val");
    this.valueEl.title = "Double-click to type a value";
    this.valueEl.addEventListener("dblclick", () => this.editField(this.valueEl, "value"));
    this.stepBtn = el("button", "arb-btn arb-num-step");
    this.stepBtn.title = "Precision — click to change";
    this.stepBtn.addEventListener("click", () => {
      const { d } = this.state;
      this.write({ decimals: (d + 1) % (MAX_DECIMALS + 1) });
    });
    top.append(this.valueEl, el("span", "arb-sp"), this.stepBtn);

    const row = el("div", "arb-num-row");
    this.minEl = el("span", "arb-num-end");
    this.minEl.title = "Click to set the minimum";
    this.minEl.addEventListener("click", () => this.editField(this.minEl, "min"));
    this.maxEl = el("span", "arb-num-end");
    this.maxEl.title = "Click to set the maximum";
    this.maxEl.addEventListener("click", () => this.editField(this.maxEl, "max"));
    this.track = el("div", "arb-num-track");
    this.fill = el("div", "arb-num-fill");
    this.knob = el("div", "arb-num-knob");
    this.track.append(this.fill, this.knob);
    row.append(this.minEl, this.track, this.maxEl);
    root.append(top, row);

    // drag: absolute by default, relative and 10x finer with Shift
    let drag = null;
    this.track.addEventListener("pointerdown", (e) => {
      this.track.setPointerCapture(e.pointerId);
      this.track.classList.add("drag");
      drag = { x: e.clientX, v: this.state.v };
      if (!e.shiftKey) this.setFromX(e.clientX);
      root.focus({ preventScroll: true });
    });
    this.track.addEventListener("pointermove", (e) => {
      if (!drag) return;
      if (e.shiftKey) {
        const { lo, hi } = this.state;
        const r = this.track.getBoundingClientRect();
        const dv = ((e.clientX - drag.x) / Math.max(1, r.width)) * (hi - lo) / 10;
        this.write({ value: drag.v + dv });
      } else {
        this.setFromX(e.clientX);
        drag = { x: e.clientX, v: this.state.v };
      }
    });
    const end = (e) => {
      drag = null;
      this.track.classList.remove("drag");
      try { this.track.releasePointerCapture(e.pointerId); } catch {}
    };
    this.track.addEventListener("pointerup", end);
    this.track.addEventListener("pointercancel", end);
    this.track.addEventListener("wheel", (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.nudge((e.deltaY < 0 ? 1 : -1) * (e.shiftKey ? 10 : 1));
    }, { passive: false });
    root.addEventListener("keydown", (e) => {
      if (e.target !== root) return;
      if (e.key === "ArrowRight" || e.key === "ArrowUp") this.nudge(e.shiftKey ? 10 : 1);
      else if (e.key === "ArrowLeft" || e.key === "ArrowDown") this.nudge(e.shiftKey ? -10 : -1);
      else return;
      e.preventDefault();
      e.stopPropagation();
    });
    isolatePointer(root);
  }

  setFromX(x) {
    const { lo, hi } = this.state;
    const r = this.track.getBoundingClientRect();
    const f = Math.min(1, Math.max(0, (x - r.left) / Math.max(1, r.width)));
    this.write({ value: lo + f * (hi - lo) });
  }

  nudge(steps) {
    const { v, d } = this.state;
    this.write({ value: v + steps * Math.pow(10, -d) });
  }

  /* write into the hidden widgets, normalising value to range and precision */
  write(patch) {
    for (const [k, val] of Object.entries(patch)) {
      const w = this.w(k);
      if (w) w.value = val;
    }
    const { lo, hi, d } = this.state;
    const raw = Number(this.w("value")?.value ?? lo);
    const v = Number(Math.min(hi, Math.max(lo, raw)).toFixed(d));
    const wv = this.w("value");
    if (wv && wv.value !== v) wv.value = v;
    markChanged(this.node);
    this.render();
  }

  editField(target, name) {
    if (target.querySelector("input")) return;
    const { d } = this.state;
    const cur = Number(this.w(name)?.value ?? 0);
    const input = el("input", "arb-num-input");
    input.type = "text";
    input.value = name === "value" ? cur.toFixed(d) : String(cur);
    target.replaceChildren(input);
    input.focus();
    input.select();
    let done = false;
    const commit = (ok) => {
      if (done) return;
      done = true;
      const n = Number(input.value.trim());
      if (ok && input.value.trim() !== "" && Number.isFinite(n)) this.write({ [name]: n });
      else this.render();
    };
    isolateKeys(input);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") commit(true);
      if (e.key === "Escape") commit(false);
    });
    input.addEventListener("blur", () => commit(true));
  }

  render() {
    const { lo, hi, d, v } = this.state;
    const fmt = (x) => Number(x).toFixed(d);
    if (!this.valueEl.querySelector("input")) this.valueEl.textContent = fmt(v);
    if (!this.minEl.querySelector("input")) this.minEl.textContent = fmt(lo);
    if (!this.maxEl.querySelector("input")) this.maxEl.textContent = fmt(hi);
    this.stepBtn.textContent = d ? `step ${Math.pow(10, -d).toFixed(d)}` : "step 1";
    const f = hi > lo ? (v - lo) / (hi - lo) : 0;
    this.fill.style.width = `${f * 100}%`;
    this.knob.style.left = `${f * 100}%`;
  }

  sync() {
    for (const n of ["value", "min", "max", "decimals"]) hideWidget(this.w(n));
    this.render();
  }
}

app.registerExtension({
  name: "Arbor.NumberSlider",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const view = new SliderView(this);
      this.__arborNumber = view;
      this.addDOMWidget("arbor_number", "arbor-number", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 64,
      });
      view.sync();
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 260), Math.max(h, 110)]);
    });

    chain(nodeType.prototype, "onConfigure", function () {
      this.__arborNumber?.sync();
    });
  },
});
