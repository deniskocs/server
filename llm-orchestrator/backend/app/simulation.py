"""Runtime state; config bodies live in CONFIGS_DIR as `*.env` files. vLLM is driven only via Docker."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Literal

from . import config_files
from .docker_vllm_runtime import (
    require_vllm_docker,
    run_vllm_container,
    stop_vllm_container,
)
from .hf_download import download_snapshot_for_config
from .model_disk import (
    delete_model_weight_dirs,
    get_models_path,
    model_weights_appear_on_disk,
    parse_default_model_name,
)
from .vllm_env import parse_env_key_values, require_port_for_vllm_start
from .vllm_liveness import is_vllm_serving_config_env, wait_until_vllm_reachable

logger = logging.getLogger(__name__)

ModelRuntimeState = Literal["not_on_disk", "downloading", "downloaded", "running"]


def format_config_file_text(doc: dict[str, Any]) -> str:
    v = doc["vllm"]
    lines = [
        f"# llm-orchestrator/vllm-runner/llm-configs/{doc['fileName']}",
        f"DEFAULT_MODEL_NAME={doc['defaultModelName']}",
        f"SERVED_MODEL_NAME={doc['servedModelName']}",
        "",
        "# Сервер (deploy-vllm + docker-entrypoint.sh; PORT обязателен для Start в оркестраторе)",
        "PORT=8000",
        "HOST=0.0.0.0",
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
        return "downloaded", None
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
        """
        not_on_disk / downloaded from MODELS_DIR; **running** only if /v1/models is up on PORT
        (see vllm_liveness: VLLM_LIVENESS_HOST for probing from a container).
        """
        rt: ModelRuntimeState = r["state"]
        if rt == "downloading":
            return "downloading"

        live = is_vllm_serving_config_env(env_text)
        root = get_models_path()
        mid = parse_default_model_name(env_text)

        if root is not None and mid is not None and not model_weights_appear_on_disk(
            root, mid
        ):
            return "not_on_disk"
        if root is not None and mid is None:
            return "not_on_disk"

        if live:
            return "running"
        if root is not None and mid is not None:
            return "downloaded"
        return "downloaded" if rt in ("downloaded", "running") else rt

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

    def update_config_text(self, config_id: str, text: str) -> None:
        if not self._known_config_id(config_id):
            raise FileNotFoundError(config_id)
        if config_id in self._pending:
            raise ValueError(
                "This config has an action in progress; try again in a moment"
            )
        config_files.write_env_text(config_id, text)
        self._sync_runtime_to_models_dir(config_id)

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
        logger.info("action_download: begin config_id=%s", config_id)
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        mid = parse_default_model_name(t)
        root = get_models_path()

        if root is not None and not mid:
            logger.warning("action_download: no DEFAULT_MODEL_NAME in %s", config_id)
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
                    logger.info(
                        "action_download: skip (state=%s, not not_on_disk)",
                        r["state"],
                    )
                    return
                self._set_runtime(
                    config_id, "downloading", "Downloading model (see logs for %…)"
                )
                self._pending.add(config_id)
            try:
                logger.info(
                    "action_download: huggingface snapshot_download model_id=%r root=%s",
                    mid,
                    root,
                )
                await asyncio.to_thread(download_snapshot_for_config, mid, root)
            except Exception as e:
                logger.exception("action_download failed for %s", config_id)
                async with self._lock:
                    self._set_runtime(
                        config_id, "not_on_disk", f"Download failed: {e!s}"[:200]
                    )
            else:
                logger.info("action_download: finished OK for %s", config_id)
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

        logger.error(
            "action_download: MODELS_DIR unset (cannot download); set MODELS_DIR in API env"
        )
        raise RuntimeError(
            "MODELS_DIR is not set: cannot download weights. "
            "Set MODELS_DIR in the API process (e.g. -e MODELS_DIR=/models) and mount host models."
        )

    async def action_start(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        logger.info("action_start: begin config_id=%s", config_id)
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        env_map = parse_env_key_values(t)
        port = require_port_for_vllm_start(env_map)
        if await asyncio.to_thread(is_vllm_serving_config_env, t):
            logger.info(
                "action_start: vLLM already serving /v1/models on this PORT, skip"
            )
            async with self._lock:
                self._set_runtime(
                    config_id,
                    "running",
                    "vLLM already up: /v1/models OK on PORT (see liveness host)",
                )
            return

        async with self._lock:
            self._sync_runtime_to_models_dir(config_id)
            r = self._get_or_init(config_id)
            if r["state"] not in ("downloaded", "running") or config_id in self._pending:
                logger.info(
                    "action_start: skip (state=%s, pending=%s)",
                    r["state"],
                    config_id in self._pending,
                )
                return
            self._pending.add(config_id)
        try:
            require_vllm_docker()
            config_stem = Path(config_id).stem
            host_listen = (env_map.get("HOST") or "0.0.0.0").strip() or "0.0.0.0"
            logger.info(
                "action_start: docker run CONFIG_STEM=%r PORT=%s HOST=%s",
                config_stem,
                port,
                host_listen,
            )
            run_msg = await asyncio.to_thread(
                run_vllm_container, config_stem, port, host_listen
            )
            logger.info("action_start: waiting for /v1/models (wait_until_vllm_reachable)")
            up = await asyncio.to_thread(wait_until_vllm_reachable, env_map)
            if not up:
                run_msg = (
                    f"{run_msg} — /v1/models not ready in time; "
                    "see vLLM logs; table shows stopped until the API answers"
                )
            ok_live = await asyncio.to_thread(is_vllm_serving_config_env, t)
            logger.info("action_start: liveness after run ok_live=%s", ok_live)
            async with self._lock:
                st: ModelRuntimeState = "running" if ok_live else "downloaded"
                self._set_runtime(config_id, st, run_msg)
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    async def action_stop(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        logger.info("action_stop: begin config_id=%s", config_id)
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        live = await asyncio.to_thread(is_vllm_serving_config_env, t)

        async with self._lock:
            self._sync_runtime_to_models_dir(config_id)
            r = self._get_or_init(config_id)
            if config_id in self._pending:
                logger.info("action_stop: skip (action pending)")
                return
            if not live and r["state"] != "running":
                logger.info(
                    "action_stop: nothing to do live=%s state=%s",
                    live,
                    r["state"],
                )
                return
            self._pending.add(config_id)
        try:
            require_vllm_docker()
            stop_msg = await asyncio.to_thread(stop_vllm_container)
            logger.info("action_stop: %s", stop_msg)
            async with self._lock:
                self._set_runtime(config_id, "downloaded", stop_msg)
        finally:
            async with self._lock:
                self._pending.discard(config_id)

    async def action_delete_model(self, config_id: str) -> None:
        if not self._known_config_id(config_id):
            return
        logger.info("action_delete_model: begin config_id=%s", config_id)
        try:
            t = config_files.read_env_text(config_id)
        except OSError:
            return
        mid = parse_default_model_name(t)
        root = get_models_path()

        if await asyncio.to_thread(is_vllm_serving_config_env, t):
            logger.warning("action_delete_model: vLLM still up on this PORT; stop first")
            return

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
            logger.warning("action_delete_model: no DEFAULT_MODEL_NAME in %s", config_id)
            return

        logger.error("action_delete_model: MODELS_DIR unset")
        raise RuntimeError(
            "MODELS_DIR is not set: cannot delete model directories from disk. "
            "Set MODELS_DIR and mount the models volume."
        )

    def action_delete_config(self, config_id: str) -> bool:
        if not self._known_config_id(config_id):
            return False
        ok = config_files.delete_env_file(config_id)
        if ok:
            self._pending.discard(config_id)
            self._runtime.pop(config_id, None)
        return ok


state = OrchestratorSimulation()
