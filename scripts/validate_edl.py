#!/usr/bin/env python3
"""Bind every narration cue to proof ranges; reject speed changes and stale scripts."""
import argparse
import itertools
import json
from pathlib import Path
from contracts import accepted_shots, digest, number, overlap

def validate(edl, narration, shots, market):
    errors = []
    if edl.get('market_profile_id') != market or narration.get('market_profile_id') != market:
        errors.append('EDL/narration/library market mismatch')
    for key in ('narration_id', 'script_sha256', 'audio_sha256', 'market_profile_sha256'):
        if not narration.get(key) or edl.get(key) != narration[key]:
            errors.append(f'stale or different narration: {key}')
    lookup = {s['shot_id']: s for s in shots}
    segments = edl.get('segments', [])
    cues = narration.get('cues', [])
    if not segments or not cues:
        return errors + ['segments and timed narration cues are required']
    cursor, selected = 0.0, []
    for seg in segments:
        shot = lookup.get(seg.get('shot_id'))
        values = [seg.get(k) for k in ('in','out','timeline_start','timeline_end')]
        if not shot or not all(number(x) for x in values):
            errors.append('unknown shot or missing numeric source/output range')
            continue
        a,b,c,d = values
        if not shot['in'] <= a < b <= shot['out'] or c < 0 or d <= c:
            errors.append('segment exceeds accepted source range')
        if abs((b-a)-(d-c)) > .04 or seg.get('speed',1) != 1:
            errors.append('speed changes/freeze padding are not allowed')
        if abs(c-cursor) > .04:
            errors.append('timeline gap/overlap/order error')
        cursor = d
        selected.append({**shot,'in':a,'out':b})
    if any(overlap(a,b) for a,b in itertools.combinations(selected,2)):
        errors.append('repeated/overlapping source footage')
    if len({s['visual_cluster_id'] for s in selected}) != len(selected):
        errors.append('repeated visual cluster inside the edit')
    if not number(edl.get('runtime')) or abs(cursor-edl['runtime']) > .04:
        errors.append('runtime differs from EDL')
    previous = -1
    for cue in cues:
        a,b = cue.get('start'),cue.get('end')
        claims = set(cue.get('claim_ids', []))
        if not number(a) or not number(b) or not 0 <= a < b or a < previous or not claims:
            errors.append('invalid/overlapping narration cue or missing claims')
            continue
        previous = b
        covered = 0
        for seg in segments:
            if not all(number(seg.get(k)) for k in ('timeline_start','timeline_end')):
                continue
            amount = max(0,min(b,seg['timeline_end'])-max(a,seg['timeline_start']))
            shot = lookup.get(seg.get('shot_id'),{})
            if amount and not claims.issubset(set(shot.get('claim_ids',[]))):
                errors.append(f'picture does not prove narration cue: {cue.get("id")}')
            else:
                covered += amount
        if covered < b-a-.04:
            errors.append(f'cue not fully covered by matching proof: {cue.get("id")}')
    return errors

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ('edl','library','narration'):
        ap.add_argument('--'+arg,type=Path,required=True)
    ap.add_argument('--script',type=Path,required=True)
    ap.add_argument('--audio',type=Path,required=True)
    args=ap.parse_args()
    try:
        library=json.loads(args.library.read_text())
        narration=json.loads(args.narration.read_text())
        errors=validate(json.loads(args.edl.read_text()),narration,
            accepted_shots(library,args.library.parent,True),library['market_profile_id'])
        if narration.get('market_profile_sha256') != library['market_profile_sha256']:
            errors.append('narration/library market profile hash mismatch')
        if narration.get('script_sha256')!=digest(args.script) or narration.get('audio_sha256')!=digest(args.audio):
            errors.append('narration manifest hash mismatch')
        print(json.dumps({'status':'fail' if errors else 'pass','errors':errors},ensure_ascii=False))
        return 1 if errors else 0
    except Exception as exc:
        print(json.dumps({'status':'blocked','error':str(exc)}))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
