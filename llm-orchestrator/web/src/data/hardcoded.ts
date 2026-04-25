import type { EnvConfigDocument } from "./types";

/**
 * Fixed snapshots from `vllm/llm-configs/*.env` in this repository (not `llm-configs/` at repo root).
 * Values match those files; comments from .env are not stored here.
 */
export const HARDCODED_CONFIGS: readonly EnvConfigDocument[] = [
  {
    id: "cfg-vllm-env",
    fileName: "vllm.env",
    defaultModelName: "ai-automation-finetuned-awq",
    servedModelName: "Finetuned",
    vllm: {
      quantization: "awq_marlin",
      maxModelLen: 8192,
      dtype: "float16",
      gpuMemoryUtilization: 0.5,
      enableAutoToolChoice: true,
      toolCallParser: "llama3_json",
    },
  },
  {
    id: "cfg-vllm-llama-env",
    fileName: "vllm-llama.env",
    defaultModelName: "nvidia/Llama-3.3-70B-Instruct-FP8",
    servedModelName: "nvidia/Llama-3.3-70B-Instruct-FP8",
    vllm: {
      quantization: null,
      maxModelLen: 8192,
      dtype: null,
      gpuMemoryUtilization: 0.95,
      enableAutoToolChoice: true,
      toolCallParser: "llama3_json",
    },
  },
  {
    id: "cfg-qwen3-coder-30b",
    fileName: "qwen3-coder-30b.env",
    defaultModelName: "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    servedModelName: "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    vllm: {
      quantization: null,
      maxModelLen: 128_000,
      dtype: null,
      gpuMemoryUtilization: 0.85,
      enableAutoToolChoice: true,
      toolCallParser: "llama3_json",
    },
  },
  {
    id: "cfg-gpt-oss-120b",
    fileName: "gpt-oss-120b.env",
    defaultModelName: "openai/gpt-oss-120b",
    servedModelName: "openai/gpt-oss-120b",
    vllm: {
      quantization: null,
      maxModelLen: 131_072,
      dtype: null,
      gpuMemoryUtilization: 0.88,
      enableAutoToolChoice: true,
      toolCallParser: "openai",
    },
  },
  {
    id: "cfg-qwen3-6-35b-a3b",
    fileName: "qwen3.6-35b-a3b.env",
    defaultModelName: "Qwen/Qwen3.6-35B-A3B",
    servedModelName: "Qwen/Qwen3.6-35B-A3B",
    vllm: {
      quantization: null,
      maxModelLen: 262_144,
      dtype: null,
      gpuMemoryUtilization: 0.85,
      enableAutoToolChoice: true,
      toolCallParser: "qwen3_coder",
      tensorParallelSize: null,
      reasoningParser: "qwen3",
    },
  },
];
