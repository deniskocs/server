#!/usr/bin/env python3
"""OpenAI-compatible POST /v1/images/generations + GET /health for HiDream Dev T2I."""

from __future__ import annotations

import base64
import io
import os
import re
import sys
import threading
import time

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoProcessor, PreTrainedTokenizerBase

from models.pipeline import DEFAULT_TIMESTEPS, generate_image
from models.qwen3_vl_transformers import Qwen3VLForConditionalGeneration

_GEN_LOCK = threading.Lock()
_MODEL: Qwen3VLForConditionalGeneration | None = None
_PROCESSOR: AutoProcessor | None = None
_READY = False

_SIZE_RE = re.compile(r"^(\d+)x(\d+)$")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _add_special_tokens(tokenizer) -> None:
    tokenizer.boi_token = "<|boi_token|>"
    tokenizer.bor_token = "<|bor_token|>"
    tokenizer.eor_token = "<|eor_token|>"
    tokenizer.bot_token = "<|bot_token|>"
    tokenizer.tms_token = "<|tms_token|>"


def _get_tokenizer(processor):
    if isinstance(processor, PreTrainedTokenizerBase):
        return processor
    return processor.tokenizer


def _log_cuda_devices() -> None:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "(unset)")
    nvidia = os.environ.get("NVIDIA_VISIBLE_DEVICES", "(unset)")
    print(f"[hidream] CUDA_VISIBLE_DEVICES={visible} NVIDIA_VISIBLE_DEVICES={nvidia}", flush=True)
    if not torch.cuda.is_available():
        return
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        free, total = torch.cuda.mem_get_info(i)
        print(
            f"[hidream] cuda:{i} {props.name} "
            f"free={free / 1e9:.2f}GB total={total / 1e9:.2f}GB",
            flush=True,
        )


def _load_model(model_path: str) -> tuple[AutoProcessor, Qwen3VLForConditionalGeneration]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for HiDream inference")

    _log_cuda_devices()
    torch.cuda.empty_cache()

    dtype_name = _env("HIDREAM_DTYPE", "bfloat16").lower()
    dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}.get(
        dtype_name, torch.bfloat16
    )

    # HiDream generate_image() expects a single CUDA device; device_map="auto" splits
    # across GPUs and breaks inference (cuda:0 vs cuda:1 tensor mismatch).
    cuda_device = int(_env("HIDREAM_CUDA_DEVICE", "0"))
    gpu_mem = _env("HIDREAM_GPU_MAX_MEMORY", "22GiB")

    print(
        f"[hidream] Loading from {model_path} "
        f"(dtype={dtype_name}, device=cuda:{cuda_device}, max_memory={gpu_mem})",
        flush=True,
    )
    processor = AutoProcessor.from_pretrained(model_path)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_path,
        dtype=dtype,
        low_cpu_mem_usage=True,
        device_map={"": cuda_device},
        max_memory={cuda_device: gpu_mem},
    ).eval()
    _add_special_tokens(_get_tokenizer(processor))
    print(f"[hidream] Model ready (device_map={getattr(model, 'hf_device_map', 'cuda')})", flush=True)
    return processor, model


def preload_model() -> None:
    """Load weights before uvicorn starts (entrypoint)."""
    global _MODEL, _PROCESSOR, _READY
    model_path = os.environ.get("MODEL_PATH")
    if not model_path:
        print("❌ MODEL_PATH is not set", file=sys.stderr)
        sys.exit(1)
    _PROCESSOR, _MODEL = _load_model(model_path)
    _READY = True


def _parse_size(size: str) -> tuple[int, int]:
    match = _SIZE_RE.match(size.strip())
    if not match:
        raise HTTPException(status_code=400, detail=f"Invalid size {size!r}; use WIDTHxHEIGHT, e.g. 1024x1024")
    width, height = int(match.group(1)), int(match.group(2))
    if width < 64 or height < 64 or width > 2048 or height > 2048:
        raise HTTPException(status_code=400, detail="size width/height must be between 64 and 2048")
    return width, height


class ImageGenerationRequest(BaseModel):
    model: str | None = None
    prompt: str
    n: int = Field(default=1, ge=1)
    size: str = Field(default_factory=lambda: _env("HIDREAM_DEFAULT_SIZE", "1024x1024"))
    response_format: str = "b64_json"
    seed: int | None = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: list[dict[str, str]]


app = FastAPI(title="hidream-runner")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if not _READY or _MODEL is None or _PROCESSOR is None:
        raise HTTPException(status_code=503, detail="model not ready")
    return {"status": "ready"}


@app.post("/v1/images/generations", response_model=ImageGenerationResponse)
def images_generations(body: ImageGenerationRequest) -> ImageGenerationResponse:
    served = _env("SERVED_MODEL_NAME", "HiDream-ai/HiDream-O1-Image-Dev-2604")
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    if body.model and body.model != served:
        raise HTTPException(status_code=400, detail=f"Unknown model {body.model!r}; served model is {served!r}")

    if body.n != 1:
        raise HTTPException(status_code=400, detail="Only n=1 is supported")

    if body.response_format != "b64_json":
        raise HTTPException(status_code=400, detail="Only response_format=b64_json is supported")

    width, height = _parse_size(body.size)
    seed = body.seed if body.seed is not None else int(_env("HIDREAM_DEFAULT_SEED", "32"))

    assert _MODEL is not None and _PROCESSOR is not None

    with _GEN_LOCK:
        try:
            image = generate_image(
                model=_MODEL,
                processor=_PROCESSOR,
                prompt=prompt,
                ref_image_paths=None,
                height=height,
                width=width,
                num_inference_steps=28,
                guidance_scale=0.0,
                shift=1.0,
                timesteps_list=DEFAULT_TIMESTEPS,
                scheduler_name="flash",
                seed=seed,
                noise_scale_start=8.0,
                noise_scale_end=8.0,
                noise_clip_std=0.0,
            )
        except torch.cuda.OutOfMemoryError as exc:
            raise HTTPException(status_code=500, detail=f"CUDA OOM: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return ImageGenerationResponse(
        created=int(time.time()),
        data=[{"b64_json": b64}],
    )


if os.environ.get("HIDREAM_SKIP_PRELOAD") != "1":
    preload_model()
