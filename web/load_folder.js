/* Arbor · Load Folder — the folder box gets a folder icon at its end, like ComfyUI's own
 * file widgets: click it to pick the folder with the system's folder dialog
 * (system_dialog.js) instead of typing the path. The original `folder` widget stays
 * (hidden) and keeps the value; this row only shows and edits it, and is not saved,
 * so workflows saved before keep their widget values in place. */

import { app } from "../../scripts/app.js";
import { injectStyle, el, chain, hideWidget, isolateKeys, isolatePointer, markChanged, ICONS, t, onLocaleChange } from "./arbor_common.js";
import { systemDialog } from "./system_dialog.js";

const NODE = "Arbor_LoadFolder";

app.registerExtension({
  name: "Arbor.LoadFolder",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;
    injectStyle();

    chain(nodeType.prototype, "onNodeCreated", function () {
      const node = this;
      const fw = this.widgets?.find((w) => w.name === "folder");
      if (!fw) return;
      hideWidget(fw);

      const row = el("div", "arb arb-path");
      const label = row.appendChild(el("span", "arb-path-label"));
      const box = row.appendChild(el("div", "arb-path-box"));
      const input = box.appendChild(el("input", "arb-path-in"));
      input.spellcheck = false;
      const pick = box.appendChild(el("button", "arb-path-btn", ICONS.folder));
      isolateKeys(input);
      isolatePointer(row);

      const set = (value) => {
        fw.value = value;
        fw.callback?.(value);
        markChanged(node);
      };
      input.addEventListener("change", () => set(input.value.trim()));
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
      pick.addEventListener("click", async () => {
        const r = await systemDialog("folder", String(fw.value ?? ""), t("dialogFolder"));
        if (!r) return;
        set(r.entries[0]);
        input.value = fw.value;
      });

      const show = () => {
        label.textContent = fw.label || fw.name;
        pick.title = t("folderPickTip");
        if (document.activeElement !== input) input.value = String(fw.value ?? "");
        input.title = input.value;
      };
      node.__arborFolderRow = show;
      show();

      // Nodes 2.0 lays widgets out as label | box: take the neighbours' label width and box height
      // so the row lines up with them; the classic canvas keeps the pill
      const adapt = () => {
        const host = row.closest(".lg-node-widgets");
        row.classList.toggle("v2", !!host);
        if (!host) return;
        const others = (sel) => [...host.querySelectorAll(sel)].find((e) => !row.contains(e) && e.offsetWidth);
        const lab = others(".lg-node-widget .truncate");
        const inp = others(".lg-node-widget input");
        if (lab) {
          const cs = getComputedStyle(lab);
          row.style.setProperty("--lw", `${lab.offsetWidth}px`);
          row.style.setProperty("--lc", cs.color);
          row.style.setProperty("--lwt", cs.fontWeight);
        }
        if (inp) {
          const cs = getComputedStyle(inp);
          row.style.setProperty("--bh", `${inp.offsetHeight}px`);
          row.style.setProperty("--bbg", cs.backgroundColor);
          row.style.setProperty("--bfg", cs.color);
        }
      };
      new ResizeObserver(adapt).observe(row);

      const dom = this.addDOMWidget("arbor_folder", "arbor-folder", row, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 26,
        getMaxHeight: () => 26,
      });
      dom.serialize = false;
      // put the row where the folder widget was
      this.widgets.splice(this.widgets.indexOf(dom), 1);
      this.widgets.splice(this.widgets.indexOf(fw) + 1, 0, dom);
      chain(this, "onRemoved", onLocaleChange(show));
    });

    chain(nodeType.prototype, "onConfigure", function () {
      this.__arborFolderRow?.();
    });
  },
});
