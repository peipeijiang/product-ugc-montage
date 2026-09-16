#!/usr/bin/env python3
"""Validate a product annotation plan with stdlib-only checks.

This intentionally mirrors the reusable JSON schema without requiring jsonschema.
Usage: validate_annotations.py plan.json [--schema schema.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    args = ap.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read JSON: {exc}")
        return 2
    errors: list[str] = []
    required = {"version", "market_profile_id", "canvas", "style", "annotations"}
    if not isinstance(data, dict):
        print("ERROR: plan must be an object")
        return 2
    for key in sorted(required - data.keys()):
        fail(errors, f"missing top-level field: {key}")
    if data.get("version") != 1:
        fail(errors, "version must equal 1")
    style = data.get("style")
    if not isinstance(style, dict):
        fail(errors, "style must be an object")
    else:
        for key in ("template_id", "card", "text", "accent", "safe_zone"):
            if key not in style:
                fail(errors, f"style missing field: {key}")
        card = style.get("card", {})
        text = style.get("text", {})
        safe = style.get("safe_zone", {})
        for key in ("color", "opacity", "padding_px"):
            if key not in card:
                fail(errors, f"card missing field: {key}")
        for key in ("font_family", "font_size_px", "color", "outline_px"):
            if key not in text:
                fail(errors, f"text missing field: {key}")
        for key in ("x_min", "x_max", "y_min", "y_max"):
            if key not in safe:
                fail(errors, f"safe_zone missing field: {key}")
        if all(k in safe for k in ("x_min", "x_max", "y_min", "y_max")):
            if not (0 <= safe["x_min"] < safe["x_max"] <= 1 and 0 <= safe["y_min"] < safe["y_max"] <= 1):
                fail(errors, "safe_zone bounds must be ordered within 0..1")
    annotations = data.get("annotations")
    if not isinstance(annotations, list) or not annotations:
        fail(errors, "annotations must be a non-empty array")
    else:
        last_end = 0.0
        seen: set[str] = set()
        for i, ann in enumerate(annotations):
            if not isinstance(ann, dict):
                fail(errors, f"annotations[{i}] must be an object")
                continue
            for key in ("id", "start", "end", "text", "claim_id", "evidence", "anchor", "animation"):
                if key not in ann:
                    fail(errors, f"annotations[{i}] missing field: {key}")
            ident = ann.get("id")
            if ident in seen:
                fail(errors, f"duplicate annotation id: {ident}")
            seen.add(str(ident))
            try:
                start, end = float(ann["start"]), float(ann["end"])
                if start < 0 or end <= start:
                    fail(errors, f"annotations[{i}] invalid interval")
                if start < last_end - 0.001:
                    fail(errors, f"annotations[{i}] overlaps prior annotation; overlap must be intentional and explicit")
                last_end = max(last_end, end)
            except (KeyError, TypeError, ValueError):
                fail(errors, f"annotations[{i}] start/end must be numbers")
            if isinstance(ann.get("text"), str) and not (1 <= len(ann["text"]) <= 80):
                fail(errors, f"annotations[{i}] text length must be 1..80")
            if not isinstance(ann.get("evidence"), list) or not ann["evidence"]:
                fail(errors, f"annotations[{i}] evidence must be non-empty")
    if errors:
        print("INVALID")
        for err in errors:
            print(f"- {err}")
        return 1
    print(f"VALID: {args.plan} ({len(annotations)} annotation(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
