#!/usr/bin/env python3
"""Score active asset-library diversity and write a JSON report.

The score is a transparent heuristic, not a substitute for visual review.
Usage: score_asset_library.py library_manifest.json [-o report.json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def probe(path: Path) -> dict:
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate", "-of", "json", str(path)],
            text=True,
        )
        return json.loads(raw)
    except Exception:
        return {}


def token_set(value: str) -> set[str]:
    return {x for x in re.split(r"[^a-z0-9]+", value.lower()) if x}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    d = json.loads(args.manifest.read_text(encoding="utf-8"))
    points = d.get("selling_points") or []
    point_reports = []
    all_variants: list[str] = []
    diversity_values: list[float] = []
    completeness_values: list[float] = []
    for point in points:
        clips = point.get("clips") or []
        variants = [str(c.get("variant", "")) for c in clips]
        angles = [str(c.get("angle", "")) for c in clips]
        unique_angles = len(set(angles)) / max(1, len(angles))
        unique_variants = len(set(variants)) / max(1, len(variants))
        metadata_fields = 0
        metadata_total = max(1, len(clips) * 4)
        for c in clips:
            for key in ("variant", "file", "duration_s", "angle"):
                metadata_fields += int(bool(c.get(key)))
            all_variants.append(str(c.get("variant", "")))
        completeness = metadata_fields / metadata_total
        angle_tokens = set().union(*(token_set(a) for a in angles)) if angles else set()
        semantic_spread = min(1.0, len(angle_tokens) / max(3.0, len(clips) * 2.0))
        point_score = round(100 * (0.40 * unique_angles + 0.25 * unique_variants + 0.20 * semantic_spread + 0.15 * completeness), 1)
        point_reports.append({"id": point.get("id"), "clip_count": len(clips), "unique_angles": len(set(angles)), "score": point_score})
        diversity_values.append(point_score)
        completeness_values.append(completeness)
    cross_point_unique = len(set(all_variants)) / max(1, len(all_variants))
    score = round((sum(diversity_values) / max(1, len(diversity_values))) * 0.85 + cross_point_unique * 15, 1)
    report = {
        "manifest": str(args.manifest),
        "score": score,
        "grade": "strong" if score >= 80 else ("usable" if score >= 65 else "needs_more_variants"),
        "method": {"per_point": "angle uniqueness 40%, variant uniqueness 25%, semantic tag spread 20%, metadata completeness 15%", "cross_point_unique_variant_weight": 15},
        "selling_points": point_reports,
        "recommendations": []
    }
    if score < 80:
        report["recommendations"].append("Add a materially different camera distance or interaction angle for the lowest-scoring selling point.")
    if cross_point_unique < 0.8:
        report["recommendations"].append("Avoid reusing the same variant or composition across selling points.")
    if any(r["clip_count"] < 3 for r in point_reports):
        report["recommendations"].append("Keep at least three active visual variants per confirmed selling point when budget allows.")
    out = args.output or args.manifest.with_name("asset_diversity_score.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
