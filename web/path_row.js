/* Arbor · a path widget with a folder icon at its end, like ComfyUI's own file widgets.
 *
 * Used by Load Folder (folder) and Save by Path (filename_prefix). The node's own
 * STRING widget stays — hidden — and keeps the value; this row only shows and edits it,
 * and is not saved, so workflows saved before keep their widget values in place.
 * A pill on the classic canvas; label | box like the other widgets in Nodes 2.0. */

import { el, hideWidget, isolateKeys, isolatePointer, markChanged, chain, ICONS, onLocaleChange } from "./arbor_common.js";

/* opts: { tip: () => string, pick: async (value) => new value | null } */
export function addPathRow(node, widget, opts) {
  hideWidget(widget);

  const row = el("div", "arb arb-path");
  const label = row.appendChild(el("span", "arb-path-label"));
  const box = row.appendChild(el("div", "arb-path-box"));
  const input = box.appendChild(el("input", "arb-path-in"));
  input.spellcheck = false;
  const pick = box.appendChild(el("button", "arb-path-btn", ICONS.folder));
  isolateKeys(input);
  isolatePointer(row);

  const set = (value) => {
    widget.value = value;
    widget.callback?.(value);
    markChanged(node);
    show();
  };
  input.addEventListener("change", () => set(input.value.trim()));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
  pick.addEventListener("click", async () => {
    const value = await opts.pick(String(widget.value ?? ""));
    if (value != null) set(value);
  });

  function show() {
    label.textContent = widget.label || widget.name;
    pick.title = opts.tip();
    if (document.activeElement !== input) input.value = String(widget.value ?? "");
    input.title = input.value;
  }
  show();

  // Nodes 2.0 lays widgets out as label | box: take the neighbours' label width, box height and
  // colours so the row lines up with them; the classic canvas keeps the pill
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

  const dom = node.addDOMWidget(`arbor_${widget.name}_row`, "arbor-path", row, {
    serialize: false,
    hideOnZoom: false,
    getMinHeight: () => 26,
    getMaxHeight: () => 26,
  });
  dom.serialize = false;
  // the row sits where the widget was
  node.widgets.splice(node.widgets.indexOf(dom), 1);
  node.widgets.splice(node.widgets.indexOf(widget) + 1, 0, dom);
  chain(node, "onRemoved", onLocaleChange(show));
  chain(node, "onConfigure", show);
  return show;
}
