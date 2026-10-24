/* Arbor · Load Media
 *
 * The node keeps its file list as text in the hidden `files` widget, the Panel's
 * way: `# name` starts a named group, an empty line a new group, every other
 * line is a file (relative to `folder`, or absolute).
 * List view: groups of thumbnails — rename a group, drag files to reorder or
 * move them between groups, × to remove. Text view: edit the list directly.
 * Browse…: pick files, or a whole folder (subfolders become groups), from disk
 * (media_browser.js); files are used where they are.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { injectStyle, el, isolatePointer, isolateKeys, markChanged, chain, hideWidget, t, tn, onLocaleChange } from "./arbor_common.js";
import { openMediaBrowser } from "./media_browser.js";

const NODE = "Arbor_LoadMedia";
const KIND_EXT = {
  image: [".png", ".jpg", ".jpeg", ".webp"],
  video: [".mp4", ".mov", ".webm", ".mkv", ".avi"],
  audio: [".wav", ".flac", ".mp3", ".ogg", ".m4a", ".opus"],
};
const kindOf = (f) => {
  const ext = f.slice(f.lastIndexOf(".")).toLowerCase();
  return Object.keys(KIND_EXT).find((k) => KIND_EXT[k].includes(ext)) || null;
};
const baseName = (f) => f.split(/[\\/]/).pop();
const isAbs = (p) => /^([a-zA-Z]:[\\/]|[\\/]|~)/.test(p);

export function parseList(text) {
  const groups = [];
  let cur = null;
  for (const raw of String(text || "").split(/\r?\n/)) {
    const line = raw.trim();
    if (line.startsWith("#")) {
      cur = { name: line.replace(/^#+/, "").trim(), files: [] };
      groups.push(cur);
    } else if (!line) {
      cur = null;
    } else {
      if (!cur) groups.push((cur = { name: "", files: [] }));
      cur.files.push(line.replace(/^"|"$/g, ""));
    }
  }
  return groups;
}

export function formatList(groups) {
  return groups
    .filter((g) => g.name || g.files.length)
    .map((g) => [g.name ? `# ${g.name}` : null, ...g.files].filter((l) => l !== null).join("\n"))
    .join("\n\n");
}

/* the path stored in the list: relative to the folder when the file is inside it */
function entryFor(abs, base) {
  if (!base) return abs;
  const norm = (p) => p.replace(/\\/g, "/").replace(/\/+$/, "");
  const a = norm(abs), b = norm(base);
  const ci = /^[a-zA-Z]:/.test(b); // Windows paths ignore case
  const inside = ci ? a.toLowerCase().startsWith(b.toLowerCase() + "/") : a.startsWith(b + "/");
  return inside ? a.slice(b.length + 1) : abs;
}

class MediaView {
  constructor(node) {
    this.node = node;
    this.groups = [];
    this.current = 0;       // group that "Add selected" fills
    this.mode = node.properties?.arbor_view || "list";
    this.build();
  }

  w(name) { return this.node.widgets?.find((w) => w.name === name); }
  get folder() { return String(this.w("folder")?.value ?? ""); }

  build() {
    const root = (this.root = el("div", "arb arb-media"));
    const bar = el("div", "arb-bar");
    this.browseBtn = el("button", "arb-btn arb-btn-main");
    this.browseBtn.addEventListener("click", () => this.browse());
    this.seg = el("div", "arb-seg", `<button data-m="list"></button><button data-m="text"></button>`);
    this.seg.addEventListener("click", (e) => {
      const m = e.target?.dataset?.m;
      if (!m || m === this.mode) return;
      this.mode = m;
      this.node.properties.arbor_view = m;
      this.render();
    });
    this.info = el("span", "arb-sub");
    this.addBtn = el("button", "arb-btn");
    this.addBtn.addEventListener("click", () => {
      this.groups.push({ name: "", files: [] });
      this.current = this.groups.length - 1;
      this.save();
      this.render();
    });
    bar.append(this.browseBtn, this.seg, this.info, el("span", "arb-sp"), this.addBtn);

    this.body = el("div", "arb-media-body");
    this.ta = el("textarea", "arb-media-ta");
    this.ta.spellcheck = false;
    this.ta.addEventListener("input", () => {
      this.groups = parseList(this.ta.value);
      this.write(this.ta.value);
      this.updateInfo();
    });
    isolateKeys(this.ta);
    root.append(bar, this.body, this.ta);
    for (const part of [bar, this.body, this.ta]) isolatePointer(part);
  }

  /* ------------------------------------------------------- model <-> widget */

  sync() {
    const fw = this.w("files");
    hideWidget(fw);
    this.groups = parseList(fw?.value);
    this.current = Math.min(this.current, Math.max(0, this.groups.length - 1));
    this.render();
  }

  write(text) {
    const fw = this.w("files");
    if (!fw || fw.value === text) return;
    fw.value = text;
    fw.callback?.(text);
    markChanged(this.node);
  }

  save() {
    this.write(formatList(this.groups));
    this.updateInfo();
  }

  thumbURL(entry) {
    const q = new URLSearchParams({ folder: this.folder, path: entry, size: "160" });
    return api.apiURL(`/arbor/media/thumb?${q}`);
  }

  updateInfo() {
    const n = this.groups.reduce((s, g) => s + g.files.length, 0);
    this.info.textContent = n ? `${tn("file", n)} · ${tn("group", this.groups.filter((g) => g.files.length).length)}` : "";
  }

  /* ------------------------------------------------------- drawing */

  render() {
    this.browseBtn.textContent = t("browse");
    this.browseBtn.title = t("browseTip");
    this.addBtn.textContent = t("addGroup");
    this.seg.children[0].textContent = t("viewList");
    this.seg.children[1].textContent = t("viewText");
    for (const b of this.seg.children) b.classList.toggle("on", b.dataset.m === this.mode);
    this.updateInfo();
    const text = this.mode === "text";
    this.body.style.display = text ? "none" : "";
    this.ta.style.display = text ? "" : "none";
    this.addBtn.style.display = text ? "none" : "";
    if (text) {
      if (document.activeElement !== this.ta) this.ta.value = this.w("files")?.value ?? "";
      this.ta.placeholder = t("mediaTextPh");
      return;
    }
    this.body.textContent = "";
    if (!this.groups.length) {
      this.body.appendChild(el("div", "arb-empty")).textContent = t("mediaEmpty");
      return;
    }
    this.groups.forEach((g, gi) => this.body.appendChild(this.groupEl(g, gi)));
  }

  groupEl(g, gi) {
    const box = el("div", "arb-media-group" + (gi === this.current ? " on" : ""));
    box.addEventListener("pointerdown", () => {
      if (this.current !== gi) {
        this.current = gi;
        this.body.querySelectorAll(".arb-media-group").forEach((b, k) => b.classList.toggle("on", k === gi));
      }
    });
    const hd = box.appendChild(el("div", "arb-media-hd"));
    hd.appendChild(el("span", "arb-path")).textContent = `{${gi}}`;
    const name = hd.appendChild(el("input", "arb-media-name"));
    name.value = g.name;
    name.placeholder = t("groupName");
    name.addEventListener("input", () => { g.name = name.value.replace(/\n/g, " "); this.save(); });
    isolateKeys(name);
    hd.appendChild(el("span", "arb-n")).textContent = tn("file", g.files.length);
    hd.appendChild(el("span", "arb-sp"));
    const del = hd.appendChild(el("button", "arb-media-x", "×"));
    del.title = t("removeGroup");
    del.addEventListener("click", () => {
      this.groups.splice(gi, 1);
      this.current = Math.min(this.current, Math.max(0, this.groups.length - 1));
      this.save();
      this.render();
    });

    const grid = box.appendChild(el("div", "arb-media-grid"));
    g.files.forEach((f, fi) => grid.appendChild(this.tileEl(f, gi, fi)));
    if (!g.files.length) grid.appendChild(el("div", "arb-media-hint")).textContent = t("groupEmpty");
    // dropping on the group's free space appends to it
    grid.addEventListener("dragover", (e) => { if (this.drag) { e.preventDefault(); grid.classList.add("over"); } });
    grid.addEventListener("dragleave", () => grid.classList.remove("over"));
    grid.addEventListener("drop", (e) => {
      grid.classList.remove("over");
      if (!this.drag || e.target.closest(".arb-media-tile")) return;
      e.preventDefault();
      this.move(this.drag, gi, g.files.length);
    });
    return box;
  }

  tileEl(f, gi, fi) {
    const kind = kindOf(f);
    const tile = el("div", `arb-media-tile k-${kind || "x"}`);
    tile.title = f;
    tile.draggable = true;
    if (kind === "image" || kind === "video") {
      const img = tile.appendChild(el("img"));
      img.loading = "lazy";
      img.src = this.thumbURL(f);
      img.addEventListener("error", () => { img.remove(); tile.classList.add("noimg"); });
    }
    tile.appendChild(el("span", "arb-media-badge")).textContent = kind === "video" ? "▶" : kind === "audio" ? "♪" : "";
    tile.appendChild(el("span", "arb-media-fn")).textContent = baseName(f);
    const x = tile.appendChild(el("button", "arb-media-x", "×"));
    x.title = t("remove");
    x.addEventListener("click", (e) => {
      e.stopPropagation();
      this.groups[gi].files.splice(fi, 1);
      this.save();
      this.render();
    });
    tile.addEventListener("dragstart", (e) => {
      this.drag = { gi, fi };
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/x-arbor-media", f);
    });
    tile.addEventListener("dragend", () => { this.drag = null; });
    tile.addEventListener("dragover", (e) => { if (this.drag) { e.preventDefault(); tile.classList.add("over"); } });
    tile.addEventListener("dragleave", () => tile.classList.remove("over"));
    tile.addEventListener("drop", (e) => {
      tile.classList.remove("over");
      if (!this.drag) return;
      e.preventDefault();
      e.stopPropagation();
      this.move(this.drag, gi, fi);
    });
    return tile;
  }

  move(from, gi, fi) {
    const [f] = this.groups[from.gi].files.splice(from.fi, 1);
    if (from.gi === gi && from.fi < fi) fi -= 1;
    this.groups[gi].files.splice(fi, 0, f);
    this.drag = null;
    this.save();
    this.render();
  }

  /* ------------------------------------------------------- adding files */

  add(entries, name) {
    if (!entries.length) return;
    let g = this.groups[this.current];
    if (name != null || !g) {
      g = { name: name || "", files: [] };
      this.groups.push(g);
      this.current = this.groups.length - 1;
    }
    g.files.push(...entries);
    this.save();
    this.render();
  }

  browse() {
    openMediaBrowser({
      folder: this.folder,
      mode: "files",
      onFiles: (paths, info) => this.add(paths.map((p) => entryFor(p, info.base))),
      onGroups: (groups, info) => {
        for (const g of groups) this.add(g.files.map((p) => entryFor(p, info.base)), g.name);
      },
    });
  }
}

app.registerExtension({
  name: "Arbor.LoadMedia",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      this.properties ||= {};
      const view = new MediaView(this);
      this.__arborMedia = view;
      const off = onLocaleChange(() => view.render());
      chain(this, "onRemoved", off);
      this.addDOMWidget("arbor_media", "arbor-media", view.root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 180,
      });
      const fw = view.w("folder");
      if (fw) {
        const cb = fw.callback;
        fw.callback = function (...a) {
          const r = cb?.apply(this, a);
          view.render();
          return r;
        };
      }
      view.sync();
      const [w, h] = this.size || [0, 0];
      this.setSize?.([Math.max(w, 380), Math.max(h, 360)]);
    });

    chain(nodeType.prototype, "onConfigure", function () {
      this.__arborMedia?.sync();
    });
  },
});
