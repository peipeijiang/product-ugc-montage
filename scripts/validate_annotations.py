#!/usr/bin/env python3
"""Validate actual schema, market/font lock, approved copy, timing and text bounds."""
import argparse
import json
from pathlib import Path
from contracts import digest, load_market, number

SCHEMA = Path(__file__).resolve().parents[1] / 'references/product_annotation.schema.json'

def validate(data, market, market_hash, ledger, duration, schema=SCHEMA):
    import jsonschema
    from PIL import ImageFont
    from fontTools.ttLib import TTFont
    def finite_json(value):
        if isinstance(value,float):
            return number(value)
        if isinstance(value,dict):
            return all(finite_json(v) for v in value.values())
        if isinstance(value,list):
            return all(finite_json(v) for v in value)
        return True
    if not finite_json(data):
        return ['nonfinite JSON numbers are not supported'], []
    errors = [e.message for e in jsonschema.Draft202012Validator(
        json.loads(Path(schema).read_text())).iter_errors(data)]
    if errors:
        return errors, []
    if data['market_profile_id'] != market['id'] or data['locale'] != market['locale']:
        errors.append('annotation market/locale mismatch')
    if data['market_profile_sha256'] != market_hash:
        errors.append('annotation market profile changed')
    if not number(duration) or duration <= 0:
        errors.append('positive final runtime required')
        return errors, []
    width, height = map(int, data['canvas'].split('x'))
    if width > 8192 or height > 8192:
        return ['canvas too large'], []
    typography = market['typography']
    font_path = typography['font_file']
    index = typography.get('font_index', 0)
    tt = TTFont(font_path, fontNumber=index)
    family_names = {r.toUnicode() for r in tt['name'].names if r.nameID in (1, 16)}
    if typography['font_family'] not in family_names:
        errors.append('market font_family does not match font_file')
    cmap = tt.getBestCmap() or {}
    tt.close()
    style = data['style']
    text, card, safe, anim = (style[k] for k in ('text', 'card', 'safe_zone', 'animation'))
    font = ImageFont.truetype(font_path, text['font_size_px'], index=index)
    if not (safe['x_min'] < safe['x_max'] and safe['y_min'] < safe['y_max']):
        return errors + ['safe-zone bounds must be ordered'], []
    x0, x1 = safe['x_min'] * width, safe['x_max'] * width
    y0, y1 = safe['y_min'] * height, safe['y_max'] * height
    claims = {c['id']: c for c in ledger.get('claims', [])}
    layouts, seen, last_end = [], set(), 0
    anchors = {'center': (.5,.5), 'upper-middle': (.5,.25), 'lower-middle': (.5,.75),
               'left-middle': (.25,.5), 'right-middle': (.75,.5)}
    for ann in sorted(data['annotations'], key=lambda a: a['start']):
        ident = ann['id']
        if ident in seen:
            errors.append(f'duplicate annotation ID: {ident}')
        seen.add(ident)
        if not 0 <= ann['start'] < ann['end'] <= duration + .01 or ann['start'] < last_end - .001:
            errors.append(f'invalid/overlapping annotation interval: {ident}')
        last_end = ann['end']
        if (anim['duration_ms'] + anim['out_duration_ms']) / 1000 > ann['end'] - ann['start']:
            errors.append(f'animation exceeds annotation duration: {ident}')
        claim = claims.get(ann['claim_id'], {})
        approved = claim.get('approved_copy', {}).get(market['locale'], [])
        if claim.get('status') != 'confirmed' or ann['text'] not in approved:
            errors.append(f'copy not approved for this claim/locale: {ident}')
        if not set(ann['evidence']).issubset(set(claim.get('evidence', []))):
            errors.append(f'evidence mismatch: {ident}')
        if ann.get('accent_text') and ann['accent_text'] not in ann['text']:
            errors.append(f'accent_text missing from text: {ident}')
        if any(ch in ann['text'] for ch in ('{', '}', '\\')) or any(
                ord(ch) < 32 and ch != '\n' for ch in ann['text']):
            errors.append(f'unsupported ASS control characters: {ident}')
        missing = [ch for ch in ann['text'] if not ch.isspace() and ord(ch) not in cmap]
        if missing:
            errors.append(f'font missing glyphs: {ident}: {"".join(sorted(set(missing)))}')
        lines = ann['text'].splitlines()
        if not ann['text'].strip():
            errors.append(f'blank annotation text: {ident}')
            continue
        # Conservative extra margin for libass/Pillow shaping differences and bold.
        tw = max(font.getlength(line) for line in lines) * 1.15
        th = sum(font.getmetrics()) * len(lines) * 1.1
        pad = card['padding_px'] + text['outline_px'] + text['shadow_px']
        bw, bh = tw + 2 * pad, th + 2 * pad
        motion_x = 24 if ann['animation']=='slide-left' else 0
        motion_y = 24 if ann['animation']=='slide-up' else 0
        if bw + motion_x > x1-x0 or bh + motion_y > y1-y0:
            errors.append(f'text/card/animation overflows safe zone; shorten or explicitly wrap: {ident}')
            continue
        ax, ay = anchors[ann['anchor']]
        x = max(x0+bw/2, min(x1-bw/2-motion_x, x0+(x1-x0)*ax))
        y = max(y0+bh/2, min(y1-bh/2-motion_y, y0+(y1-y0)*ay))
        if 'position' in ann:
            x,y=ann['position']['x']*width,ann['position']['y']*height
            if not (x0+bw/2<=x<=x1-bw/2-motion_x and y0+bh/2<=y<=y1-bh/2-motion_y):
                errors.append(f'explicit position/animation overflows safe zone: {ident}')
        if card['corner_radius_px'] > min(bw,bh)/2:
            errors.append(f'corner radius too large: {ident}')
        layouts.append({'id':ident,'x':x,'y':y,'width':bw,'height':bh})
    for omitted in data.get('omissions',[]):
        ident=omitted['id']
        if ident in seen:
            errors.append(f'duplicate annotation/omission ID: {ident}')
        seen.add(ident)
        if not 0<=omitted['start']<omitted['end']<=duration+.01:
            errors.append(f'invalid omission interval: {ident}')
        if claims.get(omitted['claim_id'],{}).get('status')!='confirmed':
            errors.append(f'omission claim not confirmed: {ident}')
        # Omission evidence describes observed obstruction/timecodes, not product claims.
        # Actual visual review is mandatory; geometry alone cannot authorize omission.
    return errors, layouts

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('--market-profile', required=True, type=Path)
    ap.add_argument('--claim-ledger', required=True, type=Path)
    ap.add_argument('--duration', required=True, type=float)
    ap.add_argument('--schema', type=Path, default=SCHEMA)
    args = ap.parse_args()
    try:
        errors, layouts = validate(json.loads(args.plan.read_text()), load_market(args.market_profile),
            digest(args.market_profile), json.loads(args.claim_ledger.read_text()), args.duration, args.schema)
        print(json.dumps({'status':'fail' if errors else 'pass','errors':errors,'layouts':layouts},ensure_ascii=False))
        return 1 if errors else 0
    except Exception as exc:
        print(json.dumps({'status':'blocked','error':str(exc)}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
