import "./style.css";
import type { ConfigRowViewModel, ModelRuntimeState } from "./data/types";
import {
  getAllTableRows,
  getConfigCount,
  getConfigById,
  getConfigFileText,
  downloadModel,
  startModel,
  stopModel,
  deleteModelWeights,
  deleteConfigFile,
} from "./data/repository";
import { createActionButton } from "./ui/actionButtons";

function el<K extends keyof HTMLElementTagNameMap>(
  name: K,
  props?: { className?: string; text?: string; html?: string }
): HTMLElementTagNameMap[K] {
  const n = document.createElement(name);
  if (props?.className) n.className = props.className;
  if (props?.text) n.textContent = props.text;
  if (props?.html) n.innerHTML = props.html;
  return n;
}

function showConfigTextModal(fileName: string, text: string): void {
  const backdrop = el("div", { className: "config-dlg-backdrop" });
  const dlg = el("div", { className: "config-dlg" });
  const closeAll = (): void => {
    backdrop.remove();
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") closeAll();
  };
  document.addEventListener("keydown", onKey);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) closeAll();
  });
  const title = el("div", { className: "config-dlg__title" });
  title.textContent = fileName;
  const pre = el("pre", { className: "config-dlg__pre" });
  pre.textContent = text;
  const closeBtn = el("button", {
    className: "btn primary config-dlg__close",
    text: "Close",
  });
  closeBtn.type = "button";
  closeBtn.addEventListener("click", closeAll);
  dlg.append(title, pre, closeBtn);
  backdrop.append(dlg);
  document.body.append(backdrop);
  closeBtn.focus();
}

function openConfigViewer(configId: string): void {
  const text = getConfigFileText(configId);
  if (text == null) return;
  const doc = getConfigById(configId);
  showConfigTextModal(doc?.fileName ?? "config", text);
}

function renderActions(
  state: ModelRuntimeState,
  r: ConfigRowViewModel,
  onRefresh: () => void
): HTMLElement {
  const wrap = el("div", { className: "actions" });
  const { configId, actionsLocked: locked } = r;
  const view = createActionButton("viewConfig");
  view.addEventListener("click", () => {
    openConfigViewer(configId);
  });
  wrap.append(view);

  if (state === "not_on_disk" || state === "downloading") {
    const busy = state === "downloading";
    const load = createActionButton("load", { disabled: busy || locked, busy });
    if (busy) {
      load.title = "Downloading weights… (simulated)";
      load.setAttribute("aria-label", "Downloading");
    }
    load.addEventListener("click", () => {
      void downloadModel(configId, onRefresh);
    });
    const delCfg = createActionButton("trashConfig", { disabled: locked });
    delCfg.addEventListener("click", () => {
      deleteConfigFile(configId);
      onRefresh();
    });
    wrap.append(load, delCfg);
  } else if (state === "downloaded") {
    const play = createActionButton("play", { disabled: locked });
    play.addEventListener("click", () => {
      void startModel(configId, onRefresh);
    });
    const delModel = createActionButton("trashModel", { disabled: locked });
    delModel.addEventListener("click", () => {
      void deleteModelWeights(configId, onRefresh);
    });
    const delCfg = createActionButton("trashConfig", { disabled: locked });
    delCfg.addEventListener("click", () => {
      deleteConfigFile(configId);
      onRefresh();
    });
    wrap.append(play, delModel, delCfg);
  } else {
    const stopB = createActionButton("stop", { disabled: locked });
    stopB.addEventListener("click", () => {
      void stopModel(configId, onRefresh);
    });
    const delModel = createActionButton("trashModel", { disabled: locked });
    delModel.addEventListener("click", () => {
      void deleteModelWeights(configId, onRefresh);
    });
    const delCfg = createActionButton("trashConfig", { disabled: locked });
    delCfg.addEventListener("click", () => {
      deleteConfigFile(configId);
      onRefresh();
    });
    wrap.append(stopB, delModel, delCfg);
  }
  return wrap;
}

function statusHeadline(s: ModelRuntimeState): string {
  switch (s) {
    case "not_on_disk":
      return "Not on disk";
    case "downloading":
      return "Downloading";
    case "downloaded":
      return "On disk";
    case "running":
      return "Running";
  }
}

function renderStatus(r: ConfigRowViewModel): HTMLElement {
  const wrap = el("div", { className: "status-cell" });
  const h = el("div", { className: "status-headline" });
  h.textContent = statusHeadline(r.state);
  h.classList.add("status--" + r.state);
  const detail = el("div", {
    className: "status-detail",
    text: r.lastRunMessage ?? "—",
  });
  wrap.append(h, detail);
  return wrap;
}

function renderTable(onRefresh: () => void): HTMLElement {
  const rows = getAllTableRows();
  const table = el("table", { className: "or-table" });
  const thead = el("thead");
  const trh = el("tr");
  trh.append(
    el("th", { className: "col-n", text: "#" }),
    el("th", { className: "col-file", text: "File" }),
    el("th", { className: "col-name", text: "Name" }),
    el("th", { className: "col-status", text: "Status" }),
    el("th", { className: "col-actions", text: "Actions" })
  );
  thead.append(trh);
  const tbody = el("tbody");
  for (const r of rows) {
    const tr = el("tr");
    const tdStatus = el("td", { className: "col-status" });
    tdStatus.append(renderStatus(r));
    tr.append(
      el("td", { className: "col-n", text: String(r.index) }),
      el("td", { className: "col-file", text: r.fileName }),
      el("td", { className: "col-name", text: r.name }),
      tdStatus
    );
    const tdA = el("td", { className: "col-actions" });
    tdA.append(renderActions(r.state, r, onRefresh));
    tr.append(tdA);
    tbody.append(tr);
  }
  table.append(thead, tbody);
  return table;
}

function mount(root: HTMLElement): void {
  root.innerHTML = "";
  const shell = el("div", { className: "shell" });
  const header = el("header", { className: "head" });
  const sub = el("p", {
    className: "sub",
    text: "",
  });
  const refresh = (): void => {
    const n = getConfigCount();
    sub.textContent = `Configs: ${n} (vllm/llm-configs/*.env) · runtime: simulated (local state)`;
    const m = root.querySelector("main.main");
    if (m) m.replaceChildren(renderTable(refresh));
  };
  sub.textContent = `Configs: ${getConfigCount()} (vllm/llm-configs/*.env) · runtime: simulated (local state)`;

  header.append(
    el("h1", { text: "LLM Orchestrator" }),
    sub
  );

  const addBtn = el("button", { className: "btn primary", text: "+ Add new config" });
  addBtn.type = "button";
  addBtn.disabled = true;
  const foot = el("div", { className: "footer" });
  foot.append(addBtn);

  const main = el("main", { className: "main" });
  main.append(renderTable(refresh));

  shell.append(header, main, foot);
  root.append(shell);
}

const app = document.getElementById("app");
if (app) mount(app);
