#!/usr/bin/env python3
"""Deterministic checks for the unified product-ad audio contract.

The script is intentionally dependency-free. It checks the final MP4, the
complete narration, optional BGM/script/annotation inputs, and an optional
video-only intermediate. It does not perform ASR; feed the final ASR result to
the report layer when available.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def probe(path: Path) -> dict:
    p = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,duration",
            "-of",
            "json",
            str(path),
        ]
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"ffprobe failed for {path}")
    return json.loads(p.stdout or "{}")


def duration(info: dict) -> float:
    try:
        return float(info.get("format", {}).get("duration", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def streams(info: dict, kind: str) -> list[dict]:
    return [s for s in info.get("streams", []) if s.get("codec_type") == kind]


def mean_volume(path: Path) -> float | None:
    p = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ]
    )
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", p.stderr)
    return float(match.group(1)) if match else None


def black_frames(path: Path) -> list[str]:
    p = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            "blackdetect=d=0.10:pix_th=0.10",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    return re.findall(r"black_start:\s*([0-9.]+).*?black_end:\s*([0-9.]+)", p.stderr)


def script_sentences(script: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?])\s*", script.strip())
    return [re.sub(r"\s+", "", p) for p in parts if p.strip()]


def annotation_check(path: Path, video_duration: float) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("annotations", [])
    invalid = []
    for item in items:
        try:
            start, end = float(item["start"]), float(item["end"])
        except (KeyError, TypeError, ValueError):
            invalid.append(item.get("id", "<missing-id>"))
            continue
        if start < 0 or end <= start or end > video_duration + 0.05:
            invalid.append(item.get("id", "<missing-id>"))
    return {"count": len(items), "invalid_ids": invalid, "pass": not invalid}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--narration", type=Path, required=True)
    parser.add_argument("--bgm", type=Path)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--video-only", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    for binary in ("ffprobe", "ffmpeg"):
        if not shutil.which(binary):
            print(json.dumps({"status": "blocked", "error": f"{binary} not found"}, ensure_ascii=False))
            return 2

    checks: dict[str, object] = {}
    final_info = probe(args.video)
    narration_info = probe(args.narration)
    video_duration = duration(final_info)
    narration_duration = duration(narration_info)
    audio_count = len(streams(final_info, "audio"))
    checks["final_audio_stream_count"] = {"value": audio_count, "pass": audio_count == 1}
    checks["narration_tail"] = {
        "video_duration": round(video_duration, 3),
        "narration_duration": round(narration_duration, 3),
        "tail_seconds": round(video_duration - narration_duration, 3),
        "pass": narration_duration > 0 and 0.8 <= video_duration - narration_duration <= 4.0,
    }

    if args.video_only:
        only_info = probe(args.video_only)
        only_audio = len(streams(only_info, "audio"))
        checks["source_audio_muted"] = {"audio_stream_count": only_audio, "pass": only_audio == 0}

    if args.bgm:
        bgm_info = probe(args.bgm)
        bgm_volume, narration_volume = mean_volume(args.bgm), mean_volume(args.narration)
        gap = None if bgm_volume is None or narration_volume is None else narration_volume - bgm_volume
        checks["bgm_continuity"] = {
            "bgm_duration": round(duration(bgm_info), 3),
            "pass": duration(bgm_info) > 0,
        }
        checks["bgm_relative_loudness"] = {
            "narration_mean_db": narration_volume,
            "bgm_mean_db": bgm_volume,
            "narration_minus_bgm_db": gap,
            "target_db": "8-12",
            "pass": gap is not None and 8.0 <= gap <= 12.0,
        }

    if args.script:
        sentences = script_sentences(args.script.read_text(encoding="utf-8"))
        normalized = [s.casefold() for s in sentences]
        duplicates = sorted({s for s in normalized if normalized.count(s) > 1})
        tail_ok = bool(sentences and re.search(r"[。！？!?」』]$", sentences[-1]))
        checks["script_integrity"] = {
            "sentence_count": len(sentences),
            "duplicate_sentences": duplicates,
            "complete_tail_punctuation": tail_ok,
            "pass": bool(sentences) and not duplicates and tail_ok,
        }

    if args.annotations:
        checks["annotation_coverage"] = annotation_check(args.annotations, video_duration)

    black = black_frames(args.video)
    checks["black_frames"] = {"segments": black, "pass": not black}
    checks["av_duration_sync"] = {
        "delta_seconds": round(abs(video_duration - narration_duration), 3),
        "pass": 0.0 <= video_duration - narration_duration <= 4.0,
    }

    failed = [name for name, value in checks.items() if isinstance(value, dict) and value.get("pass") is False]
    report = {
        "schema_version": 1,
        "video": str(args.video),
        "status": "fail" if failed else "pass",
        "failed_checks": failed,
        "checks": checks,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
