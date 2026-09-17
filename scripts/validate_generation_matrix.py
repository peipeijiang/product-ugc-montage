#!/usr/bin/env python3
"""Validate cost-efficient 10s multi-claim source-container plans."""
import argparse
import json
from collections import Counter
from pathlib import Path
from contracts import number
from source_policy import model_id

AXES=('scene_geometry','camera_distance','camera_motion','creator_staging','proof_composition')

def validate(data):
    errors=[]
    points=[p.get('id') for p in data.get('selling_points',[])]
    try:
        model_id(data.get('model'))
    except ValueError as exc:
        errors.append(str(exc))
    if data.get('reference_mode') != 'omni-reference':
        errors.append('reference_mode must be omni-reference; first/last frames are forbidden')
    if any(p.get('status')!='confirmed' or not p.get('evidence') for p in data.get('selling_points',[])):
        errors.append('only confirmed evidence-backed selling points are permitted')
    target=data.get('target_videos',20)
    if type(target) is not int or target<1:
        errors.append('target_videos must be a positive integer')
        target=20
    if not data.get('market_profile_id') or len(str(data.get('market_profile_sha256','')))!=64:
        errors.append('market profile ID/hash required')
    if not points or None in points or len(points)!=len(set(points)):
        errors.append('unique selling-point IDs required')
    containers=data.get('containers',[])
    if not containers:
        return errors+['containers required'],{}
    if len(containers)<target:
        errors.append('budget at least one distinct opening container per target video before generation')
    ids,slots,signatures=set(),set(),set()
    hook_counts=Counter()
    proof_counts=Counter()
    for i,item in enumerate(containers):
        prefix=f'containers[{i}]'
        ident=item.get('container_id')
        if not ident or ident in ids: errors.append(prefix+' duplicate/missing container_id')
        ids.add(ident)
        if item.get('duration')!=10: errors.append(prefix+' duration must be 10')
        if item.get('model',data.get('model'))!=data.get('model') or item.get('reference_mode','omni-reference')!='omni-reference':
            errors.append(prefix+' cannot override the approved model/reference route')
        claims=item.get('claim_ids',[])
        if not min(2,len(points))<=len(claims)<=3 or len(claims)!=len(set(claims)) or not set(claims)<=set(points):
            errors.append(prefix+' needs 2-3 unique known claim_ids (one if only one confirmed claim exists)')
        hook=item.get('hook_claim_id')
        if hook not in claims: errors.append(prefix+' hook_claim_id must be in claim_ids')
        else: hook_counts[hook]+=1
        slot=item.get('creative_slot_id')
        if not slot or slot in slots: errors.append(prefix+' duplicate/missing creative_slot_id')
        slots.add(slot)
        if any(not item.get(axis) for axis in AXES): errors.append(prefix+' missing creative diversity axis')
        signature=tuple(str(item.get(axis)) for axis in AXES)
        if signature in signatures: errors.append(prefix+' repeats an existing visual treatment exactly')
        signatures.add(signature)
        beats=item.get('beats',[])
        cursor=0
        seen_claims=set()
        for j,beat in enumerate(beats):
            a,b=beat.get('start'),beat.get('end')
            claim=beat.get('claim_id')
            if not number(a) or not number(b) or abs(a-cursor)>.001 or not a<b<=10:
                errors.append(f'{prefix}.beats[{j}] invalid/non-contiguous timing')
                continue
            cursor=b
            if claim not in claims or not beat.get('proof_moment'):
                errors.append(f'{prefix}.beats[{j}] missing claim/proof')
            else:
                seen_claims.add(claim); proof_counts[claim]+=1
        if abs(cursor-10)>.001: errors.append(prefix+' beats must cover all 10 seconds')
        if seen_claims!=set(claims): errors.append(prefix+' every container claim needs a proof beat')
        if not beats or beats[0].get('claim_id')!=hook or beats[0].get('start')!=0:
            errors.append(prefix+' first beat must start with the hook claim')
        if not beats or not number(beats[0].get('end')) or beats[0]['end']<3:
            errors.append(prefix+' reserve at least 3 continuous seconds for the opening proof')
        payoff=item.get('hook_payoff_by')
        if not number(payoff) or payoff>3 or payoff<=0:
            errors.append(prefix+' hook_payoff_by must be within the first 3 seconds')
        elif not beats or not number(beats[0].get('end')) or payoff>beats[0]['end']:
            errors.append(prefix+' hook payoff must occur inside the hook proof beat')
    if points and (set(proof_counts)!=set(points) or min(proof_counts.values(),default=0)<1):
        errors.append('every selling point needs at least one planned proof')
    if hook_counts and max(hook_counts.values())-min(hook_counts.get(p,0) for p in points)>1:
        errors.append('hook selling points are not balanced across the batch')
    return errors,{'container_count':len(containers),'hook_counts':dict(hook_counts),
                   'proof_counts':dict(proof_counts),'unique_visual_treatments':len(signatures)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path)
    ap.add_argument('-o','--output',type=Path)
    args=ap.parse_args()
    try:
        errors,summary=validate(json.loads(args.plan.read_text()))
        result={'status':'fail' if errors else 'pass','errors':errors,'summary':summary}
        payload=json.dumps(result,ensure_ascii=False,indent=2)
        print(payload)
        if args.output: args.output.write_text(payload+'\n')
        return 1 if errors else 0
    except Exception as exc:
        print(json.dumps({'status':'blocked','error':str(exc)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
