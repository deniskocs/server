"""In-memory async runtime; config bodies live in CONFIGS_DIR as `*.env` files."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from . import config_files
from .hf_download import download_snapshot_for_config
from .model_disk import (
    delete_model_weight_dirs,
    get_models_path,
    model_weights_appear_on_disk,
    parse_default_model_name,
)

logger = logging.getLogger(__name__)

ModelRuntimeState = Literal["not_on_disk", "downloading", "downloaded", "running"]


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


def _default_initial_state(file_name: str) -> tuple[ModelRuntimeState, str | None]:
    if file_name == "vllm.env":
        return "not_on_disk", None
    if file_name == "vllm-llama.env":
        return "running", "OK: started on :8000 (simulated)"
    return "downloaded", None


class OrchestratorSimulation:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._runtime: dict[str, dict[str, Any]] = {}
        self._pending: set[str] = set()

    def _get_or_init(self, config_id: str) -> dict[str, Any]:
        if config_id not in self._runtime:
            s, m = _default_initial_state(config_id)
            self._runtime[config_id] = {"state": s, "lastRunMessage": m}
        return self._runtime[config_id]

    def _known_config_id(self, config_id: str) -> bool:
        return config_id in set(config_files.list_env_filenames())

    def _row_state_from_disk_and_runtime(
        self, env_text: str, r: dict[str, Any]
    ) -> ModelRuntimeState:
        """In-flight and running stay simulated; not_on_disk / downloaded follow MODELS_DIR when set."""
        rt: ModelRuntimeState = r["state"]
        if rt == "downloading":
            return "downloading"
        if rt == "running":
            root = get_models_path()
            mid = parse_default_model_name(env_text)
            if (
                root is not None
                and mid
                and not model_weights_appear_on_disk(root, mid)
            ):
                return "not_on_disk"
            return "running"

        root = get_models_path()
        mid = parse_default_model_name(env_text)
        if root is not None and mid is not None:
            return (
                "downloaded"
                if model_weights_appear_on_disk(root, mid)
                else "not_on_disk"
            )
        if root is not None and mid is None:
            return "not_on_disk"
        return rt

    def _sync_runtime_to_models_dir(self, config_id: str) -> None:
        """Align in-memory not_on_disk ↔ downloaded with MODELS_DIR when MODELS_DIR is set."""
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        root = get_models_path()
        mid = parse_default_model_name(t)
        if not root or not mid:
            return
        on_disk = model_weights_appear_on_disk(root, mid)
        r = self._get_or_init(config_id)
        rt: ModelRuntimeState = r["state"]
        if rt in ("downloading", "running"):
            return
        if on_disk and rt == "not_on_disk":
            self._set_runtime(config_id, "downloaded", r["lastRunMessage"])
        elif not on_disk and rt == "downloaded":
            self._set_runtime(
                config_id, "not_on_disk", "Weights not found under MODELS_DIR"
            )

    def add_config(self, file_name: str, text: str) -> None:
        name = config_files.validate_env_filename(file_name)
        if config_files.file_exists(name):
            raise FileExistsError(name)
        config_files.write_env_text(name, text)
        s, m = _default_initial_state(name)
        self._runtime[name] = {"state": s, "lastRunMessage": m}

    def build_table(self) -> tuple[list[dict[str, Any]], int]:
        rows_out: list[dict[str, Any]] = []
        for i, file_name in enumerate(config_files.list_env_filenames(), start=1):
            try:
                t = config_files.read_env_text(file_name)
            except OSError:
                continue
            display = config_files.display_name_for_file(file_name, t)
            r = self._get_or_init(file_name)
            st = self._row_state_from_disk_and_runtime(t, r)
            rows_out.append(
                {
                    "id": f"{file_name}-row",
                    "configId": file_name,
                    "index": i,
                    "fileName": file_name,
                    "name": display,
                    "state": st,
                    "actionsLocked": file_name in self._pending,
                    "lastRunMessage": r["lastRunMessage"],
                }
            )
        return rows_out, len(rows_out)

    def file_text(self, config_id: str) -> tuple[str, str] | None:
        try:
            t = config_files.read_env_text(config_id)
        except (ValueError, FileNotFoundError, OSError):
            return None
        return config_id, t

    def _set_runtime(self, config_id: str, state: ModelRuntimeState, msg: str | None) -> None:
        self._runtime[config_id] = {"state": state, "lastRunMessage": msg}

    async def action_download(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        mid = parse_default_model_name(t)
        root = get_models_path()

        if root is not None and not mid:
            async with self._lock:
                self._set_runtime(
                    config_id,
                    "not_on_disk",
                    "Add DEFAULT_MODEL_NAME= to the .env to download from Hugging Face",
                )
            return

        if root is not None and mid:
            async with self._lock:
                self._sync_runtime_to_models_dir(config_id)
                r = self._get_or_init(config_id)
                if r["state"] != "not_on_disk":
                    return
                self._set_runtime(
                    config_id, "downloading", "Downloading model (see logs for %…)"
                )
                self._pending.add(config_id)
            try:
                await asyncio.to_thread(download_snapshot_for_config, mid, root)
            except Exception as e:
                logger.exception("action_download failed for %s", config_id)
                async with self._lock:
                    self._set_runtime(
                        config_id, "not_on_disk", f"Download failed: {e!s}"[:200]
                    )
            else:
                async with self._lock:
                    r2 = self._get_or_init(config_id)
                    if r2["state"] == "downloading":
                        self._set_runtime(
                            config_id, "downloaded", "Weights on disk"
                        )
            finally:
                async with self._lock:
                    self._pending.discard(config_id)
            return

        async with self._lock:
            self._sync_runtime_to_models_dir(config_id)
            r = self._get_or_init(config_id)
            if r["state"] != "not_on_disk":
                return
            self._set_runtime(config_id, "downloading", None)
        await asyncio.sleep(0.7)
        async with self._lock:
            r = self._get_or_init(config_id)
            if r["state"] != "downloading":
                return
            self._set_runtime(
                config_id, "downloaded", "Weights on disk (simulated; set MODELS_DIR for real download)"
            )

    async def action_start(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        async with self._lock:
            self._sync_runtime_to_models_dir(config_id)
            r = self._get_or_init(config_id)
            if r["state"] != "downloaded" or config_id in self._pending:
                return
            self._pending.add(config_id)
        try:
            await asyncio.sleep(0.45)
            async with self._lock:
                self._set_runtime(
                    config_id,
                    "running",
                    "OK: started on :8000 (simulated)",
                )
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    async def action_stop(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        async with self._lock:
            self._sync_runtime_to_models_dir(config_id)
            r = self._get_or_init(config_id)
            if r["state"] != "running" or config_id in self._pending:
                return
            self._pending.add(config_id)
        try:
            await asyncio.sleep(0.4)
            async with self._lock:
                self._set_runtime(
                    config_id,
                    "downloaded",
                    "Last run: stopped (simulated)",
                )
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    async def action_delete_model(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        mid = parse_default_model_name(t)
        root = get_models_path()

        if root is not None and mid:
            async with self._lock:
                self._sync_runtime_to_models_dir(config_id)
                r = self._get_or_init(config_id)
                st = r["state"]
                if st in ("not_on_disk", "downloading") or config_id in self._pending:
                    return
                self._pending.add(config_id)
            try:
                try:
                    await asyncio.to_thread(delete_model_weight_dirs, root, mid)
                except OSError as e:
                    logger.exception("delete model weights for %s", config_id)
                    async with self._lock:
                        self._set_runtime(
                            config_id,
                            "downloaded",
                            f"Delete failed: {e!s}"[:200],
                        )
                else:
                    async with self._lock:
                        self._set_runtime(
                            config_id,
                            "not_on_disk",
                            "Model weights removed from disk",
                        )
            finally:
                async with self._lock:
                    self._pending.discard(config_id)
            return

        if root is not None and not mid:
            logger.warning("delete model weights: no DEFAULT_MODEL_NAME in %s", config_id)
            return

        async with self._lock:
            self._sync_runtime_to_models_dir(config_id)
            r = self._get_or_init(config_id)
            st = r["state"]
            if st in ("not_on_disk", "downloading") or config_id in self._pending:
                return
            self._pending.add(config_id)
            ms = 0.55 if st == "running" else 0.4
        try:
            await asyncio.sleep(ms)
            async with self._lock:
                self._set_runtime(
                    config_id,
                    "not_on_disk",
                    "Model weights no longer on disk (simulated; set MODELS_DIR to delete for real)",
                )
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    def action_delete_config(self, config_id: str) -> bool:
        if not self._known_config_id(config_id):
            return False
        ok = config_files.delete_env_file(config_id)
        if ok:
            self._pending.discard(config_id)
            self._runtime.pop(config_id, None)
        return ok


state = OrchestratorSimulation()
