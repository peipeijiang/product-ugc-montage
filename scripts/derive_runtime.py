#!/usr/bin/env python3
"""Derive montage runtime from the real narration duration.

The result is a planning value, not a fixed platform preset. Shot selection
must fill this runtime without freezing or stretching the final picture.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("narration", type=Path)
    ap.add_argument("--headroom", type=float, default=0.4)
    ap.add_argument("--clean-tail", type=float, default=1.0)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    if not shutil.which("ffprobe"):
        raise SystemExit("ffprobe is required")
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(args.narration)],
        text=True,
    )
    narration_duration = float(raw.strip())
    if (not all(math.isfinite(v) for v in (narration_duration,args.headroom,args.clean_tail))
            or narration_duration <= 0 or args.headroom < 0 or args.clean_tail < 0):
        raise SystemExit("duration and margins must be finite; duration positive and margins nonnegative")
    result = {
        "schema_version": 1,
        "narration": str(args.narration),
        "narration_duration_seconds": round(narration_duration, 3),
        "headroom_before_seconds": round(args.headroom, 3),
        "clean_tail_after_seconds": round(args.clean_tail, 3),
        "derived_runtime_seconds": round(narration_duration + args.headroom + args.clean_tail, 3),
        "formula": "narration_duration + headroom_before + clean_tail_after",
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
