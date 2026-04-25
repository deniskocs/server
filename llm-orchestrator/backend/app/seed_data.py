"""Source of truth for config documents (was web/src/data/hardcoded.ts)."""

from __future__ import annotations

from typing import Any

# Mirrors vllm/llm-configs/*.env snapshots
HARDCODED_CONFIGS: list[dict[str, Any]] = [
    {
        "id": "cfg-vllm-env",
        "fileName": "vllm.env",
        "defaultModelName": "ai-automation-finetuned-awq",
        "servedModelName": "Finetuned",
        "vllm": {
            "quantization": "awq_marlin",
            "maxModelLen": 8192,
            "dtype": "float16",
            "gpuMemoryUtilization": 0.5,
            "enableAutoToolChoice": True,
            "toolCallParser": "llama3_json",
        },
    },
    {
        "id": "cfg-vllm-llama-env",
        "fileName": "vllm-llama.env",
        "defaultModelName": "nvidia/Llama-3.3-70B-Instruct-FP8",
        "servedModelName": "nvidia/Llama-3.3-70B-Instruct-FP8",
        "vllm": {
            "quantization": None,
            "maxModelLen": 8192,
            "dtype": None,
            "gpuMemoryUtilization": 0.95,
            "enableAutoToolChoice": True,
            "toolCallParser": "llama3_json",
        },
    },
    {
        "id": "cfg-qwen3-coder-30b",
        "fileName": "qwen3-coder-30b.env",
        "defaultModelName": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        "servedModelName": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        "vllm": {
            "quantization": None,
            "maxModelLen": 128_000,
            "dtype": None,
            "gpuMemoryUtilization": 0.85,
            "enableAutoToolChoice": True,
            "toolCallParser": "llama3_json",
        },
    },
    {
        "id": "cfg-gpt-oss-120b",
        "fileName": "gpt-oss-120b.env",
        "defaultModelName": "openai/gpt-oss-120b",
        "servedModelName": "openai/gpt-oss-120b",
        "vllm": {
            "quantization": None,
            "maxModelLen": 131_072,
            "dtype": None,
            "gpuMemoryUtilization": 0.88,
            "enableAutoToolChoice": True,
            "toolCallParser": "openai",
        },
    },
    {
        "id": "cfg-qwen3-6-35b-a3b",
        "fileName": "qwen3.6-35b-a3b.env",
        "defaultModelName": "Qwen/Qwen3.6-35B-A3B",
        "servedModelName": "Qwen/Qwen3.6-35B-A3B",
        "vllm": {
            "quantization": None,
            "maxModelLen": 262_144,
            "dtype": None,
            "gpuMemoryUtilization": 0.85,
            "enableAutoToolChoice": True,
            "toolCallParser": "qwen3_coder",
            "tensorParallelSize": None,
            "reasoningParser": "qwen3",
        },
    },
]
