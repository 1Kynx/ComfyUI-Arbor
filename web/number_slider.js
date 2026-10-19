/* Arbor · Number Slider — one bar, nothing else to learn.
 *
 *   ┌───────────────────────────────┐
 *   │██████████████▏      0.55      │   drag = set · click = type
 *   └───────────────────────────────┘
 *    0           step 0.05         1      click any of them to edit
 *
 * Drag maps the pointer straight to the value (Shift: 10× finer, relative).
 * Scrolling over the bar or ← / → step it. A typed value outside the range
 * widens the range instead of being clamped. value / min / max / step live in
 * the node's own hidden widgets, so they save with the workflow and live
 * Panels downstream follow while you drag.
 */

import { app } from "../../scripts/app.js";
import { injectStyle, el, isolatePointer, isolateKeys, markChanged, chain, hideWidget, t, onLocaleChange } from "./arbor_common.js";

const NODE = "Arbor_NumberSlider";
const DRAG_PX = 3;

/* decimal places a step implies (mirror of nodes_data.step_decimals) */
function stepDecimals(step) {
  if (!(step > 0)) return 6;
  const s = step.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
  return s.includes(".") ? s.split(".")[1].length : 0;
}

/* clamp + snap (mirror of nodes_data.slider_value) */
function snap(v, lo, hi, step) {
  v = Math.min(hi, Math.max(lo, v));
  if (step > 0) v = Math.min(hi, Math.max(lo, lo + Math.round((v - lo) / step) * step));
  return Number(v.toFixed(stepDecimals(step)));
}

function fmt(x, step) {
  if (step > 0) return Number(x).toFixed(stepDecimals(step));
  return String(Number(Number(x).toFixed(4)));
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
    const step = Math.max(0, Number(this.w("step")?.value ?? 0.01));
    const v = snap(Number(this.w("value")?.value ?? lo), lo, hi, step);
    return { lo, hi, step, v };
  }

  build() {
    const root = (this.root = el("div", "arb arb-num"));

    const bar = (this.bar = el("div", "arb-num-bar"));
    bar.tabIndex = 0;
    this.fill = el("div", "arb-num-fill");
    this.valueEl = el("div", "arb-num-val");
    bar.append(this.fill, this.valueEl);

    const foot = el("div", "arb-num-foot");
    this.minEl = el("span", "arb-num-field");
    this.stepEl = el("span", "arb-num-field arb-num-step");
    this.maxEl = el("span", "arb-num-field arb-num-max");
    this.minEl.addEventListener("click", () => this.edit(this.minEl, "min"));
    this.stepEl.addEventListener("click", () => this.edit(this.stepEl, "step"));
    this.maxEl.addEventListener("click", () => this.edit(this.maxEl, "max"));
    foot.append(this.minEl, this.stepEl, this.maxEl);
    root.append(bar, foot);

    // drag = set (absolute; Shift = 10x finer, relative) · click without moving = type
    let press = null;
    bar.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 || bar.querySelector("input")) return;
      bar.setPointerCapture(e.pointerId);
      press = { x: e.clientX, v: this.state.v, dragging: false };
    });
    bar.addEventListener("pointermove", (e) => {
      if (!press) return;
      if (!press.dragging && Math.abs(e.clientX - press.x) < DRAG_PX) return;
      if (!press.dragging) {
        press.dragging = true;
        bar.classList.add("drag");
      }
      if (e.shiftKey) {
        const { lo, hi } = this.state;
        const dx = e.clientX - press.x;
        this.write({ value: press.v + (dx / Math.max(1, bar.clientWidth)) * (hi - lo) / 10 });
      } else {
        this.setFromX(e.clientX);
        press.x = e.clientX;
        press.v = this.state.v;
      }
    });
    const release = (e) => {
      if (!press) return;
      const clicked = !press.dragging;
      press = null;
      bar.classList.remove("drag");
      try { bar.releasePointerCapture(e.pointerId); } catch {}
      if (clicked && e.type === "pointerup") this.edit(this.valueEl, "value");
    };
    bar.addEventListener("pointerup", release);
    bar.addEventListener("pointercancel", release);

    bar.addEventListener("wheel", (e) => {
      if (bar.querySelector("input")) return;
      e.preventDefault();
      e.stopPropagation();
      this.nudge((e.deltaY < 0 ? 1 : -1) * (e.shiftKey ? 10 : 1));
    }, { passive: false });
    bar.addEventListener("keydown", (e) => {
      if (e.target !== bar) return;
      const k = e.key;
      if (k === "ArrowRight" || k === "ArrowUp") this.nudge(e.shiftKey ? 10 : 1);
      else if (k === "ArrowLeft" || k === "ArrowDown") this.nudge(e.shiftKey ? -10 : -1);
      else if (k === "Enter") this.edit(this.valueEl, "value");
      else return;
      e.preventDefault();
      e.stopPropagation();
    });
    isolatePointer(root);
    this.render();
  }

  setFromX(x) {
    const { lo, hi } = this.state;
    const r = this.bar.getBoundingClientRect();
    const f = Math.min(1, Math.max(0, (x - r.left) / Math.max(1, r.width)));
    this.write({ value: lo + f * (hi - lo) });
  }

  nudge(steps) {
    const { v, step, lo, hi } = this.state;
    const unit = step > 0 ? step : (hi - lo) / 100 || 0.01;
    this.write({ value: v + steps * unit });
  }

  /* write into the hidden widgets, then normalise value to range and step */
  write(patch) {
    for (const [k, val] of Object.entries(patch)) {
      const w = this.w(k);
      if (w) w.value = val;
    }
    const { lo, hi, step } = this.state;
    const wmin = this.w("min"), wmax = this.w("max");
    if (wmin && wmax && Number(wmin.value) > Number(wmax.value)) [wmin.value, wmax.value] = [lo, hi];
    const wv = this.w("value");
    const v = snap(Number(wv?.value ?? lo), lo, hi, step);
    if (wv && wv.value !== v) wv.value = v;
    markChanged(this.node);
    this.render();
  }

  /* inline text field over a label; Enter / blur commits, Esc cancels */
  edit(target, name) {
    if (target.querySelector("input")) return;
    const s = this.state;
    const cur = name === "value" ? s.v : Number(this.w(name)?.value ?? 0);
    const input = el("input", "arb-num-input");
    input.type = "text";
    input.inputMode = "decimal";
    input.value = name === "value" ? fmt(cur, s.step) : String(cur);
    target.replaceChildren(input);
    target.classList.add("editing");
    input.focus();
    input.select();
    let done = false;
    const commit = (ok) => {
      if (done) return;
      done = true;
      const n = Number(input.value.trim().replace(",", "."));
      const raw = input.value.trim();
      target.classList.remove("editing");
      input.remove(); // render() only fills labels that hold no input
      if (!ok || raw === "" || !Number.isFinite(n)) return this.render();
      if (name === "value") {
        // typing outside the range widens it instead of clamping
        const patch = { value: n };
        if (n < s.lo) patch.min = n;
        if (n > s.hi) patch.max = n;
        this.write(patch);
      } else if (name === "step") {
        this.write({ step: Math.max(0, n) });
      } else {
        this.write({ [name]: n });
      }
      this.bar.focus({ preventScroll: true });
    };
    isolateKeys(input);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") commit(true);
      if (e.key === "Escape") commit(false);
    });
    input.addEventListener("blur", () => commit(true));
    input.addEventListener("pointerdown", (e) => e.stopPropagation());
  }

  /* linked to an input that only takes INT (steps, seed, width…)? The
   * server then rounds the value (nodes_data.feeds_int), so show it rounded. */
  feedsInt() {
    const g = this.node.graph;
    for (const id of this.node.outputs?.[0]?.links ?? []) {
      const l = g?.links?.get?.(id) ?? g?.links?.[id] ?? g?.getLink?.(id);
      const target = l && g.getNodeById(l.target_id);
      const parts = String(target?.inputs?.[l.target_slot]?.type ?? "").split(",");
      if (parts.includes("INT") && !parts.includes("FLOAT")) return true;
    }
    return false;
  }

  render() {
    const { lo, hi, step, v } = this.state;
    const f = hi > lo ? (v - lo) / (hi - lo) : 0;
    const asInt = this.feedsInt();
    this.bar.classList.toggle("int", asInt);
    this.bar.dataset.tag = asInt ? "INT" : "";
    this.fill.style.width = `${f * 100}%`;
    if (!this.valueEl.querySelector("input")) this.valueEl.textContent = asInt ? String(Math.round(v)) : fmt(v, step);
    if (!this.minEl.querySelector("input")) this.minEl.textContent = fmt(lo, step);
    if (!this.maxEl.querySelector("input")) this.maxEl.textContent = fmt(hi, step);
    if (!this.stepEl.querySelector("input")) {
      this.stepEl.textContent = step > 0 ? t("stepIs", { s: fmt(step, step) }) : t("stepFree");
    }
    this.bar.title = asInt ? `${t("barTip")}\n${t("intMode")}` : t("barTip");
    this.minEl.title = t("minTip");
    this.maxEl.title = t("maxTip");
    this.stepEl.title = t("stepTip");
  }

  sync() {
    for (const n of ["value", "min", "max", "step"]) hideWidget(this.w(n));
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
      const off = onLocaleChange(() => view.render());
      chain(this, "onRemoved", off);
      this.addDOMWidget("arbor_number", "arbor-number", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 58,
      });
      view.sync();
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 240), Math.max(h, 92)]);
    });

    chain(nodeType.prototype, "onConfigure", function () {
      this.__arborNumber?.sync();
    });

    chain(nodeType.prototype, "onConnectionsChange", function () {
      this.__arborNumber?.render();
    });
  },
});
