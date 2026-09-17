#!/usr/bin/env python3
"""Render validated, market-bound annotations as separate ASS card/text layers."""
import argparse
import json
from pathlib import Path
from contracts import digest, load_market
from validate_annotations import validate

def ass_time(seconds):
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

def bgr(value):
    value = value.lstrip('#')
    return (value[4:6]+value[2:4]+value[0:2]).upper()

def rounded_rect(w, h, r):
    # ASS cubic Bezier path; separate opaque-border styles would lose text outline.
    w, h, r = (round(x,2) for x in (w,h,r))
    k = r * .55228475
    return (f'm {r} 0 l {w-r} 0 b {w-r+k} 0 {w} {r-k} {w} {r} '
            f'l {w} {h-r} b {w} {h-r+k} {w-r+k} {h} {w-r} {h} '
            f'l {r} {h} b {r-k} {h} 0 {h-r+k} 0 {h-r} '
            f'l 0 {r} b 0 {r-k} {r-k} 0 {r} 0')

def motion(ann, layout, animation):
    x,y = layout['x'],layout['y']
    mode = ann['animation']
    ms = animation['duration_ms']
    tail = animation['out_duration_ms'] if animation['out']=='fade' else 0
    loc = rf'\pos({x:.2f},{y:.2f})'
    if mode == 'slide-up':
        loc = rf'\move({x:.2f},{y+24:.2f},{x:.2f},{y:.2f},0,{ms})'
    if mode == 'slide-left':
        loc = rf'\move({x+24:.2f},{y:.2f},{x:.2f},{y:.2f},0,{ms})'
    if mode == 'scale-in':
        loc += rf'\fscx85\fscy85\t(0,{ms},1,\fscx100\fscy100)'
    return loc + rf'\fad({ms if mode != "none" else 0},{tail})'

def render(data, market, layouts):
    w,h = map(int,data['canvas'].split('x'))
    style=data['style']
    tx,card=style['text'],style['card']
    font=market['typography']['font_family']
    if any(ch in font for ch in ',\n\r'):
        raise ValueError('invalid ASS font family')
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ProductTag,{font},{tx['font_size_px']},&H00{bgr(tx['color'])},&H00{bgr(tx['color'])},&H00{bgr(tx['outline_color'])},&H80000000,{-1 if tx['bold'] else 0},0,0,0,100,100,0,0,1,{tx['outline_px']},{tx['shadow_px']},5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines=[header]
    by_id={l['id']:l for l in layouts}
    for ann in data['annotations']:
        box=by_id[ann['id']]
        tags=motion(ann,box,style['animation'])
        alpha=round((1-card['opacity'])*255)
        path=rounded_rect(box['width'],box['height'],card['corner_radius_px'])
        background=rf'{{{tags}\an5\p1\bord0\shad0\1c&H{bgr(card["color"])}&\1a&H{alpha:02X}&}}'+path
        content=ann['text']
        if ann.get('accent_text'):
            accent=ann['accent_text']
            content=content.replace(accent,rf'{{\1c&H{bgr(style["accent"])}&}}'+accent+
                                    rf'{{\1c&H{bgr(tx["color"])}&}}',1)
        content=content.replace('\n',r'\N')
        foreground='{'+tags+r'\q2}'+content
        for layer,value in ((0,background),(1,foreground)):
            lines.append(f'Dialogue: {layer},{ass_time(ann["start"])},{ass_time(ann["end"])},ProductTag,,0,0,0,,{value}\n')
    return ''.join(lines)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path)
    ap.add_argument('--market-profile',type=Path,required=True)
    ap.add_argument('--claim-ledger',type=Path,required=True)
    ap.add_argument('--duration',type=float,required=True)
    ap.add_argument('-o','--output',type=Path)
    args=ap.parse_args()
    try:
        data=json.loads(args.plan.read_text())
        market=load_market(args.market_profile)
        errors,layouts=validate(data,market,digest(args.market_profile),
                               json.loads(args.claim_ledger.read_text()),args.duration)
        if errors:
            raise ValueError('; '.join(errors))
        out=args.output or args.plan.with_name('product_annotations.ass')
        out.write_text(render(data,market,layouts),encoding='utf-8')
        receipt={'schema_version':2,'plan_sha256':digest(args.plan),
                 'market_profile_sha256':digest(args.market_profile),
                 'font_file':market['typography']['font_file'],
                 'font_sha256':digest(market['typography']['font_file']),
                 'ass_sha256':digest(out),'layouts':layouts,
                 'required_render_step':'Load this exact font in libass fontsdir; inspect rendered frames for shaping and bounds.'}
        out.with_suffix('.receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        print(out)
        return 0
    except Exception as exc:
        print(json.dumps({'status':'blocked','error':str(exc)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
