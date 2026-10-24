/* Arbor · the system's own file / folder dialog for Load Media and Load Folder.
 *
 * A web page never learns where a picked file lives, so the ComfyUI server opens
 * the native dialog on its own screen and answers with real paths
 * (POST /arbor/media/pick, see arbor/dialogs.py). That only makes sense on the
 * computer running ComfyUI; from another one the server refuses and we say so.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { t } from "./arbor_common.js";

function notify(detail) {
  const toast = app.extensionManager?.toast;
  if (toast?.add) toast.add({ severity: "warn", summary: "Arbor", detail, life: 6000 });
  else window.alert(detail);
}

/* mode: "files" | "folder" | "tree" (a folder, read back as groups); start: where the dialog
 * opens (any path the nodes accept). Resolves to the server's answer — {paths, entries (the same,
 * written short: output/…, arbor:…, relative to input), dir, groups?} — or null when cancelled. */
export async function systemDialog(mode, start, title) {
  let r;
  try {
    r = await api.fetchApi("/arbor/media/pick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, start: start || "", title: title || "" }),
    });
  } catch (e) {
    notify(String(e));
    return null;
  }
  const data = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (data.error) {
    notify(data.error === "remote" ? t("dialogRemote") : data.error);
    return null;
  }
  return data.paths?.length ? data : null;
}
