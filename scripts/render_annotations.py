#!/usr/bin/env python3
"""Convert a product_annotation_plan.json into a reusable ASS overlay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def bgr(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    return f"{value[4:6]}{value[2:4]}{value[0:2]}".upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    d = json.loads(args.plan.read_text(encoding="utf-8"))
    width, height = (int(x) for x in d.get("canvas", "1080x1920").split("x", 1))
    style = d["style"]
    card, text = style["card"], style["text"]
    back_alpha = max(0, min(255, round((1 - float(card["opacity"])) * 255)))
    header = f"""[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: ProductTag,{text['font_family']},{int(text['font_size_px'])},&H00{bgr(text['color'])},&H00{bgr(text['color'])},&H00{bgr('#101010')},&H{back_alpha:02X}{bgr(card['color'])},1,0,0,0,100,100,0,0,3,0,0,5,{int(card['padding_px'])},{int(card['padding_px'])},0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text\n"""
    lines = [header]
    positions = {"center": (width // 2, int(height * 0.48)), "upper-middle": (width // 2, int(height * 0.34)), "lower-middle": (width // 2, int(height * 0.62)), "left-middle": (int(width * 0.28), int(height * 0.50)), "right-middle": (int(width * 0.72), int(height * 0.50))}
    for ann in d["annotations"]:
        x, y = positions.get(ann.get("anchor", "lower-middle"), positions["lower-middle"])
        rendered = str(ann["text"]).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        accent = ann.get("accent_text")
        if accent and accent in rendered:
            rendered = rendered.replace(accent, "{\\c&H00" + bgr(style["accent"]) + "&}" + accent + "{\\c&H00" + bgr(text["color"]) + "&}", 1)
        rendered = "{\\pos(%d,%d)}%s" % (x, y, rendered)
        lines.append(f"Dialogue: 0,{ass_time(float(ann['start']))},{ass_time(float(ann['end']))},ProductTag,,0,0,0,,{rendered}\n")
    out = args.output or args.plan.with_name("product_annotations.ass")
    out.write_text("".join(lines), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
