#!/usr/bin/env python3
"""Apply HiDream upstream patches after git clone."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PIPELINE = Path("/app/hidream/models/pipeline.py")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        print(f"❌ patch target not found: {label}", file=sys.stderr)
        sys.exit(1)
    return text.replace(old, new, 1)


def main() -> None:
    text = PIPELINE.read_text()
    notes: list[str] = ["native low-res enabled"]

    disable_flash = os.environ.get("HIDREAM_DISABLE_FLASH_ATTN", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    if disable_flash:
        text = _replace_once(
            text,
            '"use_flash_attn": True',
            '"use_flash_attn": False',
            "use_flash_attn",
        )
        notes.append("flash_attn off")
    else:
        notes.append("flash_attn on")

    old_snap = (
        "        w, h = find_closest_resolution(width, height)\n"
        "        if w != width or h != height:\n"
        '            print(f"[warning] Resolution snapped from {width}x{height} to {w}x{h}")\n'
        "            width, height = w, h"
    )
    new_snap = (
        "        import os as _os\n"
        '        if _os.environ.get("HIDREAM_SNAP_RESOLUTION", "0").lower() in ("1", "true", "yes"):\n'
        "            w, h = find_closest_resolution(width, height)\n"
        "            if w != width or h != height:\n"
        '                print(f"[warning] Resolution snapped from {width}x{height} to {w}x{h}")\n'
        "                width, height = w, h\n"
        "        else:\n"
        "            w = max(PATCH_SIZE, width // PATCH_SIZE * PATCH_SIZE)\n"
        "            h = max(PATCH_SIZE, height // PATCH_SIZE * PATCH_SIZE)\n"
        "            if w != width or h != height:\n"
        '                print(f"[info] Resolution aligned to patch grid {width}x{height} -> {w}x{h}")\n'
        "            width, height = w, h"
    )
    text = _replace_once(text, old_snap, new_snap, "resolution snap")

    PIPELINE.write_text(text)
    print(f"✅ HiDream pipeline patched ({', '.join(notes)})", flush=True)


if __name__ == "__main__":
    main()
