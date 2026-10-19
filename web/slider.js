/* Arbor · Image Slider
 *
 * Flip mode: one image at a time; drag the scrubber under the stage (or use
 *            ← →) to move through every connected image / frame.
 * Wipe mode: A (chosen from the chip) is split against B (the scrubber) by a
 *            divider that follows the pointer.
 * Images of different sizes share one stage: "Real" keeps their relative
 * scale (a 512px image looks half as big as a 1024px one), "Fit" scales each
 * one to fill the stage.
 */

import { app } from "../../scripts/app.js";
import { injectStyle, el, viewURL, isolatePointer, markChanged, chain, showMenu, ICONS, t, onLocaleChange } from "./arbor_common.js";

const NODE = "Arbor_ImageSlider";

class SliderView {
  constructor(node) {
    this.node = node;
    this.slides = [];
    this.index = 0;     // flip: shown slide; wipe: B
    this.a = 0;         // wipe: A
    this.mode = node.properties?.arbor_mode || "flip";
    this.scale = node.properties?.arbor_scale || "real";
    this.div = 0.5;     // wipe divider, fraction of stage width
    this.build();
  }

  build() {
    const root = (this.root = el("div", "arb arb-cmp"));
    root.tabIndex = 0;

    const bar = el("div", "arb-bar");
    this.seg = el("div", "arb-seg", `<button data-m="flip"></button><button data-m="wipe"></button>`);
    this.seg.addEventListener("click", (e) => {
      const m = e.target?.dataset?.m;
      if (m) this.setMode(m);
    });
    this.chipA = el("button", "arb-chip");
    this.chipA.addEventListener("click", () => this.pickA());
    this.info = el("span", "arb-sub");
    this.scaleBtn = el("button", "arb-btn");
    this.scaleBtn.addEventListener("click", () => {
      this.scale = this.scale === "real" ? "fit" : "real";
      this.node.properties.arbor_scale = this.scale;
      markChanged(this.node);
      this.render();
    });
    this.openBtn = el("button", "arb-btn", ICONS.open);
    this.openBtn.addEventListener("click", () => {
      const s = this.slides[this.index];
      if (s) window.open(viewURL(s), "_blank");
    });
    bar.append(this.seg, this.chipA, this.info, el("span", "arb-sp"), this.scaleBtn, this.openBtn);

    const stage = (this.stage = el("div", "arb-cmp-stage"));
    this.imgB = el("img");
    this.imgA = el("img");
    this.divEl = el("div", "arb-cmp-div");
    this.tagA = el("div", "arb-cmp-tag");
    this.tagB = el("div", "arb-cmp-tag");
    this.empty = el("div", "arb-empty");
    stage.append(this.imgB, this.imgA, this.divEl, this.tagA, this.tagB, this.empty);
    stage.addEventListener("pointermove", (e) => {
      if (this.mode !== "wipe") return;
      const r = stage.getBoundingClientRect();
      this.div = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      this.layout();
    });
    stage.addEventListener("dblclick", () => this.openBtn.click());

    const scrub = (this.scrub = el("div", "arb-scrub"));
    this.rail = el("div", "arb-scrub-rail");
    this.fill = el("div", "arb-scrub-fill");
    this.knob = el("div", "arb-scrub-knob");
    this.tip = el("div", "arb-scrub-tip");
    this.rail.append(this.fill);
    scrub.append(this.rail, this.knob, this.tip);
    const at = (e) => {
      const r = this.rail.getBoundingClientRect();
      const n = this.slides.length;
      const f = Math.min(1, Math.max(0, (e.clientX - r.left) / Math.max(1, r.width)));
      return { i: n > 1 ? Math.round(f * (n - 1)) : 0, x: e.clientX - scrub.getBoundingClientRect().left };
    };
    scrub.addEventListener("pointerdown", (e) => {
      if (!this.slides.length) return;
      scrub.setPointerCapture(e.pointerId);
      scrub.classList.add("drag");
      this.go(at(e).i);
      root.focus({ preventScroll: true });
    });
    scrub.addEventListener("pointermove", (e) => {
      if (!this.slides.length) return;
      const { i } = at(e);
      if (scrub.classList.contains("drag")) this.go(i);
      this.showTip(i);
    });
    const end = (e) => {
      scrub.classList.remove("drag");
      try { scrub.releasePointerCapture(e.pointerId); } catch {}
    };
    scrub.addEventListener("pointerup", end);
    scrub.addEventListener("pointercancel", end);

    root.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        this.go(this.index + (e.key === "ArrowRight" ? 1 : -1));
        e.preventDefault();
        e.stopPropagation();
      }
    });

    root.append(bar, stage, scrub);
    isolatePointer(stage);
    isolatePointer(scrub);
    isolatePointer(bar);

    new ResizeObserver(() => this.layout()).observe(stage);
    this.render();
  }

  setMode(m) {
    this.mode = m;
    this.node.properties.arbor_mode = m;
    markChanged(this.node);
    if (m === "wipe" && this.index === this.a && this.slides.length > 1) {
      this.index = (this.a + 1) % this.slides.length;
    }
    this.render();
  }

  setSlides(slides) {
    this.slides = slides || [];
    const n = this.slides.length;
    this.index = Math.min(this.index, Math.max(0, n - 1));
    this.a = Math.min(this.a, Math.max(0, n - 1));
    if (this.mode === "wipe" && n > 1 && this.index === this.a) this.index = (this.a + 1) % n;
    for (const s of this.slides) new Image().src = viewURL(s); // warm the cache for smooth scrubbing
    this.render();
  }

  go(i) {
    const n = this.slides.length;
    if (!n) return;
    i = Math.max(0, Math.min(n - 1, i));
    if (i === this.index) return;
    this.index = i;
    this.render();
  }

  pickA() {
    if (!this.slides.length) return;
    showMenu(this.chipA, this.slides.map((s, i) => ({
      label: `${s.label}  ${s.w}×${s.h}`, img: viewURL(s), on: i === this.a,
      pick: () => { this.a = i; this.render(); },
    })));
  }

  showTip(i) {
    const s = this.slides[i];
    if (!s) return;
    const n = this.slides.length;
    const r = this.rail.getBoundingClientRect();
    const pr = this.scrub.getBoundingClientRect();
    const x = r.left - pr.left + (n > 1 ? (i / (n - 1)) * r.width : r.width / 2);
    this.tip.textContent = `${i + 1}. ${s.label}`;
    this.tip.style.left = `${x}px`;
  }

  render() {
    const n = this.slides.length;
    const wipe = this.mode === "wipe";
    for (const b of this.seg.children) b.classList.toggle("on", b.dataset.m === this.mode);
    this.scaleBtn.textContent = t(this.scale === "real" ? "real" : "fit");
    this.seg.children[0].textContent = t("flip");
    this.seg.children[1].textContent = t("wipe");
    this.chipA.title = t("chooseA");
    this.scaleBtn.title = t("scaleTip");
    this.openBtn.title = t("openTip");
    this.empty.textContent = t("sliderEmpty");
    this.empty.style.display = n ? "none" : "";
    this.stage.classList.toggle("wipe", wipe);
    this.chipA.style.display = wipe && n ? "" : "none";
    this.scrub.style.visibility = n > 1 ? "" : "hidden";

    const cur = this.slides[this.index];
    if (!cur) {
      this.info.textContent = "";
      this.imgA.style.display = this.imgB.style.display = "none";
      this.divEl.style.display = this.tagA.style.display = this.tagB.style.display = "none";
      return;
    }
    this.info.textContent = `${this.index + 1} / ${n} · ${cur.label} · ${cur.w}×${cur.h}`;
    this.info.title = this.info.textContent;

    const A = this.slides[this.a];
    if (wipe) {
      this.chipA.innerHTML = `<b>A</b><span></span>`;
      this.chipA.lastChild.textContent = A.label;
      this.setSrc(this.imgA, A);
      this.setSrc(this.imgB, cur);
      this.tagA.textContent = `A · ${A.label}`;
      this.tagB.textContent = `B · ${cur.label}`;
    } else {
      this.setSrc(this.imgB, cur);
    }
    this.imgB.style.display = "";
    this.imgA.style.display = wipe ? "" : "none";
    this.divEl.style.display = this.tagA.style.display = this.tagB.style.display = wipe ? "" : "none";

    // scrubber
    this.rail.querySelectorAll(".arb-scrub-tick").forEach((t) => t.remove());
    const pos = (i) => (n > 1 ? (i / (n - 1)) * 100 : 50);
    if (n <= 48) {
      for (let i = 0; i < n; i++) {
        const t = el("div", "arb-scrub-tick" + (i <= this.index ? " done" : "") + (wipe && i === this.a ? " pin" : ""));
        t.style.left = `${pos(i)}%`;
        this.rail.appendChild(t);
      }
    }
    this.fill.style.width = `${pos(this.index)}%`;
    this.knob.style.left = `calc(8px + (100% - 16px) * ${pos(this.index) / 100})`;
    this.showTip(this.index);
    this.layout();
  }

  setSrc(img, s) {
    const url = viewURL(s);
    if (img.dataset.src !== url) {
      img.dataset.src = url;
      img.src = url;
    }
  }

  /* place the image(s) inside the stage */
  layout() {
    const n = this.slides.length;
    if (!n) return;
    const W = this.stage.clientWidth;
    const H = this.stage.clientHeight;
    if (!W || !H) return;
    const wipe = this.mode === "wipe";
    const shown = wipe ? [this.slides[this.a], this.slides[this.index]] : [this.slides[this.index]];
    // "real": one shared scale so relative sizes survive; "fit": per image
    const ref = this.slides;
    const uw = Math.max(...ref.map((s) => s.w));
    const uh = Math.max(...ref.map((s) => s.h));
    const shared = Math.min(W / uw, H / uh);

    const boxes = shown.map((s) => {
      const k = this.scale === "real" ? shared : Math.min(W / s.w, H / s.h);
      const w = s.w * k, h = s.h * k;
      return { x: (W - w) / 2, y: (H - h) / 2, w, h };
    });
    const place = (img, b) => {
      img.style.left = `${b.x}px`;
      img.style.top = `${b.y}px`;
      img.style.width = `${b.w}px`;
      img.style.height = `${b.h}px`;
    };
    if (!wipe) {
      place(this.imgB, boxes[0]);
      this.imgB.style.clipPath = "";
      return;
    }
    const [ba, bb] = boxes;
    place(this.imgA, ba);
    place(this.imgB, bb);
    const dx = this.div * W;
    const cut = Math.min(ba.w, Math.max(0, ba.x + ba.w - dx));
    this.imgA.style.clipPath = `inset(0 ${cut}px 0 0)`;
    const cutB = Math.min(bb.w, Math.max(0, dx - bb.x));
    this.imgB.style.clipPath = `inset(0 0 0 ${cutB}px)`;
    this.divEl.style.left = `${dx}px`;
    this.tagA.style.left = "6px";
    this.tagB.style.right = "6px";
    this.tagA.style.opacity = this.div > 0.15 ? 1 : 0;
    this.tagB.style.opacity = this.div < 0.85 ? 1 : 0;
  }
}

app.registerExtension({
  name: "Arbor.ImageSlider",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      this.properties ||= {};
      const view = new SliderView(this);
      const off = onLocaleChange(() => view.render());
      chain(this, "onRemoved", off);
      this.__arborSlider = view;
      this.addDOMWidget("arbor_slider", "arbor-slider", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 220,
      });
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 380), Math.max(h, 420)]);
    });

    chain(nodeType.prototype, "onExecuted", function (output) {
      const data = output?.arbor_slider?.[0];
      if (data) this.__arborSlider?.setSlides(data.slides);
    });
  },
});
