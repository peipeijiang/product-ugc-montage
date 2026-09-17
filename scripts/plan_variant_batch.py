#!/usr/bin/env python3
"""Plan low-repeat TikTok variants from claim-bound shot ranges.

A 10-second source may cover several claims, but each accepted proof must have
its own range. This planner varies selling-point order and shot choice while
keeping every candidate free of repeated/near-duplicate visual clusters.
"""
import argparse
import itertools
import json
import math
import random
from pathlib import Path
from contracts import accepted_shots, overlap

def claim_orders(points, limit=720):
    count=math.factorial(len(points))
    if count<=limit:
        return list(itertools.permutations(points))
    # Deterministic spread: rotations, reverse rotations, then seeded sampling.
    orders=[]
    for base in (points,list(reversed(points))):
        for shift in range(len(points)):
            order=tuple(base[shift:]+base[:shift])
            if order not in orders:
                orders.append(order)
    rng=random.Random(1701)
    seen=set(orders)
    while len(orders)<limit:
        order=tuple(rng.sample(points,len(points)))
        if order not in seen:
            seen.add(order)
            orders.append(order)
    return orders

def candidate_pool(points, choices, max_candidates=50000):
    combination_count=math.prod(len(c) for c in choices)
    orders=claim_orders(points)
    rng=random.Random(17)
    if combination_count*len(orders)<=max_candidates:
        raw=((order,combo) for combo in itertools.product(*choices) for order in orders)
    else:
        raw=((rng.choice(orders),tuple(rng.choice(c) for c in choices))
             for _ in range(max_candidates))
    seen=set()
    for order,combo in raw:
        by_claim=dict(zip(points,combo))
        ordered=tuple(by_claim[p] for p in order)
        signature=(order,tuple(s['shot_id'] for s in ordered))
        if signature in seen:
            continue
        seen.add(signature)
        if len({s['visual_cluster_id'] for s in ordered})!=len(ordered):
            continue
        if any(overlap(a,b) for a,b in itertools.combinations(ordered,2)):
            continue
        yield order,ordered

def overlap_ratio(a,b):
    left={s['visual_cluster_id'] for s in a}
    right={s['visual_cluster_id'] for s in b}
    return len(left & right)/max(1,len(left))

def plan(data,root,include_reserve=False,cap=20,recommended=20,selected=None,
         max_pairwise_overlap=.34):
    if any(not isinstance(v,int) or isinstance(v,bool) or v<1 for v in (cap,recommended)):
        raise ValueError('caps must be positive integers')
    if selected is not None and (type(selected) is not int or selected < 1):
        raise ValueError('selected N must be a positive integer')
    target = selected if selected is not None else recommended
    if not 0<=max_pairwise_overlap<=1:
        raise ValueError('max_pairwise_overlap must be within 0..1')
    shots=accepted_shots(data,root,include_reserve)
    points=[p['id'] for p in data.get('selling_points',[])]
    if not points or len(set(points))!=len(points):
        raise ValueError('unique selling point IDs required')
    choices=[[s for s in shots if p in s['claim_ids']] for p in points]
    order_ceiling=math.factorial(len(points))
    shot_ceiling=math.prod(len(c) for c in choices)
    theoretical=order_ceiling*shot_ceiling
    all_candidates=list(candidate_pool(points,choices))
    pool=list(all_candidates)
    zero_reuse=[]
    zero_clusters=set()
    for candidate in all_candidates:
        clusters={s['visual_cluster_id'] for s in candidate[1]}
        if (clusters.isdisjoint(zero_clusters) and not any(
                overlap(a,b) for a in candidate[1] for old in zero_reuse for b in old[1])):
            zero_reuse.append(candidate)
            zero_clusters.update(clusters)
            if len(zero_reuse)>=cap:
                break
    selected_candidates=[]
    hook_counts={p:0 for p in points}
    while pool and len(selected_candidates)<cap:
        valid=[candidate for candidate in pool
               if candidate[1][0].get('hook_eligible') is True
               and candidate[1][0]['out']-candidate[1][0]['in'] >= 3
               and all(candidate[1][0]['visual_cluster_id'] != old[1][0]['visual_cluster_id']
                       and not overlap(candidate[1][0], old[1][0]) for old in selected_candidates)
               and all(
            overlap_ratio(candidate[1],old[1])<=max_pairwise_overlap
            for old in selected_candidates)]
        if not valid:
            break
        def score(candidate):
            order,ordered=candidate
            max_overlap=max((overlap_ratio(ordered,old[1])
                             for old in selected_candidates),default=0)
            position_novelty=sum(sum(p!=old[0][i] for i,p in enumerate(order))
                                 for old in selected_candidates)
            new_clusters=sum(s['visual_cluster_id'] not in {
                old_shot['visual_cluster_id']
                for old in selected_candidates for old_shot in old[1]}
                for s in ordered)
            # Rotate first-3-second hooks before repeating one.
            return (-hook_counts[order[0]],-max_overlap,new_clusters,position_novelty)
        chosen=max(valid,key=score)
        pool.remove(chosen)
        selected_candidates.append(chosen)
        hook_counts[chosen[0][0]]+=1
    previews=[]
    for index,(order,ordered) in enumerate(selected_candidates,1):
        previews.append({
            'variant_id':f'v{index:02d}',
            'selling_point_order':list(order),
            'hook_claim_id':order[0],
            'hook_window_seconds':[0,3],
            'ordered_shots':[{'claim_id':claim,'shot':shot}
                             for claim,shot in zip(order,ordered)],
            'visual_cluster_ids':[s['visual_cluster_id'] for s in ordered],
            'requires_new_full_narration':True,
            'alignment_contract':'narration cue, picture shot and annotation must use the same claim_id'
        })
    hard_cap=len(previews)
    zero_reuse_upper_bound=min(len({s['visual_cluster_id'] for s in c}) for c in choices)
    initial=min(target,hard_cap)
    readiness='ready' if hard_cap>=target else 'expand_library'
    return {
        'schema_version':4,
        'target_videos':target,
        'status':readiness,
        'candidate_shortfall':max(0,target-hard_cap),
        'distinct_hook_count':len({s['visual_cluster_id'] for s in shots
                                   if s.get('hook_eligible') is True and s['out']-s['in']>=3}),
        'market_profile_id':data['market_profile_id'],
        'market_profile_sha256':data['market_profile_sha256'],
        'selling_point_count':len(points),
        'accepted_shot_count':len(shots),
        'accepted_proofs_by_claim':{p:len(c) for p,c in zip(points,choices)},
        'missing_claim_ids':[p for p,c in zip(points,choices) if not c],
        'theoretical_ceiling':theoretical,
        'theoretical_order_permutations':order_ceiling,
        'theoretical_shot_combinations':shot_ceiling,
        'ceiling_is_not_valid_combination_count':True,
        'candidate_search_count':len(all_candidates),
        'max_pairwise_visual_overlap':max_pairwise_overlap,
        'zero_reuse_batch_found':len(zero_reuse),
        'zero_reuse_batch_upper_bound':zero_reuse_upper_bound,
        'reviewable_hard_cap':hard_cap,
        'tiktok_release_recommendation':{
            'recommended_initial_batch':initial,
            'requested_batch':target,
            'review_ceiling_per_round':hard_cap,
            'status':readiness,
            'guidance':(
                f'{target} picture candidates found; per-video narration/runtime and release QA still required.'
                if readiness=='ready' else
                f'Only {hard_cap} distinct-opening candidates found for target {target}; '
                'expand/review hooks and proof coverage, or ask user to reduce the target. Never pad.'
            )
        },
        'recommended_batch':initial,
        'selected_n':target,
        'user_choice_required':False,
        'candidate_preview':previews,
        'policy':{
            'multi_claim_source':'A 10-second source may prove multiple claims only as separate QC-passed shot ranges.',
            'alignment':'Narration cues, picture ranges and annotations share claim_id and output timing.',
            'order':'Each changed selling-point order requires a new complete narration and QA.',
            'per_video_narration':'Each selected video needs its own complete script and independent TTS job; unchanged successful jobs resume without resubmission.',
            'duplication':'No repeated opening range/cluster across variants; body pairwise overlap is bounded.'
        }
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest',type=Path)
    ap.add_argument('--include-reserve',action='store_true')
    ap.add_argument('--review-cap',type=int,default=20)
    ap.add_argument('--recommended',type=int,default=20,help='target when --selected-n is omitted')
    ap.add_argument('--selected-n',type=int)
    ap.add_argument('--max-pairwise-overlap',type=float,default=.34)
    ap.add_argument('-o','--output',type=Path)
    args=ap.parse_args()
    try:
        if args.review_cap<1 or args.recommended<1:
            raise ValueError('caps must be positive')
        result=plan(json.loads(args.manifest.read_text()),args.manifest.parent,
                    args.include_reserve,args.review_cap,args.recommended,args.selected_n,
                    args.max_pairwise_overlap)
        payload=json.dumps(result,ensure_ascii=False,indent=2)
        if args.output:
            args.output.write_text(payload+'\n')
        print(payload)
        return 0 if result['status']=='ready' else 2
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'status':'blocked','error':str(exc)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
