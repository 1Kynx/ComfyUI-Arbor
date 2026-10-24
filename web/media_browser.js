/* Arbor · media browser — the "Browse…" window of Load Media and Load Folder.
 *
 * Lists folders and media files on disk through /arbor/media/browse (thumbnails
 * from /arbor/media/thumb). Two modes:
 *   files  — select files (or a whole folder, subfolders as groups) to add;
 *   folder — pick the folder itself (its files are shown as a preview).
 */

import { api } from "../../scripts/api.js";
import { el, isolateKeys, openModal, t } from "./arbor_common.js";

async function load(folder, path, recursive) {
  const q = new URLSearchParams({ folder: folder || "", path: path || "" });
  if (recursive) q.set("recursive", "1");
  const r = await api.fetchApi(`/arbor/media/browse?${q}`);
  return r.json().catch(() => ({ error: `HTTP ${r.status}` }));
}

/* `path` written the short way when it is inside ComfyUI's input or output folder */
export function shortPath(path, info) {
  const norm = (p) => String(p || "").replace(/\\/g, "/").replace(/\/+$/, "");
  const ci = /^[a-zA-Z]:/.test(norm(path));
  const under = (root) => {
    const a = norm(path), b = norm(root);
    if (!b) return null;
    if ((ci ? a.toLowerCase() : a) === (ci ? b.toLowerCase() : b)) return "";
    const pre = b + "/";
    return (ci ? a.toLowerCase().startsWith(pre.toLowerCase()) : a.startsWith(pre)) ? a.slice(pre.length) : null;
  };
  const out = under(info?.output);
  if (out !== null) return out ? `output/${out}` : "output";
  const inp = under(info?.input);
  if (inp !== null && inp) return inp;
  return path;
}

/* opts: { folder, mode: "files" | "folder", onFiles(paths, info), onGroups(groups, info), onFolder(path, info) } */
export async function openMediaBrowser(opts) {
  const pickFolder = opts.mode === "folder";
  let state = null;
  const selected = new Set();
  let render = () => {};
  const go = async (path) => {
    const data = await load(opts.folder, path);
    if (data.error) {
      if (!state) state = { error: data.error, dirs: [], files: [], drives: [] };
      else state.error = data.error;
    } else {
      state = data;
      selected.clear();
    }
    render();
  };
  const close = openModal(t(pickFolder ? "browseFolderTitle" : "browseTitle"), (body, extra) => {
    body.classList.add("arb-br-body");
    const nav = body.appendChild(el("div", "arb-bar"));
    const up = nav.appendChild(el("button", "arb-btn"));
    const pathIn = nav.appendChild(el("input", "arb-br-path"));
    const drives = nav.appendChild(el("select", "arb-btn arb-br-drives"));
    isolateKeys(pathIn);
    pathIn.addEventListener("keydown", (e) => { if (e.key === "Enter") go(pathIn.value.trim()); });
    up.addEventListener("click", () => state?.parent && go(state.parent));
    drives.addEventListener("change", () => drives.value && go(drives.value));
    const err = body.appendChild(el("div", "arb-err"));
    const panes = body.appendChild(el("div", "arb-br-panes"));
    const dirs = panes.appendChild(el("div", "arb-br-dirs"));
    const files = panes.appendChild(el("div", "arb-br-files"));
    const foot = body.appendChild(el("div", "arb-bar"));
    const all = foot.appendChild(el("button", "arb-btn"));
    const count = foot.appendChild(el("span", "arb-sub"));
    foot.appendChild(el("span", "arb-sp"));
    const addFolder = foot.appendChild(el("button", "arb-btn"));
    const main = foot.appendChild(el("button", "arb-btn arb-btn-main"));
    all.style.display = addFolder.style.display = pickFolder ? "none" : "";

    const absOf = (name) => `${state.path.replace(/[\\/]+$/, "")}${state.path.includes("\\") ? "\\" : "/"}${name}`;
    all.addEventListener("click", () => {
      const names = state?.files?.map((f) => f.name) || [];
      if (selected.size === names.length) selected.clear();
      else names.forEach((n) => selected.add(n));
      render();
    });
    main.addEventListener("click", () => {
      if (!state?.path) return;
      if (pickFolder) {
        opts.onFolder?.(state.path, state);
      } else {
        if (!selected.size) return;
        opts.onFiles?.(state.files.map((f) => f.name).filter((n) => selected.has(n)).map(absOf), state);
      }
      close();
    });
    addFolder.addEventListener("click", async () => {
      if (!state?.path) return;
      const data = await load(opts.folder, state.path, true);
      if (data.error) { state.error = data.error; render(); return; }
      opts.onGroups?.(data.groups, state);
      close();
    });

    render = () => {
      up.textContent = t("up");
      up.disabled = !state?.parent;
      all.textContent = t("selectAll");
      addFolder.textContent = t("addFolder");
      addFolder.title = t("addFolderTip");
      main.textContent = pickFolder ? t("useFolder") : t("addSelected", { n: selected.size });
      main.disabled = pickFolder ? !state?.path : !selected.size;
      err.textContent = state?.error || "";
      err.style.display = state?.error ? "" : "none";
      if (!state) return;
      state.error = "";
      pathIn.value = state.path || "";
      count.textContent = pickFolder && state.files ? t("mediaHere", { n: state.files.length }) : "";
      drives.textContent = "";
      drives.style.display = state.drives?.length > 1 ? "" : "none";
      drives.appendChild(el("option")).textContent = t("drives");
      for (const d of state.drives || []) drives.appendChild(Object.assign(el("option"), { value: d, textContent: d }));
      dirs.textContent = "";
      for (const d of state.dirs || []) {
        const row = dirs.appendChild(el("div", "arb-br-dir"));
        row.textContent = d;
        row.title = d;
        row.addEventListener("click", () => go(absOf(d)));
      }
      files.textContent = "";
      files.classList.toggle("preview", pickFolder);
      if (!state.files?.length) files.appendChild(el("div", "arb-empty")).textContent = t("noMedia");
      for (const f of state.files || []) {
        const tile = files.appendChild(el("div", `arb-media-tile k-${f.kind}` + (selected.has(f.name) ? " sel" : "")));
        tile.title = f.name;
        if (f.kind !== "audio") {
          const img = tile.appendChild(el("img"));
          img.loading = "lazy";
          img.src = api.apiURL(`/arbor/media/thumb?${new URLSearchParams({ path: absOf(f.name), size: "160" })}`);
          img.addEventListener("error", () => { img.remove(); tile.classList.add("noimg"); });
        }
        tile.appendChild(el("span", "arb-media-badge")).textContent = f.kind === "video" ? "▶" : f.kind === "audio" ? "♪" : "";
        tile.appendChild(el("span", "arb-media-fn")).textContent = f.name;
        if (pickFolder) continue;
        tile.addEventListener("click", () => {
          selected.has(f.name) ? selected.delete(f.name) : selected.add(f.name);
          render();
        });
        tile.addEventListener("dblclick", () => {
          opts.onFiles?.([absOf(f.name)], state);
          close();
        });
      }
      extra.textContent = state.local === false ? t("remoteBrowse") : "";
    };
    render();
  });
  await go(opts.start || "");
}
