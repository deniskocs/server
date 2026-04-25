"""LLM Orchestrator API: configs on disk, vLLM via Docker, models list + actions."""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config_files
from .simulation import state

logger = logging.getLogger(__name__)
app = FastAPI(title="LLM Orchestrator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModelsResponse(BaseModel):
    rows: list[dict[str, Any]]
    count: int


class FileTextResponse(BaseModel):
    fileName: str
    text: str


class ActionType(str, Enum):
    download = "download"
    start = "start"
    stop = "stop"
    delete_model = "delete_model"
    delete_config = "delete_config"


class ModelsActionBody(BaseModel):
    action: ActionType
    configFile: str

    model_config = {"extra": "forbid"}


class AddConfigBody(BaseModel):
    fileName: str
    text: str


class UpdateConfigBody(BaseModel):
    text: str


def _normalize_config_file(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(400, detail="configFile is required")
    base = s.replace("\\", "/").rstrip("/").split("/")[-1]
    if not base.endswith(".env"):
        base = f"{base}.env"
    try:
        return config_files.validate_env_filename(base)
    except ValueError as e:
        raise HTTPException(400, detail=str(e)) from e


def _config_must_exist(name: str) -> None:
    if name not in set(config_files.list_env_filenames()):
        raise HTTPException(404, detail="Unknown config")


@app.get("/api/health")
def health() -> dict[str, str]:
    out: dict[str, str] = {"status": "ok"}
    m = os.environ.get("MODELS_DIR")
    c = os.environ.get("CONFIGS_DIR")
    if m:
        out["modelsDir"] = m
    if c:
        out["configsDir"] = c
    return out


@app.get("/api/orchestrator/models", response_model=ModelsResponse)
def get_models() -> ModelsResponse:
    rows, count = state.build_table()
    return ModelsResponse(rows=rows, count=count)


@app.post("/api/orchestrator/configs", response_model=ModelsResponse)
def post_add_config(body: AddConfigBody) -> ModelsResponse:
    try:
        state.add_config(body.fileName, body.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileExistsError as e:
        raise HTTPException(
            status_code=409,
            detail="A config with this file name already exists",
        ) from e
    rows, count = state.build_table()
    return ModelsResponse(rows=rows, count=count)


@app.get("/api/orchestrator/configs/{config_id}/file-text", response_model=FileTextResponse)
def get_file_text(config_id: str) -> FileTextResponse:
    res = state.file_text(config_id)
    if not res:
        raise HTTPException(status_code=404, detail="Unknown config")
    name, text = res
    return FileTextResponse(fileName=name, text=text)


@app.put("/api/orchestrator/configs/{config_id}/file-text", response_model=ModelsResponse)
def put_file_text(config_id: str, body: UpdateConfigBody) -> ModelsResponse:
    try:
        state.update_config_text(config_id, body.text)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Unknown config") from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    rows, count = state.build_table()
    return ModelsResponse(rows=rows, count=count)


@app.post("/api/orchestrator/models/actions", response_model=ModelsResponse)
async def post_models_action(body: ModelsActionBody) -> ModelsResponse:
    config_id = _normalize_config_file(body.configFile)
    _config_must_exist(config_id)
    a = body.action
    if a == ActionType.download:
        try:
            await state.action_download(config_id)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    elif a == ActionType.start:
        try:
            await state.action_start(config_id)
        except ValueError as e:
            logger.warning(
                "POST models/actions start: 400 configFile=%s reason=%s",
                config_id,
                e,
            )
            raise HTTPException(status_code=400, detail=str(e)) from e
        except FileNotFoundError as e:
            # vLLM: .env in CONFIGS_DIR, forwarded as -e (no /llm-configs in container)
            logger.warning(
                "POST models/actions start: 400 configFile=%s reason=%s",
                config_id,
                e,
            )
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            logger.error(
                "POST models/actions start: 500 configFile=%s reason=%s",
                config_id,
                e,
            )
            raise HTTPException(status_code=500, detail=str(e)) from e
    elif a == ActionType.stop:
        try:
            await state.action_stop(config_id)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    elif a == ActionType.delete_model:
        try:
            await state.action_delete_model(config_id)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    elif a == ActionType.delete_config:
        ok = state.action_delete_config(config_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Unknown config")
    else:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Bad action")
    rows, count = state.build_table()
    return ModelsResponse(rows=rows, count=count)
