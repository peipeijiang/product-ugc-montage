#!/usr/bin/env python3
"""Offline demand plan BEFORE generation; estimates are not paid-job authorization."""
import argparse
import json
import math
from pathlib import Path


def plan(ledger, target=20, reserve_ratio=.25):
    if type(target) is not int or target < 1:
        raise ValueError('target must be a positive integer')
    if not 0 <= reserve_ratio <= 1:
        raise ValueError('reserve_ratio must be within 0..1')
    claims = ledger.get('claims', [])
    points = [c['id'] for c in claims if c.get('status') == 'confirmed' and c.get('evidence')]
    if not points or len(points) != len(set(points)):
        raise ValueError('unique evidence-backed confirmed claims required; never invent claims for volume')
    # Conservative: only one independent opener is budgeted per generated container.
    # Interior proof ranges may become additional hooks AFTER observed visual QC.
    k = min(3, len(points))
    # This planner's downstream EDL candidate covers the selected batch claims.
    # Plan enough proofs for <=3 uses per proof as a budget assumption, not QA.
    per_claim = math.ceil(target / 3)
    base = max(target, len(points), math.ceil(len(points) * per_claim / k))
    total = math.ceil(base * (1 + reserve_ratio))
    slots = []
    counts = dict.fromkeys(points, 0)
    for i in range(total):
        selected = [points[i % len(points)]]
        for _ in range(k-1):
            selected.append(min((p for p in points if p not in selected), key=lambda p: counts[p]))
        for p in selected:
            counts[p] += 1
        slots.append({'container_id': f'c{i+1:03d}', 'variant_id': i+1,
                      'claim_ids': selected, 'hook_claim_id': selected[0],
                      'duration': 10, 'reserve_budget': i >= base,
                      'creative_treatment_required': True})
    return {'schema_version': 1, 'target_videos': target,
            'confirmed_claim_ids': points, 'claims_per_video': len(points),
            'planned_proof_count_by_claim': counts,
            'budget_proof_reuse_assumption': 3,
            'claims_per_container': k, 'required_distinct_openings': target,
            'base_container_count': base, 'reserve_ratio': reserve_ratio,
            'planned_container_count': total, 'planned_source_seconds': total * 10,
            'planned_proof_ranges': total * k, 'slots': slots,
            'capacity_is_estimate': True, 'paid_authorization': False,
            'assumptions': ['one independent opening per 10s container before QC',
                            'two or three compatible proof beats; one if only one claim is confirmed',
                            'final runtime is measured from each narration, not fixed at 10 seconds',
                            'actual QA, duration and overlap may require extra sources; no padded outputs']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('ledger', type=Path)
    ap.add_argument('--target', type=int, default=20)
    ap.add_argument('--reserve-ratio', type=float, default=.25)
    ap.add_argument('-o', '--output', type=Path, required=True)
    args = ap.parse_args()
    result = plan(json.loads(args.ledger.read_text()), args.target, args.reserve_ratio)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'slots'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
