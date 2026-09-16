#!/usr/bin/env python3
"""Score whether a rendered ending is visually dynamic and intentional.

Usage: score_dynamic_ending.py video.mp4 [--edl edl.json] [-o report.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def frames(video: Path, duration: float, directory: Path) -> list[Path]:
    paths = []
    for i, t in enumerate((max(0.0, duration - 2.0), max(0.0, duration - 1.0), max(0.0, duration - 0.15))):
        out = directory / f"f{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=320:-1", str(out)], check=True)
        paths.append(out)
    return paths


def motion_score(paths: list[Path]) -> float:
    try:
        from PIL import Image, ImageChops, ImageStat
        images = [Image.open(p).convert("RGB") for p in paths]
        diffs = []
        for a, b in zip(images, images[1:]):
            diffs.append(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / (3 * 255))
        return min(60.0, sum(diffs) / max(1, len(diffs)) * 240.0)
    except Exception:
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--edl", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    raw = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(args.video)], text=True)
    duration = float(raw.strip())
    with tempfile.TemporaryDirectory(prefix="ugc-ending-") as td:
        motion = motion_score(frames(args.video, duration, Path(td)))
    source_bonus = 0.0
    freeze_penalty = 0.0
    sources: list[str] = []
    if args.edl and args.edl.exists():
        e = json.loads(args.edl.read_text(encoding="utf-8"))
        ranges = e.get("ranges") or e.get("segments") or []
        for r in ranges[-3:]:
            sources.append(str(r.get("source", r.get("file", ""))))
        source_bonus = 20.0 if len(set(sources)) >= 2 else 8.0
        if any("clone" in s.lower() or "freeze" in s.lower() for s in sources):
            freeze_penalty = 30.0
    score = round(max(0.0, min(100.0, motion + source_bonus + 20.0 - freeze_penalty)), 1)
    report = {"video": str(args.video), "duration_seconds": duration, "score": score, "grade": "dynamic" if score >= 70 else ("borderline" if score >= 45 else "static_risk"), "motion_component": round(motion, 1), "source_diversity_component": source_bonus, "freeze_penalty": freeze_penalty, "tail_sources": sources, "method": "frame differences at duration-2.0s, -1.0s, -0.15s plus EDL tail-source diversity"}
    out = args.output or args.video.with_name("dynamic_ending_score.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
