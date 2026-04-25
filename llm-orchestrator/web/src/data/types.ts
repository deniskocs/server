/**
 * Mirrors `vllm/llm-configs/*.env` in the repo (DEFAULT_MODEL_NAME, VLLM_*), not root `llm-configs/*.yaml`.
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

/** One deploy profile = one `.env` file under `vllm/llm-configs/`. */
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
  /** `vllm/llm-configs/*.env` file name. */
  fileName: string;
  /** Served model name (SERVED_MODEL_NAME). */
  name: string;
  state: ModelRuntimeState;
  /** When true, simulates in-flight request; action buttons are disabled. */
  actionsLocked: boolean;
  lastRunMessage: string | null;
}
