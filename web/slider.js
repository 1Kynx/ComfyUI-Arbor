/* Arbor · Compare Viewer (node id Arbor_ImageSlider, its first name)
 *
 * Slides are images, videos or audio clips.
 * Flip mode: one slide at a time; drag the scrubber under the stage (or use
 *            ← →) to move through every connected slide.
 * Wipe mode: A (chosen from the chip) against B (the scrubber). Two pictures or
 *            videos are split by a divider that follows the pointer; when either
 *            is audio they are stacked, A on top, and you hear the half under
 *            the pointer.
 * Videos and audio share one clock (play / seek / loop under the stage) and keep
 * their place when you switch slides, so an A/B listen stays on the same moment.
 * Pictures of different sizes share one stage: "Real" keeps their relative
 * scale (a 512px image looks half as big as a 1024px one), "Fit" scales each
 * one to fill the stage.
 */

import { app } from "../../scripts/app.js";
import { injectStyle, el, viewURL, isolatePointer, markChanged, chain, showMenu, ICONS, t, onLocaleChange } from "./arbor_common.js";

const NODE = "Arbor_ImageSlider";
const TIMED = new Set(["video", "audio"]);
const KIND_MARK = { image: "", video: "▶ ", audio: "♪ " };

function fmtTime(s) {
  const tenths = Math.round(Math.max(0, s || 0) * 10);
  const m = Math.floor(tenths / 600);
  return `${m}:${((tenths - m * 600) / 10).toFixed(1).padStart(4, "0")}`;
}

/* One picture / video / waveform on the stage (A or B).
   A video isn't put on the page: its frames are drawn into a canvas. A <video> on screen is scaled and
   post-processed by the browser and graphics driver in ways that can differ between two players (one side
   sharpened or blocky); a canvas shows the decoded pixels, the same way for A and B. */
class Layer {
  constructor(stage, onMeta) {
    this.img = el("img");
    this.video = el("video");
    this.video.playsInline = true;
    this.video.preload = "auto";
    this.video.muted = true;
    this.screen = el("canvas");
    for (const ev of ["loadeddata", "seeked"]) this.video.addEventListener(ev, () => this.paint());
    this.audio = el("audio");
    this.audio.preload = "auto";
    this.wave = el("canvas", "arb-cmp-wave");
    for (const m of [this.video, this.audio]) m.addEventListener("loadedmetadata", onMeta);
    stage.append(this.img, this.screen, this.wave);
    this.slide = null;
  }

  get kind() { return this.slide?.kind || null; }
  get media() { return this.kind === "video" ? this.video : this.kind === "audio" ? this.audio : null; }
  get elm() { return this.kind === "video" ? this.screen : this.kind === "audio" ? this.wave : this.img; }
  get dur() { return this.slide?.dur || this.media?.duration || 0; }

  show(slide) {
    const before = this.media;
    this.slide = slide || null;
    if (before && before !== this.media) before.pause();
    this.img.style.display = this.kind === "image" ? "" : "none";
    this.screen.style.display = this.kind === "video" ? "" : "none";
    this.wave.style.display = this.kind === "audio" ? "" : "none";
    if (!slide) return;
    const target = slide.kind === "image" ? this.img : this.media;
    const url = viewURL(slide);
    if (target.dataset.src !== url) {
      target.dataset.src = url;
      target.src = url;
      this.tries = 0;
      if (target === this.video) this.screen.width = 0;  // no frame of the previous clip
    }
  }

  paint() {
    const v = this.video, c = this.screen;
    if (this.kind !== "video" || v.readyState < 2 || !v.videoWidth) return;
    if (c.width !== v.videoWidth || c.height !== v.videoHeight) {
      c.width = v.videoWidth;
      c.height = v.videoHeight;
    }
    c.getContext("2d").drawImage(v, 0, 0);
  }

  stop() {
    this.video.pause();
    this.audio.pause();
  }

  place(b) {
    const e = this.elm;
    e.style.left = `${b.x}px`;
    e.style.top = `${b.y}px`;
    e.style.width = `${b.w}px`;
    e.style.height = `${b.h}px`;
    e.style.clipPath = "";
    this.box = b;
  }
}

class SliderView {
  constructor(node) {
    this.node = node;
    this.all = [];      // every slide the node sent
    this.slides = [];   // the ones of the chosen group
    this.index = 0;     // flip: shown slide; wipe: B
    this.a = 0;         // wipe: A
    this.readProps();
    this.muted = false;
    this.div = 0.5;     // wipe divider, fraction of stage width
    this.top = false;   // stacked: pointer over the top half (A)
    this.time = 0;      // shared clock, seconds
    this.playing = false;
    this.timer = 0;   // clock tick while playing (a timer, not rAF: it keeps running when the canvas isn't painted)
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
    this.chipG = el("button", "arb-chip");
    this.chipG.addEventListener("click", () => this.pickGroup());
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
    bar.append(this.seg, this.chipG, this.chipA, this.info, el("span", "arb-sp"), this.scaleBtn, this.openBtn);

    const stage = (this.stage = el("div", "arb-cmp-stage"));
    const meta = () => { this.sync(true); this.layout(); };
    this.B = new Layer(stage, meta);
    this.A = new Layer(stage, meta);
    this.divEl = el("div", "arb-cmp-div");
    this.tagA = el("div", "arb-cmp-tag");
    this.tagB = el("div", "arb-cmp-tag");
    this.empty = el("div", "arb-empty");
    stage.append(this.divEl, this.tagA, this.tagB, this.empty);
    stage.addEventListener("pointermove", (e) => {
      if (this.mode !== "wipe") return;
      const r = stage.getBoundingClientRect();
      if (this.stacked()) {
        const top = e.clientY - r.top < r.height / 2;
        if (top !== this.top) {
          this.top = top;
          this.sync(false);
          this.tags();
        }
        return;
      }
      this.div = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      this.layout();
      this.sync(false);
    });
    stage.addEventListener("pointerdown", (e) => {
      // click a waveform to seek
      const r = stage.getBoundingClientRect();
      const layer = this.mode === "wipe" && this.stacked() ? (e.clientY - r.top < r.height / 2 ? this.A : this.B)
        : this.mode === "flip" ? this.B : null;
      if (layer?.kind !== "audio" || !layer.box) return;
      const f = (e.clientX - r.left - layer.box.x) / Math.max(1, layer.box.w);
      this.seek(Math.min(1, Math.max(0, f)) * this.length());
    });
    stage.addEventListener("dblclick", () => this.openBtn.click());

    // transport: shared clock for video and audio
    const tp = (this.tp = el("div", "arb-tp"));
    this.playBtn = el("button", "arb-btn");
    this.playBtn.addEventListener("click", () => this.toggle());
    this.timeEl = el("span", "arb-tp-time");
    this.trail = el("div", "arb-tp-rail", `<div class="arb-tp-line"><div class="arb-tp-fill"></div></div><div class="arb-tp-knob"></div>`);
    this.loopBtn = el("button", "arb-btn", ICONS.loop);
    this.loopBtn.addEventListener("click", () => {
      this.loop = !this.loop;
      this.node.properties.arbor_loop = this.loop;
      markChanged(this.node);
      this.transport();
    });
    this.muteBtn = el("button", "arb-btn");
    this.muteBtn.addEventListener("click", () => {
      this.muted = !this.muted;
      this.sync(false);
      this.transport();
    });
    tp.append(this.playBtn, this.trail, this.timeEl, this.loopBtn, this.muteBtn);
    const seekAt = (e) => {
      const r = this.trail.getBoundingClientRect();
      this.seek(Math.min(1, Math.max(0, (e.clientX - r.left) / Math.max(1, r.width))) * this.length());
    };
    this.trail.addEventListener("pointerdown", (e) => {
      this.trail.setPointerCapture(e.pointerId);
      this.trail.classList.add("drag");
      seekAt(e);
    });
    this.trail.addEventListener("pointermove", (e) => {
      if (this.trail.classList.contains("drag")) seekAt(e);
    });
    const endSeek = (e) => {
      this.trail.classList.remove("drag");
      try { this.trail.releasePointerCapture(e.pointerId); } catch {}
    };
    this.trail.addEventListener("pointerup", endSeek);
    this.trail.addEventListener("pointercancel", endSeek);

    // slide scrubber
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
      return n > 1 ? Math.round(f * (n - 1)) : 0;
    };
    scrub.addEventListener("pointerdown", (e) => {
      if (!this.slides.length) return;
      scrub.setPointerCapture(e.pointerId);
      scrub.classList.add("drag");
      this.go(at(e));
      root.focus({ preventScroll: true });
    });
    scrub.addEventListener("pointermove", (e) => {
      if (!this.slides.length) return;
      const i = at(e);
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
      } else if (e.key === " " && this.timed().length) {
        this.toggle();
      } else {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
    });

    root.append(bar, stage, tp, scrub);
    for (const part of [stage, tp, scrub, bar]) isolatePointer(part);

    new ResizeObserver(() => this.layout()).observe(stage);
    this.render();
  }

  // the node's saved settings; a loaded workflow sets them after the node (and this view) is created
  readProps() {
    const p = this.node.properties || {};
    this.group = p.arbor_group || "";  // "" = all
    this.mode = p.arbor_mode || "flip";
    this.scale = p.arbor_scale || "real";
    this.loop = p.arbor_loop ?? true;
  }

  destroy() {
    clearInterval(this.timer);
    this.playing = false;
    this.A.stop();
    this.B.stop();
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
    this.all = slides || [];
    this.showGroup(this.group);
  }

  groups() {
    return [...new Set(this.all.map((s) => s.group).filter((g) => g != null))];
  }

  /* a slide without a group (a plain list next to a tree) belongs to every group */
  inGroup(s, g) {
    return !g || s.group == null || s.group === g;
  }

  /* show one group ("" = all); a group the new slides don't have falls back to all */
  showGroup(g) {
    if (g && !this.groups().includes(g)) g = "";
    if (g !== this.group) {
      this.group = g;
      this.node.properties.arbor_group = g;
      markChanged(this.node);
      this.index = this.a = 0;
    }
    this.slides = this.all.filter((s) => this.inGroup(s, g));
    const n = this.slides.length;
    this.index = Math.min(this.index, Math.max(0, n - 1));
    this.a = Math.min(this.a, Math.max(0, n - 1));
    if (this.mode === "wipe" && n > 1 && this.index === this.a) this.index = (this.a + 1) % n;
    for (const s of this.slides) if (s.kind === "image" || !s.kind) new Image().src = viewURL(s); // smooth scrubbing
    this.pause();
    this.time = 0;
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

  pickGroup() {
    const groups = this.groups();
    if (groups.length < 2) return;
    const first = (g) => this.all.find((s) => (!g || s.group === g) && (s.kind === "image" || !s.kind));
    const count = (g) => this.all.filter((s) => this.inGroup(s, g)).length;
    showMenu(this.chipG, ["", ...groups].map((g) => ({
      label: `${g || t("allGroups")}  (${count(g)})`,
      img: first(g) ? viewURL(first(g)) : null, on: g === this.group,
      pick: () => this.showGroup(g),
    })));
  }

  pickA() {
    if (!this.slides.length) return;
    showMenu(this.chipA, this.slides.map((s, i) => ({
      label: `${KIND_MARK[s.kind] || ""}${s.label}  ${this.describe(s)}`,
      img: s.kind === "image" || !s.kind ? viewURL(s) : null, on: i === this.a,
      pick: () => { this.a = i; this.render(); },
    })));
  }

  describe(s) {
    if (s.kind === "audio") return fmtTime(s.dur);
    const size = s.w && s.h ? `${s.w}×${s.h}` : "";
    return s.kind === "video" ? [size, fmtTime(s.dur)].filter(Boolean).join(" · ") : size;
  }

  showTip(i) {
    const s = this.slides[i];
    if (!s) return;
    const n = this.slides.length;
    const r = this.rail.getBoundingClientRect();
    const pr = this.scrub.getBoundingClientRect();
    const x = r.left - pr.left + (n > 1 ? (i / (n - 1)) * r.width : r.width / 2);
    this.tip.textContent = `${i + 1}. ${KIND_MARK[s.kind] || ""}${s.label}`;
    this.tip.style.left = `${x}px`;
  }

  /* ---------------------------------------------------------- the clock */

  layers() {
    return this.mode === "wipe" ? [this.A, this.B] : [this.B];
  }

  timed() {
    return this.layers().filter((l) => TIMED.has(l.kind));
  }

  length() {
    return Math.max(0, ...this.timed().map((l) => l.dur));
  }

  /* the layer you hear: the one shown, the larger side of a wipe, the half under the pointer */
  audible() {
    if (this.mode !== "wipe") return this.B;
    if (this.stacked()) return this.top ? this.A : this.B;
    return this.div > 0.5 ? this.A : this.B;
  }

  toggle() {
    this.playing ? this.pause() : this.play();
  }

  play() {
    if (!this.timed().length) return;
    if (this.time >= this.length() - 0.05) this.time = 0;
    this.playing = true;
    this.last = performance.now();
    this.sync(true);
    clearInterval(this.timer);
    this.timer = setInterval(() => this.tick(), 40);
    const frame = () => {  // the canvases follow the players at the display's rate
      if (!this.playing) return;
      this.A.paint();
      this.B.paint();
      this.raf = requestAnimationFrame(frame);
    };
    cancelAnimationFrame(this.raf);
    this.raf = requestAnimationFrame(frame);
    this.transport();
  }

  pause() {
    this.playing = false;
    clearInterval(this.timer);
    this.A.stop();
    this.B.stop();
    this.sync(true);  // each player stops wherever its decoder was: put both on the clock's frame
    this.transport();
  }

  seek(s) {
    this.time = Math.max(0, s);
    this.sync(true);
    this.transport();
  }

  tick() {
    if (!this.playing) return;
    const now = performance.now();
    const L = this.length();
    // follow the longest clip while it plays; count real time while it loads or has ended
    const lead = this.timed().reduce((a, l) => (!a || l.dur > a.dur ? l : a), null);
    const m = lead?.media;
    if (m && !m.paused && m.readyState >= 2 && m.currentTime < lead.dur - 0.05) this.time = m.currentTime;
    else this.time += (now - this.last) / 1000;
    this.last = now;
    if (!L) {
      this.pause();
      return;
    }
    if (this.time >= L) {
      if (this.loop) {
        this.time = 0;
        this.sync(true);
      } else {
        this.time = L;
        this.pause();
        return;
      }
    }
    this.sync(false);
    this.transport();
  }

  /* put every visible video / audio at the clock's time, playing or held */
  sync(force) {
    const loud = this.audible();
    for (const layer of [this.A, this.B]) {
      const m = layer.media;
      const shown = this.layers().includes(layer);
      if (!m) continue;
      if (!shown) {
        m.pause();
        continue;
      }
      const dur = layer.dur;
      const at = dur ? Math.min(this.time, Math.max(0, dur - 0.04)) : this.time;
      const drift = m.currentTime - at;
      // held: on the clock's frame. Playing: seek only when far off (a seek stutters); a small drift is
      // taken up by running that player a little faster or slower until it is back on the clock.
      if (m.readyState >= 1 && (force || Math.abs(drift) > (this.playing ? 0.15 : 0.02))) {
        try { m.currentTime = at; } catch {}
        m.playbackRate = 1;
      } else if (this.playing) {
        m.playbackRate = Math.abs(drift) < 0.02 ? 1 : drift > 0 ? 0.9 : 1.1;
      }
      m.muted = this.muted || layer !== loud;
      const run = this.playing && (!dur || this.time < dur - 0.04);
      if (run && m.paused) m.play().catch(() => {});
      else if (!run && !m.paused) m.pause();
    }
    if (force) this.watch();
    this.drawWaves();
  }

  // A player can stick (seen with hardware decode in Edge: it never loads, or stays on an old frame and
  // ignores seeks until its clip is picked again). Reload one that hasn't reached the clock, and look again.
  watch() {
    clearTimeout(this.dog);
    this.dog = setTimeout(() => {
      if (this.playing) return;
      let again = false;
      for (const layer of this.layers()) {
        const m = layer.media;
        if (!m || !m.getAttribute("src")) continue;
        const dur = layer.dur;
        const at = dur ? Math.min(this.time, Math.max(0, dur - 0.04)) : this.time;
        if (m.readyState >= 2 && !m.seeking && Math.abs(m.currentTime - at) < 0.05) layer.tries = 0;
        else if ((layer.tries = (layer.tries || 0) + 1) <= 3) {
          m.load();  // its loadedmetadata seeks it again
          again = true;
        }
      }
      if (again) this.watch();
    }, 1500);
  }

  transport() {
    const timed = this.timed().length > 0;
    this.tp.style.display = timed ? "" : "none";
    if (!timed) return;
    const L = this.length();
    // Swap an icon only when it changes. This runs on every clock tick while playing, and replacing the
    // button's contents between pointerdown and pointerup drops the click — pause would then miss.
    const icon = (btn, html) => {
      if (btn.dataset.icon !== html) {
        btn.dataset.icon = html;
        btn.innerHTML = html;
      }
    };
    icon(this.playBtn, this.playing ? ICONS.pause : ICONS.play);
    this.playBtn.title = t(this.playing ? "pauseTip" : "playTip");
    this.loopBtn.classList.toggle("on", this.loop);
    this.loopBtn.title = t("loopTip");
    icon(this.muteBtn, this.muted ? ICONS.muted : ICONS.sound);
    this.muteBtn.title = t("muteTip");
    this.timeEl.textContent = `${fmtTime(Math.min(this.time, L))} / ${fmtTime(L)}`;
    const f = L ? Math.min(1, this.time / L) : 0;
    this.trail.querySelector(".arb-tp-fill").style.width = `${f * 100}%`;
    this.trail.querySelector(".arb-tp-knob").style.left = `${f * 100}%`;
    if (!this.playing) this.drawWaves();
  }

  drawWaves() {
    for (const layer of this.layers()) {
      if (layer.kind !== "audio" || !layer.box) continue;
      const c = layer.wave;
      const { w, h } = layer.box;
      const dpr = window.devicePixelRatio || 1;
      if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
        c.width = Math.round(w * dpr);
        c.height = Math.round(h * dpr);
      }
      const g = c.getContext("2d");
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, h);
      const css = getComputedStyle(this.root);
      const accent = css.getPropertyValue("--arb-accent").trim() || "#5fbf9a";
      const rest = css.getPropertyValue("--arb-sub").trim() || "#8b8b95";
      const peaks = layer.slide.peaks?.length ? layer.slide.peaks : [0];
      const dur = layer.dur || 1;
      const played = Math.min(1, this.time / dur) * w;
      const n = peaks.length;
      const bw = w / n;
      const mid = h / 2;
      for (let i = 0; i < n; i++) {
        const x = i * bw;
        const a = Math.max(1, peaks[i] * (mid - 6));
        g.fillStyle = x < played ? accent : rest;
        g.fillRect(x, mid - a, Math.max(1, bw - (bw > 3 ? 1 : 0)), a * 2);
      }
      g.fillStyle = css.getPropertyValue("--arb-fg").trim() || "#fff";
      g.fillRect(Math.min(w - 1.5, played), 0, 1.5, h);
    }
  }

  /* ---------------------------------------------------------- drawing */

  stacked() {
    return this.mode === "wipe" && (this.A.kind === "audio" || this.B.kind === "audio");
  }

  tags() {
    const loud = this.timed().length ? this.audible() : null;
    const mark = (layer) => (layer === loud && !this.muted ? "♪ " : "");
    if (this.mode === "wipe" && this.A.slide && this.B.slide) {
      this.tagA.textContent = `${mark(this.A)}A · ${this.A.slide.label}`;
      this.tagB.textContent = `${mark(this.B)}B · ${this.B.slide.label}`;
    }
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
    this.chipA.style.display = wipe && n ? "" : "none";
    const grouped = this.groups().length > 1;
    this.chipG.style.display = grouped ? "" : "none";
    if (grouped) {
      this.chipG.title = t("chooseGroup");
      this.chipG.innerHTML = `<span></span>`;
      this.chipG.firstChild.textContent = `${this.group || t("allGroups")} ▾`;
    }
    this.scrub.style.visibility = n > 1 ? "" : "hidden";

    const cur = this.slides[this.index];
    if (!cur) {
      this.info.textContent = "";
      this.A.show(null);
      this.B.show(null);
      this.divEl.style.display = this.tagA.style.display = this.tagB.style.display = "none";
      this.transport();
      return;
    }
    this.info.textContent = `${this.index + 1} / ${n} · ${cur.label} · ${this.describe(cur)}`;
    this.info.title = this.info.textContent;

    const A = this.slides[this.a];
    this.B.show(cur);
    this.A.show(wipe ? A : null);
    if (wipe) {
      this.chipA.innerHTML = `<b>A</b><span></span>`;
      this.chipA.lastChild.textContent = `${KIND_MARK[A.kind] || ""}${A.label}`;
    }
    const stacked = this.stacked();
    this.stage.classList.toggle("wipe", wipe && !stacked);
    this.divEl.classList.toggle("h", stacked);
    this.divEl.style.display = this.tagA.style.display = this.tagB.style.display = wipe ? "" : "none";
    this.tags();

    // scrubber
    this.rail.querySelectorAll(".arb-scrub-tick").forEach((tk) => tk.remove());
    const pos = (i) => (n > 1 ? (i / (n - 1)) * 100 : 50);
    if (n <= 48) {
      for (let i = 0; i < n; i++) {
        const tk = el("div", "arb-scrub-tick" + (i <= this.index ? " done" : "") + (wipe && i === this.a ? " pin" : ""));
        tk.style.left = `${pos(i)}%`;
        this.rail.appendChild(tk);
      }
    }
    this.fill.style.width = `${pos(this.index)}%`;
    this.knob.style.left = `calc(8px + (100% - 16px) * ${pos(this.index) / 100})`;
    this.showTip(this.index);
    this.layout();
    this.sync(true);
    this.transport();
  }

  /* place the slide(s) inside the stage */
  layout() {
    if (!this.slides.length) return;
    const W = this.stage.clientWidth;
    const H = this.stage.clientHeight;
    if (!W || !H) return;
    const wipe = this.mode === "wipe";
    // "real": one shared scale so relative sizes survive; "fit": per picture
    const pics = this.slides.filter((s) => s.kind !== "audio" && s.w && s.h);
    const uw = Math.max(1, ...pics.map((s) => s.w));
    const uh = Math.max(1, ...pics.map((s) => s.h));

    const box = (layer, x0, y0, w0, h0) => {
      const s = layer.slide;
      if (s.kind === "audio") return { x: x0 + 8, y: y0 + 8, w: Math.max(1, w0 - 16), h: Math.max(1, h0 - 16) };
      const sw = s.w || layer.video.videoWidth || layer.img.naturalWidth || w0;
      const sh = s.h || layer.video.videoHeight || layer.img.naturalHeight || h0;
      const k = this.scale === "real" ? Math.min(w0 / uw, h0 / uh) : Math.min(w0 / sw, h0 / sh);
      const w = sw * k, h = sh * k;
      return { x: x0 + (w0 - w) / 2, y: y0 + (h0 - h) / 2, w, h };
    };

    if (!wipe) {
      this.B.place(box(this.B, 0, 0, W, H));
      this.drawWaves();
      return;
    }
    if (this.stacked()) {
      this.A.place(box(this.A, 0, 0, W, H / 2));
      this.B.place(box(this.B, 0, H / 2, W, H / 2));
      this.tagA.style.left = this.tagB.style.left = "6px";
      this.tagA.style.right = this.tagB.style.right = "";
      this.tagA.style.top = "6px";
      this.tagB.style.top = `${H / 2 + 6}px`;
      this.tagA.style.opacity = this.tagB.style.opacity = 1;
      this.divEl.style.left = "";
      this.drawWaves();
      return;
    }
    const ba = box(this.A, 0, 0, W, H);
    const bb = box(this.B, 0, 0, W, H);
    this.A.place(ba);
    this.B.place(bb);
    const dx = this.div * W;
    const cut = Math.min(ba.w, Math.max(0, ba.x + ba.w - dx));
    this.A.elm.style.clipPath = `inset(0 ${cut}px 0 0)`;
    const cutB = Math.min(bb.w, Math.max(0, dx - bb.x));
    this.B.elm.style.clipPath = `inset(0 0 0 ${cutB}px)`;
    this.divEl.style.left = `${dx}px`;
    this.tagA.style.left = "6px";
    this.tagA.style.right = "";
    this.tagB.style.right = "6px";
    this.tagB.style.left = "";
    this.tagA.style.top = this.tagB.style.top = "6px";
    this.tagA.style.opacity = this.div > 0.15 ? 1 : 0;
    this.tagB.style.opacity = this.div < 0.85 ? 1 : 0;
    this.tags();
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
      chain(this, "onRemoved", () => { off(); view.destroy(); });
      this.__arborSlider = view;
      this.addDOMWidget("arbor_slider", "arbor-slider", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 240,
      });
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 380), Math.max(h, 440)]);
    });

    chain(nodeType.prototype, "onConfigure", function () {
      const view = this.__arborSlider;
      if (!view) return;
      view.readProps();
      view.render();
    });

    chain(nodeType.prototype, "onExecuted", function (output) {
      const data = output?.arbor_slider?.[0];
      if (data) this.__arborSlider?.setSlides(data.slides);
    });
  },
});
