/* Arbor · Load Folder — the folder box gets a folder icon at its end (path_row.js):
 * click it to pick the folder with the system's folder dialog (system_dialog.js)
 * instead of typing the path. */

import { app } from "../../scripts/app.js";
import { injectStyle, chain, t } from "./arbor_common.js";
import { addPathRow } from "./path_row.js";
import { systemDialog } from "./system_dialog.js";

const NODE = "Arbor_LoadFolder";

app.registerExtension({
  name: "Arbor.LoadFolder",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const fw = this.widgets?.find((w) => w.name === "folder");
      if (!fw) return;
      addPathRow(this, fw, {
        tip: () => t("folderPickTip"),
        pick: async (value) => (await systemDialog("folder", value, t("dialogFolder")))?.entries[0] ?? null,
      });
    });
  },
});
