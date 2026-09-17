#!/usr/bin/env python3
"""Preflight the deterministic parts of an AI-managed montage."""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edit-dir", type=Path)
    ap.add_argument("--market-profile", type=Path)
    args = ap.parse_args()
    checks: list[tuple[str, bool, str]] = []
    for binary in ("ffmpeg", "ffprobe"):
        path = shutil.which(binary)
        checks.append((binary, bool(path), path or "not on PATH"))
    if shutil.which("ffmpeg"):
        filters = subprocess.check_output(["ffmpeg", "-hide_banner", "-filters"], stderr=subprocess.STDOUT, text=True)
        checks.append(("libass/subtitles", " subtitles " in filters or " ass " in filters, "available" if " subtitles " in filters or " ass " in filters else "missing; ASS render blocked"))
    for module in ('PIL', 'fontTools', 'jsonschema', 'numpy'):
        checks.append((module, importlib.util.find_spec(module) is not None, 'local dependency'))
    if args.market_profile:
        try:
            from contracts import load_market
            market = load_market(args.market_profile)
            checks.append(('market/font', True, market['locale']))
        except Exception as exc:
            checks.append(('market/font', False, str(exc)))
    if args.edit_dir:
        checks.append(("edit_dir", args.edit_dir.exists() and args.edit_dir.is_dir(), str(args.edit_dir)))
        checks.append(("edit_dir_writable", args.edit_dir.exists() and bool(__import__("os").access(args.edit_dir, __import__("os").W_OK)), str(args.edit_dir)))
    ok = True
    for name, passed, detail in checks:
        print(f"{'OK' if passed else 'FAIL'}\t{name}\t{detail}")
        ok &= passed
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
