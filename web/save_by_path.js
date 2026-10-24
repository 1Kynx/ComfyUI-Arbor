/* Arbor · Save by Path — the filename prefix box gets a folder icon at its end
 * (path_row.js): pick the destination folder with the system's folder dialog; the
 * last part of the prefix (the file name part, e.g. "batch") is kept. A folder inside
 * ComfyUI's output folder is written relative to it, anything else as an absolute
 * path (which the node only accepts while ComfyUI listens on this computer alone). */

import { app } from "../../scripts/app.js";
import { injectStyle, chain, t } from "./arbor_common.js";
import { addPathRow } from "./path_row.js";
import { systemDialog } from "./system_dialog.js";

const NODE = "Arbor_SaveByPath";

const parts = (p) => String(p || "").split(/[\\/]+/);
const isAbs = (p) => /^([a-zA-Z]:[\\/]|[\\/]|~)/.test(String(p || ""));

/* where the dialog opens: the folder the prefix saves into */
function startOf(prefix) {
  const dir = parts(prefix).slice(0, -1).join("/");
  if (isAbs(prefix)) return dir;
  return /^output(\/|$)/i.test(dir) ? dir : `output/${dir}`;
}

app.registerExtension({
  name: "Arbor.SaveByPath",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const pw = this.widgets?.find((w) => w.name === "filename_prefix");
      if (!pw) return;
      addPathRow(this, pw, {
        tip: () => t("saveFolderTip"),
        pick: async (value) => {
          const r = await systemDialog("folder", startOf(value), t("dialogSaveFolder"));
          if (!r) return null;
          const name = parts(value).pop() || "batch";
          const base = r.output_rel != null ? r.output_rel : r.paths[0].replace(/[\\/]+$/, "");
          return base ? `${base}/${name}` : name;
        },
      });
    });
  },
});
