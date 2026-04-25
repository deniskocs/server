/**
 * Parsed from `*.env` in orchestrator CONFIGS_DIR (DEFAULT_MODEL_NAME, VLLM_*; same shape as vLLM docker-entrypoint).
 */
export interface VllmParams {
  quantization: string | null;
  maxModelLen: number;
  dtype: string | null;
  gpuMemoryUtilization: number;
  enableAutoToolChoice: boolean;
  toolCallParser: string;
  /** Present in some env files, e.g. qwen3.6 */
  tensorParallelSize?: string | null;
  reasoningParser?: string | null;
}

/** One deploy profile = one `*.env` in CONFIGS_DIR. */
export interface EnvConfigDocument {
  id: string;
  fileName: string;
  defaultModelName: string;
  servedModelName: string;
  vllm: VllmParams;
}

export type ModelRuntimeState =
  | "not_on_disk"
  | "downloading"
  | "downloaded"
  | "running";

export interface ConfigRowViewModel {
  id: string;
  /** Stable id of the config document (`doc.id` from `.env` snapshot). */
  configId: string;
  index: number;
  /** `*.env` file name in CONFIGS_DIR. */
  fileName: string;
  /** Served model name (SERVED_MODEL_NAME). */
  name: string;
  state: ModelRuntimeState;
  /** When true, a request is in flight; action buttons are disabled. */
  actionsLocked: boolean;
  lastRunMessage: string | null;
  /** While `state === "downloading"`: 0–100, or null (size not known yet / indeterminate). */
  downloadProgress?: number | null;
}

export interface HostStatsGpu {
  index: number;
  name: string;
  memoryTotalMib: number;
  memoryUsedMib: number;
  memoryFreeMib: number;
  utilizationPercent: number | null;
}

export interface HostStatsModelsFilesystem {
  totalBytes: number;
  usedBytes: number;
  freeBytes: number;
}

export interface HostStatsModels {
  path: string;
  dirSizeBytes: number;
  filesystem: HostStatsModelsFilesystem;
}

export interface HostStats {
  cpuPercent: number;
  memory: {
    totalBytes: number;
    usedBytes: number;
    availableBytes: number;
  };
  gpus: HostStatsGpu[];
  models: HostStatsModels | null;
  modelsDirConfigured: boolean;
  modelsError?: string;
}
