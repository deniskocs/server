"""In-memory fake runtime (was web/src/data/repository.ts logic)."""

from __future__ import annotations

import asyncio
import copy
from typing import Any, Literal

from .seed_data import HARDCODED_CONFIGS

ModelRuntimeState = Literal["not_on_disk", "downloading", "downloaded", "running"]


def _default_initial_state(config_id: str) -> tuple[ModelRuntimeState, str | None]:
    if config_id == "cfg-vllm-env":
        return "not_on_disk", None
    if config_id == "cfg-vllm-llama-env":
        return "running", "OK: started on :8000"
    return "downloaded", None


def format_config_file_text(doc: dict[str, Any]) -> str:
    v = doc["vllm"]
    lines = [
        f"# vllm/llm-configs/{doc['fileName']}",
        f"DEFAULT_MODEL_NAME={doc['defaultModelName']}",
        f"SERVED_MODEL_NAME={doc['servedModelName']}",
        "",
        "# Параметры vLLM",
        f"VLLM_QUANTIZATION={v.get('quantization') or ''}",
        f"VLLM_MAX_MODEL_LEN={v['maxModelLen']}",
        f"VLLM_DTYPE={v.get('dtype') or ''}",
        f"VLLM_GPU_MEMORY_UTILIZATION={v['gpuMemoryUtilization']}",
    ]
    if "tensorParallelSize" in v:
        lines.append(f"VLLM_TENSOR_PARALLEL_SIZE={v.get('tensorParallelSize') or ''}")
    if v.get("reasoningParser"):
        lines.append(f"VLLM_REASONING_PARSER={v['reasoningParser']}")
    lines.append(f"VLLM_ENABLE_AUTO_TOOL_CHOICE={v['enableAutoToolChoice']}")
    lines.append(f"VLLM_TOOL_CALL_PARSER={v['toolCallParser']}")
    return "\n".join(lines)


class OrchestratorSimulation:
    """Thread-safe async state for fake API delays."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._deleted: set[str] = set()
        self._runtime: dict[str, dict[str, Any]] = {}
        self._pending: set[str] = set()

    def _configs(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(c) for c in HARDCODED_CONFIGS if c["id"] not in self._deleted]

    def _get_or_init(self, config_id: str) -> dict[str, Any]:
        if config_id not in self._runtime:
            s, m = _default_initial_state(config_id)
            self._runtime[config_id] = {"state": s, "lastRunMessage": m}
        return self._runtime[config_id]

    def _get_doc(self, config_id: str) -> dict[str, Any] | None:
        for c in self._configs():
            if c["id"] == config_id:
                return c
        return None

    def build_table(self) -> tuple[list[dict[str, Any]], int]:
        rows_out: list[dict[str, Any]] = []
        for i, doc in enumerate(self._configs(), start=1):
            cid = doc["id"]
            r = self._get_or_init(cid)
            st = r["state"]
            rows_out.append(
                {
                    "id": f"{cid}-row",
                    "configId": cid,
                    "index": i,
                    "fileName": doc["fileName"],
                    "name": doc["servedModelName"],
                    "state": st,
                    "actionsLocked": cid in self._pending,
                    "lastRunMessage": r["lastRunMessage"],
                }
            )
        return rows_out, len(rows_out)

    def file_text(self, config_id: str) -> tuple[str, str] | None:
        doc = self._get_doc(config_id)
        if not doc:
            return None
        return doc["fileName"], format_config_file_text(doc)

    def _set_runtime(self, config_id: str, state: ModelRuntimeState, msg: str | None) -> None:
        self._runtime[config_id] = {"state": state, "lastRunMessage": msg}

    async def action_download(self, config_id: str) -> None:
        async with self._lock:
            r = self._get_or_init(config_id)
            if r["state"] != "not_on_disk":
                return
            self._set_runtime(config_id, "downloading", None)
        await asyncio.sleep(0.7)
        async with self._lock:
            if config_id in self._deleted:
                return
            r = self._get_or_init(config_id)
            if r["state"] != "downloading":
                return
            self._set_runtime(config_id, "downloaded", "Weights on disk (simulated)")

    async def action_start(self, config_id: str) -> None:
        async with self._lock:
            r = self._get_or_init(config_id)
            if r["state"] != "downloaded" or config_id in self._pending:
                return
            self._pending.add(config_id)
        try:
            await asyncio.sleep(0.45)
            async with self._lock:
                if config_id in self._deleted:
                    return
                self._set_runtime(
                    config_id,
                    "running",
                    "OK: started on :8000 (simulated)",
                )
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    async def action_stop(self, config_id: str) -> None:
        async with self._lock:
            r = self._get_or_init(config_id)
            if r["state"] != "running" or config_id in self._pending:
                return
            self._pending.add(config_id)
        try:
            await asyncio.sleep(0.4)
            async with self._lock:
                if config_id in self._deleted:
                    return
                self._set_runtime(
                    config_id,
                    "downloaded",
                    "Last run: stopped (simulated)",
                )
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    async def action_delete_model(self, config_id: str) -> None:
        async with self._lock:
            r = self._get_or_init(config_id)
            st = r["state"]
            if st in ("not_on_disk", "downloading") or config_id in self._pending:
                return
            self._pending.add(config_id)
            ms = 0.55 if st == "running" else 0.4
        try:
            await asyncio.sleep(ms)
            async with self._lock:
                if config_id in self._deleted:
                    return
                self._set_runtime(
                    config_id,
                    "not_on_disk",
                    "Model weights no longer on disk (simulated)",
                )
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    def action_delete_config(self, config_id: str) -> bool:
        if not self._get_doc(config_id):
            return False
        self._deleted.add(config_id)
        self._pending.discard(config_id)
        self._runtime.pop(config_id, None)
        return True


state = OrchestratorSimulation()
