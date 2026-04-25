import "./style.css";
import type { ConfigRowViewModel, HostStats, ModelRuntimeState } from "./data/types";
import {
  fetchHostStats,
  fetchModels,
  getConfigFileText,
  createConfig,
  updateConfigFileText,
  downloadModel,
  startModel,
  stopModel,
  deleteModelWeights,
  deleteConfigFile,
  ApiError,
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

function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"] as const;
  let v = n;
  let u = 0;
  while (v >= 1024 && u < units.length - 1) {
    v /= 1024;
    u += 1;
  }
  const d = u === 0 || v >= 10 ? v.toFixed(0) : v.toFixed(1);
  return `${d} ${units[u]}`;
}

function hostStatsRow(
  label: string,
  value: string,
  labelHint?: string
): HTMLElement {
  const row = el("div", { className: "host-stats__row" });
  if (labelHint) {
    const col = el("div", { className: "host-stats__label-col" });
    col.append(
      el("span", { className: "host-stats__label", text: label }),
      el("div", { className: "host-stats__label-hint", text: labelHint })
    );
    row.append(
      col,
      el("span", { className: "host-stats__value", text: value })
    );
  } else {
    row.append(
      el("span", { className: "host-stats__label", text: label }),
      el("span", { className: "host-stats__value", text: value })
    );
  }
  return row;
}

function renderHostStats(s: HostStats): HTMLElement {
  const root = el("div", { className: "host-stats__inner" });
  const grid = el("div", { className: "host-stats__grid" });
  grid.append(
    hostStatsRow("CPU", `${s.cpuPercent.toFixed(1)}%`),
    hostStatsRow(
      "RAM",
      `${formatBytes(s.memory.usedBytes)} / ${formatBytes(
        s.memory.totalBytes
      )} used — ${formatBytes(s.memory.availableBytes)} free`
    )
  );
  if (s.gpus.length) {
    s.gpus.forEach((g) => {
      const base = `GPU ${g.index}`;
      const load =
        g.utilizationPercent != null ? `${g.utilizationPercent}%` : "n/a";
      const pwr = g.powerDrawW != null ? `${g.powerDrawW} W` : "n/a";
      const wrap = el("div", { className: "host-stats__gpu" });
      wrap.append(
        hostStatsRow(base, g.name),
        hostStatsRow(`${base} — load`, load),
        hostStatsRow(`${base} — power draw`, pwr),
        hostStatsRow(
          `${base} — VRAM`,
          `${g.memoryUsedMib} / ${g.memoryTotalMib} MiB used, ${g.memoryFreeMib} MiB free`
        )
      );
      grid.append(wrap);
    });
  } else {
    grid.append(
      hostStatsRow(
        "GPU",
        "not detected: install nvidia-smi in the API image and run the container with GPU access (e.g. --gpus all)"
      )
    );
  }
  if (s.models) {
    const m = s.models;
    const fs = m.filesystem;
    grid.append(
      hostStatsRow("MODELS_DIR path", m.path),
      hostStatsRow(
        "Size of MODELS_DIR (folder)",
        `${formatBytes(m.dirSizeBytes)} / ${formatBytes(fs.freeBytes)} (free)`,
        "Left: all files in this tree (weights, cache). After slash: free space on the same disk volume. The (free) tag marks the free value after the slash."
      )
    );
  } else {
    if (s.modelsError) {
      grid.append(hostStatsRow("Models / disk", s.modelsError));
    } else if (!s.modelsDirConfigured) {
      grid.append(
        hostStatsRow("Models / disk", "MODELS_DIR is not set in the API process")
      );
    }
  }
  root.append(grid);
  return root;
}

function apiErrorToMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const raw = e.message;
    try {
      const j = JSON.parse(raw) as { detail?: string | { msg: string }[] };
      if (typeof j.detail === "string") return j.detail;
      if (Array.isArray(j.detail) && j.detail[0] && "msg" in (j.detail[0] as object)) {
        return String((j.detail[0] as { msg: string }).msg);
      }
    } catch {
      if (raw) return raw;
    }
    return `Error ${e.status}`;
  }
  return e instanceof Error ? e.message : "Could not save config";
}

function showEditConfigDialog(
  configId: string,
  fileName: string,
  text: string,
  onSaved: () => void | Promise<void>
): void {
  const backdrop = el("div", { className: "config-dlg-backdrop" });
  const dlg = el("div", { className: "config-dlg config-dlg--form" });
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
  title.textContent = "Edit config";

  const fileWrap = el("div", { className: "config-dlg__field" });
  const fileLabel = el("label", {
    className: "config-dlg__label",
    text: "File",
  });
  const fileIn = el("input", { className: "config-dlg__input" }) as HTMLInputElement;
  fileIn.id = "edit-cfg-filename";
  fileLabel.setAttribute("for", fileIn.id);
  fileIn.type = "text";
  fileIn.readOnly = true;
  fileIn.value = fileName;
  fileIn.tabIndex = -1;
  fileWrap.append(fileLabel, fileIn);

  const textWrap = el("div", { className: "config-dlg__field" });
  const textLabel = el("label", {
    className: "config-dlg__label",
    text: "Contents",
  });
  const ta = el("textarea", {
    className: "config-dlg__textarea",
  }) as HTMLTextAreaElement;
  ta.id = "edit-cfg-body";
  textLabel.setAttribute("for", ta.id);
  ta.rows = 18;
  ta.value = text;
  textWrap.append(textLabel, ta);

  const err = el("div", { className: "config-dlg__err" });
  err.hidden = true;

  const actions = el("div", { className: "config-dlg__actions" });
  const cancel = el("button", { className: "btn", text: "Cancel" });
  cancel.type = "button";
  const save = el("button", { className: "btn btn--save", text: "Save" });
  save.type = "button";
  cancel.addEventListener("click", closeAll);
  save.addEventListener("click", () => {
    void (async () => {
      err.textContent = "";
      err.hidden = true;
      save.disabled = true;
      try {
        await updateConfigFileText(configId, ta.value);
        closeAll();
        await onSaved();
      } catch (e) {
        err.textContent = apiErrorToMessage(e);
        err.hidden = false;
      } finally {
        save.disabled = false;
      }
    })();
  });
  actions.append(cancel, save);

  dlg.append(title, fileWrap, textWrap, err, actions);
  backdrop.append(dlg);
  document.body.append(backdrop);
  ta.focus();
  ta.setSelectionRange(0, 0);
}

function showAddConfigDialog(onSaved: () => void | Promise<void>): void {
  const backdrop = el("div", { className: "config-dlg-backdrop" });
  const dlg = el("div", { className: "config-dlg config-dlg--form" });
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
  title.textContent = "Add config";

  const fileWrap = el("div", { className: "config-dlg__field" });
  const fileLabel = el("label", {
    className: "config-dlg__label",
    text: "File name",
  });
  const fileIn = el("input", { className: "config-dlg__input" }) as HTMLInputElement;
  fileIn.id = "add-cfg-filename";
  fileLabel.setAttribute("for", fileIn.id);
  fileIn.type = "text";
  fileIn.autocomplete = "off";
  fileIn.placeholder = "e.g. my-vllm.env";
  fileWrap.append(fileLabel, fileIn);

  const textWrap = el("div", { className: "config-dlg__field" });
  const textLabel = el("label", {
    className: "config-dlg__label",
    text: "Config",
  });
  const ta = el("textarea", {
    className: "config-dlg__textarea",
  }) as HTMLTextAreaElement;
  ta.id = "add-cfg-body";
  textLabel.setAttribute("for", ta.id);
  ta.rows = 16;
  ta.placeholder = "# .env for vLLM (one KEY=value per line)";
  textWrap.append(textLabel, ta);

  const err = el("div", { className: "config-dlg__err" });
  err.hidden = true;

  const actions = el("div", { className: "config-dlg__actions" });
  const cancel = el("button", {
    className: "btn",
    text: "Cancel",
  });
  cancel.type = "button";
  const save = el("button", {
    className: "btn btn--save",
    text: "Save",
  });
  save.type = "button";
  cancel.addEventListener("click", closeAll);
  save.addEventListener("click", () => {
    void (async () => {
      const name = fileIn.value.trim();
      const body = ta.value;
      err.textContent = "";
      err.hidden = true;
      if (!name) {
        err.textContent = "Enter a file name.";
        err.hidden = false;
        return;
      }
      save.disabled = true;
      try {
        await createConfig(name, body);
        closeAll();
        await onSaved();
      } catch (e) {
        err.textContent = apiErrorToMessage(e);
        err.hidden = false;
      } finally {
        save.disabled = false;
      }
    })();
  });
  actions.append(cancel, save);

  dlg.append(title, fileWrap, textWrap, err, actions);
  backdrop.append(dlg);
  document.body.append(backdrop);
  fileIn.focus();
}

function openConfigEditor(
  configId: string,
  onRefresh: () => void | Promise<void>
): void {
  void (async () => {
    const res = await getConfigFileText(configId);
    if (res == null) return;
    showEditConfigDialog(configId, res.fileName, res.text, onRefresh);
  })();
}

function renderActions(
  state: ModelRuntimeState,
  r: ConfigRowViewModel,
  onRefresh: () => void | Promise<void>
): HTMLElement {
  const wrap = el("div", { className: "actions" });
  const { configId, actionsLocked: locked } = r;
  const view = createActionButton("viewConfig");
  view.addEventListener("click", () => {
    void openConfigEditor(configId, onRefresh);
  });
  wrap.append(view);

  if (state === "not_on_disk" || state === "downloading") {
    const busy = state === "downloading";
    const load = createActionButton("load", { disabled: busy || locked, busy });
    if (busy) {
      load.title = "Downloading weights…";
      load.setAttribute("aria-label", "Downloading");
    }
    load.addEventListener("click", () => {
      void (async () => {
        const poll = window.setInterval(() => {
          void onRefresh();
        }, 400);
        try {
          await downloadModel(configId);
        } catch (e) {
          console.error(e);
        } finally {
          clearInterval(poll);
        }
        await onRefresh();
      })();
    });
    const delCfg = createActionButton("trashConfig", { disabled: locked });
    delCfg.addEventListener("click", () => {
      void (async () => {
        try {
          await deleteConfigFile(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
    });
    wrap.append(load, delCfg);
  } else if (state === "downloaded") {
    const play = createActionButton("play", { disabled: locked });
    play.addEventListener("click", () => {
      void (async () => {
        try {
          await startModel(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
    });
    const delModel = createActionButton("trashModel", { disabled: locked });
    delModel.addEventListener("click", () => {
      void (async () => {
        try {
          await deleteModelWeights(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
    });
    const delCfg = createActionButton("trashConfig", { disabled: locked });
    delCfg.addEventListener("click", () => {
      void (async () => {
        try {
          await deleteConfigFile(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
    });
    wrap.append(play, delModel, delCfg);
  } else {
    const stopB = createActionButton("stop", { disabled: locked });
    stopB.addEventListener("click", () => {
      void (async () => {
        try {
          await stopModel(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
    });
    const delModel = createActionButton("trashModel", { disabled: locked });
    delModel.addEventListener("click", () => {
      void (async () => {
        try {
          await deleteModelWeights(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
    });
    const delCfg = createActionButton("trashConfig", { disabled: locked });
    delCfg.addEventListener("click", () => {
      void (async () => {
        try {
          await deleteConfigFile(configId);
        } catch (e) {
          console.error(e);
        }
        await onRefresh();
      })();
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
  const detail = el("div", { className: "status-detail" });
  if (r.state === "downloading") {
    if (r.downloadProgress != null) {
      detail.textContent = `${r.downloadProgress.toFixed(1)}%`;
      const bar = el("div", { className: "download-progress" });
      const fill = el("div", { className: "download-progress__fill" });
      fill.style.width = `${Math.min(100, Math.max(0, r.downloadProgress))}%`;
      bar.append(fill);
      wrap.append(h, bar, detail);
    } else {
      detail.textContent = "Preparing…";
      wrap.append(h, detail);
    }
  } else {
    detail.textContent = r.lastRunMessage ?? "—";
    wrap.append(h, detail);
  }
  return wrap;
}

function renderTable(
  rows: ConfigRowViewModel[],
  onRefresh: () => void | Promise<void>
): HTMLElement {
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
  const sub = el("p", { className: "sub", text: "Loading…" });
  const main = el("main", { className: "main" });
  const hostPanel = el("div", { className: "host-stats" });
  hostPanel.append(
    el("div", {
      className: "host-stats__title",
      text: "Server resources",
    })
  );
  const hostBody = el("div", { className: "host-stats__body" });
  hostBody.textContent = "Loading…";
  hostPanel.append(hostBody);
  const tableMount = el("div", { className: "table-wrap" });
  main.append(hostPanel, tableMount);
  const addBtn = el("button", {
    className: "btn primary",
    text: "+ Add new config",
  });
  addBtn.type = "button";
  addBtn.disabled = true;
  const foot = el("div", { className: "footer" });
  foot.append(addBtn);
  addBtn.addEventListener("click", () => {
    showAddConfigDialog(refresh);
  });

  const refresh = async (): Promise<void> => {
    try {
      const { rows, count } = await fetchModels();
      addBtn.disabled = false;
      sub.textContent = `Configs: ${count} (CONFIGS_DIR / *.env) · state: server API`;
      tableMount.replaceChildren(renderTable(rows, refresh));
    } catch (e) {
      addBtn.disabled = true;
      const msg = e instanceof ApiError ? `API error ${e.status}` : "Cannot reach API";
      sub.textContent = `${msg} — start backend: cd backend && uvicorn app.main:app --port 8765`;
      tableMount.replaceChildren(
        el("p", {
          className: "api-err",
          text: "Vite dev proxies /api → :8765. Or set VITE_API_BASE_URL to your API base.",
        })
      );
    }
  };

  header.append(
    el("h1", { text: "LLM Orchestrator" }),
    sub
  );
  shell.append(header, main, foot);
  root.append(shell);
  void (async () => {
    const [hst, mdl] = await Promise.allSettled([
      fetchHostStats(),
      fetchModels(),
    ]);
    if (hst.status === "fulfilled") {
      hostBody.replaceChildren(renderHostStats(hst.value));
    } else {
      hostBody.classList.add("host-stats__body--err");
      hostBody.textContent =
        hst.reason instanceof ApiError
          ? `Host stats failed (HTTP ${hst.reason.status})`
          : "Host stats unavailable";
    }
    if (mdl.status === "fulfilled") {
      const { rows, count } = mdl.value;
      addBtn.disabled = false;
      sub.textContent = `Configs: ${count} (CONFIGS_DIR / *.env) · state: server API`;
      tableMount.replaceChildren(renderTable(rows, refresh));
    } else {
      addBtn.disabled = true;
      const e = mdl.reason;
      const msg = e instanceof ApiError ? `API error ${e.status}` : "Cannot reach API";
      sub.textContent = `${msg} — start backend: cd backend && uvicorn app.main:app --port 8765`;
      tableMount.replaceChildren(
        el("p", {
          className: "api-err",
          text: "Vite dev proxies /api → :8765. Or set VITE_API_BASE_URL to your API base.",
        })
      );
    }
  })();
}

const app = document.getElementById("app");
if (app) mount(app);
