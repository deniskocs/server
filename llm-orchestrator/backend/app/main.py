"""LLM Orchestrator API — fake delays, same behaviour as the former in-browser simulation."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .simulation import state

app = FastAPI(title="LLM Orchestrator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TableResponse(BaseModel):
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


class ActionBody(BaseModel):
    action: ActionType


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


@app.get("/api/orchestrator/table", response_model=TableResponse)
def get_table() -> TableResponse:
    rows, count = state.build_table()
    return TableResponse(rows=rows, count=count)


@app.get("/api/orchestrator/configs/{config_id}/file-text", response_model=FileTextResponse)
def get_file_text(config_id: str) -> FileTextResponse:
    res = state.file_text(config_id)
    if not res:
        raise HTTPException(status_code=404, detail="Unknown config")
    name, text = res
    return FileTextResponse(fileName=name, text=text)


@app.post("/api/orchestrator/configs/{config_id}/actions", response_model=TableResponse)
async def post_action(config_id: str, body: ActionBody) -> TableResponse:
    a = body.action
    if a == ActionType.download:
        await state.action_download(config_id)
    elif a == ActionType.start:
        await state.action_start(config_id)
    elif a == ActionType.stop:
        await state.action_stop(config_id)
    elif a == ActionType.delete_model:
        await state.action_delete_model(config_id)
    elif a == ActionType.delete_config:
        ok = state.action_delete_config(config_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Unknown config")
    else:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Bad action")
    rows, count = state.build_table()
    return TableResponse(rows=rows, count=count)
