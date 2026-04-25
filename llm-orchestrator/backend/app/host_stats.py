"""Host metrics: CPU, RAM, optional GPUs (nvidia-smi), MODELS_DIR size + filesystem free space."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


def _parse_gpu_util(s: str) -> int | None:
    s = s.strip().rstrip(" %")
    if not s or s.upper() in ("N/A", "[N/A]"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_power_w(s: str) -> float | None:
    s = s.strip()
    if not s or s.upper() in ("N/A", "[N/A]"):
        return None
    for suffix in (" W", "W"):
        if s.endswith(suffix) and s.upper() != "N/A":
            s = s[: -len(suffix)].strip()
            break
    try:
        return round(float(s), 1)
    except ValueError:
        return None


def _parse_nvidia_smi_line(line: str) -> dict[str, Any] | None:
    """
    Parse one CSV line from nvidia-smi with fields (order matters):
    index, name, memory.total, memory.used, memory.free, utilization.gpu, power.draw
    Commas inside GPU name: join fields between index and the five tail metrics.
    """
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 7:
        return None
    try:
        index = int(parts[0])
        power_w = _parse_power_w(parts[-1])
        util = _parse_gpu_util(parts[-2])
        mem_free = int(float(parts[-3]))
        mem_used = int(float(parts[-4]))
        mem_total = int(float(parts[-5]))
    except (ValueError, IndexError):
        return None
    name = ",".join(parts[1:-5]) if len(parts) > 7 else parts[1]
    return {
        "index": index,
        "name": name,
        "memoryTotalMib": mem_total,
        "memoryUsedMib": mem_used,
        "memoryFreeMib": mem_free,
        "utilizationPercent": util,
        "powerDrawW": power_w,
    }


def _query_gpus() -> list[dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return []
    try:
        p = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.debug("nvidia-smi not usable: %s", e)
        return []
    if p.returncode != 0 or not p.stdout.strip():
        return []
    gpus: list[dict[str, Any]] = []
    for line in p.stdout.strip().splitlines():
        row = _parse_nvidia_smi_line(line)
        if row:
            gpus.append(row)
    return gpus


def _dir_size_bytes(path: Path) -> int:
    if shutil.which("du"):
        try:
            r = subprocess.run(
                ["du", "-sk", str(path.resolve())],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            first = (r.stdout or "").split()
            if first:
                return int(first[0]) * 1024
        except (OSError, subprocess.TimeoutExpired, ValueError) as e:
            logger.debug("du failed for %s: %s", path, e)
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda err: None):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def collect_host_stats() -> dict[str, Any]:
    cpu_percent = float(psutil.cpu_percent(interval=0.12))
    vm = psutil.virtual_memory()
    gpus = _query_gpus()

    raw = os.environ.get("MODELS_DIR", "").strip()
    models: dict[str, Any] | None = None
    if not raw:
        out = {
            "cpuPercent": round(cpu_percent, 1),
            "memory": {
                "totalBytes": vm.total,
                "usedBytes": vm.used,
                "availableBytes": vm.available,
            },
            "gpus": gpus,
            "models": None,
            "modelsDirConfigured": False,
        }
        return out

    models_path = Path(raw).resolve()
    try:
        if not models_path.is_dir():
            out = {
                "cpuPercent": round(cpu_percent, 1),
                "memory": {
                    "totalBytes": vm.total,
                    "usedBytes": vm.used,
                    "availableBytes": vm.available,
                },
                "gpus": gpus,
                "models": None,
                "modelsDirConfigured": True,
                "modelsError": f"Path is not a directory: {raw}",
            }
            return out
        du = shutil.disk_usage(str(models_path))
        size_b = _dir_size_bytes(models_path)
        models = {
            "path": str(models_path),
            "dirSizeBytes": size_b,
            "filesystem": {
                "totalBytes": du.total,
                "usedBytes": du.used,
                "freeBytes": du.free,
            },
        }
    except OSError as e:
        return {
            "cpuPercent": round(cpu_percent, 1),
            "memory": {
                "totalBytes": vm.total,
                "usedBytes": vm.used,
                "availableBytes": vm.available,
            },
            "gpus": gpus,
            "models": None,
            "modelsDirConfigured": True,
            "modelsError": str(e)[:200],
        }

    return {
        "cpuPercent": round(cpu_percent, 1),
        "memory": {
            "totalBytes": vm.total,
            "usedBytes": vm.used,
            "availableBytes": vm.available,
        },
        "gpus": gpus,
        "models": models,
        "modelsDirConfigured": True,
    }
