import { HARDCODED_CONFIGS } from "./hardcoded";
import type { ConfigRowViewModel, EnvConfigDocument, ModelRuntimeState } from "./types";

type RowRuntime = { state: ModelRuntimeState; lastRunMessage: string | null };

const deletedConfigIds = new Set<string>();
const runtimeByConfigId = new Map<string, RowRuntime>();
/** Mid-flight simulated API (play / stop / delete weights, not "download" — that uses `downloading` state). */
const pendingActionIds = new Set<string>();

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function defaultInitialState(configId: string): RowRuntime {
  if (configId === "cfg-vllm-env") {
    return { state: "not_on_disk", lastRunMessage: null };
  }
  if (configId === "cfg-vllm-llama-env") {
    return { state: "running", lastRunMessage: "OK: started on :8000" };
  }
  return { state: "downloaded", lastRunMessage: null };
}

function getOrInitRuntime(configId: string): RowRuntime {
  if (!runtimeByConfigId.has(configId)) {
    runtimeByConfigId.set(configId, defaultInitialState(configId));
  }
  return runtimeByConfigId.get(configId)!;
}

/**
 * All UI code should depend on this module (or types), not on `hardcoded` directly.
 * Runtime mutations simulate backend until `fetch()` is wired.
 */
function formatConfigFileText(doc: EnvConfigDocument): string {
  const { vllm: v } = doc;
  const lines: string[] = [
    `# vllm/llm-configs/${doc.fileName}`,
    `DEFAULT_MODEL_NAME=${doc.defaultModelName}`,
    `SERVED_MODEL_NAME=${doc.servedModelName}`,
    "",
    "# Параметры vLLM",
    `VLLM_QUANTIZATION=${v.quantization ?? ""}`,
    `VLLM_MAX_MODEL_LEN=${v.maxModelLen}`,
    `VLLM_DTYPE=${v.dtype ?? ""}`,
    `VLLM_GPU_MEMORY_UTILIZATION=${v.gpuMemoryUtilization}`,
  ];
  if ("tensorParallelSize" in v) {
    lines.push(`VLLM_TENSOR_PARALLEL_SIZE=${v.tensorParallelSize ?? ""}`);
  }
  if (v.reasoningParser) {
    lines.push(`VLLM_REASONING_PARSER=${v.reasoningParser}`);
  }
  lines.push(
    `VLLM_ENABLE_AUTO_TOOL_CHOICE=${v.enableAutoToolChoice}`,
    `VLLM_TOOL_CALL_PARSER=${v.toolCallParser}`,
  );
  return lines.join("\n");
}

function activeConfigs(): EnvConfigDocument[] {
  return HARDCODED_CONFIGS.filter((c) => !deletedConfigIds.has(c.id));
}

export function listConfigDocuments(): EnvConfigDocument[] {
  return activeConfigs();
}

export function getConfigById(id: string): EnvConfigDocument | undefined {
  return activeConfigs().find((c) => c.id === id);
}

/** Full `.env`-style text for the viewer (modal). */
export function getConfigFileText(configId: string): string | null {
  const doc = getConfigById(configId);
  if (!doc) return null;
  return formatConfigFileText(doc);
}

/** All configs as table rows: one row per `.env` file, indices 1…N. */
export function getAllTableRows(): ConfigRowViewModel[] {
  return activeConfigs().map((doc, i) => {
    const row = getOrInitRuntime(doc.id);
    return {
      id: `${doc.id}-row`,
      configId: doc.id,
      index: i + 1,
      fileName: doc.fileName,
      name: doc.servedModelName,
      state: row.state,
      actionsLocked: pendingActionIds.has(doc.id),
      lastRunMessage: row.lastRunMessage,
    };
  });
}

export function getConfigCount(): number {
  return activeConfigs().length;
}

function setRuntime(
  configId: string,
  state: ModelRuntimeState,
  lastRunMessage: string | null
): void {
  runtimeByConfigId.set(configId, { state, lastRunMessage });
}

/** Simulated: download / load model weights to disk. */
export async function downloadModel(
  configId: string,
  onStateChange: () => void
): Promise<void> {
  const r = getOrInitRuntime(configId);
  if (r.state !== "not_on_disk") return;
  setRuntime(configId, "downloading", null);
  onStateChange();
  await delay(700);
  if (deletedConfigIds.has(configId)) return;
  setRuntime(configId, "downloaded", "Weights on disk (simulated)");
  onStateChange();
}

/** Simulated: start the model process. */
export async function startModel(
  configId: string,
  onStateChange: () => void
): Promise<void> {
  const r = getOrInitRuntime(configId);
  if (r.state !== "downloaded" || pendingActionIds.has(configId)) return;
  pendingActionIds.add(configId);
  onStateChange();
  try {
    await delay(450);
    if (deletedConfigIds.has(configId)) return;
    setRuntime(
      configId,
      "running",
      "OK: started on :8000 (simulated)"
    );
    onStateChange();
  } finally {
    pendingActionIds.delete(configId);
    onStateChange();
  }
}

/** Simulated: stop the running model. */
export async function stopModel(
  configId: string,
  onStateChange: () => void
): Promise<void> {
  const r = getOrInitRuntime(configId);
  if (r.state !== "running" || pendingActionIds.has(configId)) return;
  pendingActionIds.add(configId);
  onStateChange();
  try {
    await delay(400);
    if (deletedConfigIds.has(configId)) return;
    setRuntime(
      configId,
      "downloaded",
      "Last run: stopped (simulated)"
    );
    onStateChange();
  } finally {
    pendingActionIds.delete(configId);
    onStateChange();
  }
}

/** Simulated: remove weights from disk; row shows Download again. */
export async function deleteModelWeights(
  configId: string,
  onStateChange: () => void
): Promise<void> {
  const r = getOrInitRuntime(configId);
  if (r.state === "not_on_disk" || r.state === "downloading" || pendingActionIds.has(configId)) {
    return;
  }
  pendingActionIds.add(configId);
  onStateChange();
  try {
    const ms = r.state === "running" ? 550 : 400;
    await delay(ms);
    if (deletedConfigIds.has(configId)) return;
    setRuntime(
      configId,
      "not_on_disk",
      "Model weights no longer on disk (simulated)"
    );
    onStateChange();
  } finally {
    pendingActionIds.delete(configId);
    onStateChange();
  }
}

/** Simulated: delete the `.env` config; row is removed. */
export function deleteConfigFile(configId: string): void {
  deletedConfigIds.add(configId);
  pendingActionIds.delete(configId);
  runtimeByConfigId.delete(configId);
}
