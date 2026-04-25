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
}
