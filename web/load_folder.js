/* Arbor · Load Folder — a "Browse…" button that picks the folder with the
 * system's own folder dialog (system_dialog.js) instead of typing its path.
 * A folder inside ComfyUI's output / input folder is written the short way
 * (output/…, or relative). */

import { app } from "../../scripts/app.js";
import { injectStyle, chain, markChanged, t, onLocaleChange } from "./arbor_common.js";
import { systemDialog, shortPath } from "./system_dialog.js";

const NODE = "Arbor_LoadFolder";

app.registerExtension({
  name: "Arbor.LoadFolder",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const node = this;
      const folder = () => node.widgets?.find((w) => w.name === "folder");
      // last in the list, so the saved widget values of older workflows keep their places
      const btn = this.addWidget("button", "browse_folder", null, async () => {
        const r = await systemDialog("folder", String(folder()?.value ?? ""), t("dialogFolder"));
        const w = folder();
        if (!r || !w) return;
        w.value = shortPath(r.paths[0], r);
        w.callback?.(w.value);
        markChanged(node);
      }, { serialize: false });
      btn.serialize = false;
      const relabel = () => { btn.label = t("browseFolder"); node.setDirtyCanvas?.(true, false); };
      relabel();
      chain(this, "onRemoved", onLocaleChange(relabel));
    });
  },
});
