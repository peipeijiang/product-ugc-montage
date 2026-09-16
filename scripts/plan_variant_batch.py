#!/usr/bin/env python3
"""Plan a user-confirmed batch of distinct TikTok montage variants.

This is a planning gate, not a renderer. It reports the combinatorial ceiling
from the accepted visual library and a conservative reviewable cap so the user
can choose how many variants to render after asset QC.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path


def options(point: dict, include_reserve: bool) -> int:
    count = len(point.get("clips") or [])
    if include_reserve and point.get("reserve"):
        count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--include-reserve", action="store_true")
    ap.add_argument("--review-cap", type=int, default=12)
    ap.add_argument("--recommended", type=int, default=6)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    if args.review_cap < 1 or args.recommended < 1:
        raise SystemExit("caps must be positive")
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    points = data.get("selling_points") or []
    if not points:
        raise SystemExit("manifest has no selling_points")
    point_ids = [str(p.get("id", f"point_{i+1}")) for i, p in enumerate(points)]
    choices = []
    counts = {}
    for i, point in enumerate(points):
        point_id = point_ids[i]
        clips = list(point.get("clips") or [])
        if args.include_reserve and point.get("reserve"):
            clips.append(point["reserve"])
        counts[point_id] = len(clips)
        choices.append([str(c.get("variant", c.get("file", "unknown"))) for c in clips])
    if any(value < 1 for value in counts.values()):
        raise SystemExit("every selling point needs at least one accepted clip")
    theoretical = math.prod(counts.values())
    active_clip_count = sum(len(p.get("clips") or []) for p in points)
    reserve_count = sum(1 for p in points if p.get("reserve"))
    # A 12-cut review batch keeps visual QA, claims review, and paid audio
    # accounting tractable while still permitting meaningful A/B testing.
    hard_cap = min(theoretical, args.review_cap)
    recommended = min(hard_cap, args.recommended)
    previews = []
    for index, combo in enumerate(itertools.product(*choices), start=1):
        if index > hard_cap:
            break
        previews.append({"variant_id": f"v{index:02d}", "clips_by_selling_point": dict(zip(point_ids, combo))})
    result = {
        "schema_version": 1,
        "manifest": str(args.manifest),
        "market": data.get("market"),
        "selling_point_count": len(points),
        "accepted_clip_counts": counts,
        "active_clip_count": active_clip_count,
        "reserve_clip_count": reserve_count,
        "include_reserve": args.include_reserve,
        "theoretical_combinations": theoretical,
        "reviewable_hard_cap": hard_cap,
        "recommended_batch": recommended,
        "candidate_preview": previews,
        "user_choice_required": True,
        "policy": {
            "one_variant_requires": "one complete narration, one continuous BGM bed, evidence-linked annotations, and dynamic ending QA",
            "do_not_publish_all_combinations": "near-duplicate combinations must be collapsed after visual/claim/audio review",
            "parallelism": "render variants independently after the shared market/claim/audio gates pass",
            "bgm": "assign passing BGM candidates across variants; do not force one track across the entire batch",
        },
        "selection_prompt": f"Choose a batch size from 1 to {hard_cap}; recommended starting batch: {recommended}.",
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
