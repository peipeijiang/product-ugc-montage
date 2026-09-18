"""Demand-bound finite-domain assignment; existing jsonschema validation, no new solver.

FEASIBLE is a witness, INFEASIBLE requires exhausted search, UNKNOWN is a limit.
Neither a planned witness nor observed-shot assignment is release approval.
"""
import time
import json
from functools import lru_cache
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError
from contracts import number, overlap

ROLES = {'hook', 'proof', 'transition', 'ending'}


@lru_cache(maxsize=1)
def schema_validator():
    schema=json.loads((Path(__file__).resolve().parents[1]/'references/creative_demand.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_demand(data):
    try:
        schema_validator().validate(data)
    except ValidationError as exc:
        raise ValueError('invalid creative demand: '+exc.message) from exc
    if data.get('schema_version') != 1:
        raise ValueError('demand schema_version=1 required')
    n = data.get('target_videos', 20)
    if type(n) is not int or n < 1 or len(data.get('variants', [])) != n:
        raise ValueError('one creative brief per requested video required (default 20)')
    if not data.get('market_profile_id') or len(data.get('market_profile_sha256', '')) != 64:
        raise ValueError('frozen market ID/hash required')
    points = data.get('selling_points', [])
    claims = {p['id'] for p in points if p.get('status') == 'confirmed' and p.get('evidence')}
    if not claims or len(claims) != len(points):
        raise ValueError('unique confirmed evidence-backed selling points required')
    reuse = data.get('constraints', {}).get('max_shot_uses')
    limit = data.get('constraints', {}).get('max_pairwise_overlap')
    if type(reuse) is not int or reuse < 1 or not number(limit) or not 0 <= limit <= 1:
        raise ValueError('explicit max_shot_uses and max_pairwise_overlap required')
    ids, briefs, scripts, requirements = set(), set(), set(), []
    for variant in data['variants']:
        ident = variant.get('variant_id')
        if not ident or ident in ids:
            raise ValueError('unique variant_id required')
        ids.add(ident)
        for key in ('audience', 'scenario', 'creative_angle', 'script_draft'):
            if not isinstance(variant.get(key), str) or not variant[key].strip():
                raise ValueError('creative brief missing '+key)
        signature = tuple(variant[k].strip() for k in ('audience', 'scenario', 'creative_angle'))
        script = ''.join(variant['script_draft'].split())
        if signature in briefs or script in scripts:
            raise ValueError('duplicate creative brief/script; changed IDs are not new concepts')
        briefs.add(signature); scripts.add(script)
        if variant.get('runtime_basis') not in ('estimated', 'measured'):
            raise ValueError('runtime_basis must be estimated or measured')
        slots = variant.get('slots', [])
        if len(slots) < 2 or slots[0].get('role') != 'hook' or slots[-1].get('role') != 'ending':
            raise ValueError('each variant needs an opening hook and separate dynamic ending')
        local, used = set(), set()
        for i, slot in enumerate(slots):
            sid = slot.get('slot_id')
            seconds = slot.get('seconds')
            if (not sid or sid in local or slot.get('claim_id') not in claims
                    or slot.get('role') not in ROLES or not slot.get('proof_key')
                    or not slot.get('calibration_group') or not number(seconds) or not 0 < seconds <= 10):
                raise ValueError('invalid slot ID/claim/role/proof/duration/calibration group')
            if slot['role'] == 'hook' and (i != 0 or seconds < 3):
                raise ValueError('one opening hook per video, at least 3s')
            local.add(sid); used.add(slot['claim_id'])
            requirements.append({**slot, 'variant_id': ident})
        if variant.get('main_claim_id') not in used:
            raise ValueError('main_claim_id must have a proof in this variant')
        runtime = variant.get('runtime_seconds')
        if not number(runtime) or abs(runtime-sum(s['seconds'] for s in slots)) > .001:
            raise ValueError('slot durations must cover the narration-derived/estimated runtime including head/tail')
    return requirements


def matches(slot, shot):
    return (slot['claim_id'] in shot.get('claim_ids', [])
            and slot['proof_key'] in shot.get('proof_keys', [])
            and slot['role'] in shot.get('roles', [])
            and slot['calibration_group'] == shot.get('calibration_group')
            and shot['out']-shot['in']+.000001 >= slot['seconds']
            and (slot['role'] != 'hook' or shot.get('hook_eligible') is True)
            and (slot['role'] != 'ending' or shot.get('dynamic_ending') is True))


def conflicts(slot, shot, assignments, constraints, runtimes):
    same = [(s, p) for s,p in assignments if s['variant_id'] == slot['variant_id']]
    selected = {**shot, 'out': shot['in']+slot['seconds']}
    if any(p['visual_cluster_id'] == shot['visual_cluster_id'] or overlap(selected, p) for _,p in same):
        return True
    if sum(p['visual_cluster_id'] == shot['visual_cluster_id'] for _,p in assignments) >= constraints['max_shot_uses']:
        return True
    if slot['role'] == 'hook' and any(s['role'] == 'hook' and
            (p['visual_cluster_id'] == shot['visual_cluster_id'] or overlap(selected, p))
            for s,p in assignments):
        return True
    current = same + [(slot, selected)]
    for other in {s['variant_id'] for s,_ in assignments} - {slot['variant_id']}:
        prior = [(s,p) for s,p in assignments if s['variant_id'] == other]
        shared = sum(min(a['seconds'], b['seconds']) for a,x in current for b,y in prior
                     if x['visual_cluster_id'] == y['visual_cluster_id'] or overlap(x,y))
        if shared/min(runtimes[other], runtimes[slot['variant_id']]) > constraints['max_pairwise_overlap']+.000001:
            return True
    return False


def solve(demand, shots, max_nodes=20000, seconds=5):
    slots = validate_demand(demand)
    if type(max_nodes) is not int or max_nodes < 1 or not number(seconds) or seconds <= 0:
        raise ValueError('positive search limits required')
    identities = set()
    for shot in shots:
        if (not shot.get('shot_id') or shot['shot_id'] in identities or not shot.get('source_id')
                or not shot.get('source_sha256') or not shot.get('visual_cluster_id')
                or not number(shot.get('in')) or not number(shot.get('out')) or not 0<=shot['in']<shot['out']):
            raise ValueError('unique ranged source identities required')
        identities.add(shot['shot_id'])
    domains = [[s for s in shots if matches(slot, s)] for slot in slots]
    deficits = [{'variant_id':s['variant_id'], 'slot_id':s['slot_id'], 'claim_id':s['claim_id'],
                 'proof_key':s['proof_key'], 'role':s['role'], 'seconds':s['seconds'],
                 'calibration_group':s['calibration_group'], 'reason':'no matching usable range'}
                for s,candidates in zip(slots,domains) if not candidates]
    start = time.monotonic()
    nodes, interrupted, solution = 0, False, None
    runtimes = {v['variant_id']:v['runtime_seconds'] for v in demand['variants']}
    # Most-constrained first; source reuse is a cost heuristic, not an optimality proof.
    order = sorted(range(len(slots)), key=lambda i:(len(domains[i]), slots[i]['role']!='hook'))
    def visit(depth, assigned):
        nonlocal nodes, interrupted, solution
        if nodes >= max_nodes or time.monotonic()-start >= seconds:
            interrupted = True
            return False
        nodes += 1
        if depth == len(order):
            solution = list(assigned)
            return True
        i = order[depth]
        used = {p['source_id'] for _,p in assigned}
        for shot in sorted(domains[i], key=lambda p:(p['source_id'] not in used, p['shot_id'])):
            if conflicts(slots[i], shot, assigned, demand['constraints'], runtimes):
                continue
            chosen = {**shot, 'out':shot['in']+slots[i]['seconds']}
            if visit(depth+1, assigned+[(slots[i], chosen)]):
                return True
            if interrupted:
                return False
        return False
    if not deficits:
        visit(0, [])
    status = 'FEASIBLE' if solution is not None else 'UNKNOWN' if interrupted else 'INFEASIBLE'
    allocations = []
    for slot,shot in solution or []:
        allocations.append({'variant_id':slot['variant_id'], 'slot_id':slot['slot_id'],
                            'shot_id':shot['shot_id'], 'source_id':shot['source_id'],
                            'in':shot['in'], 'out':shot['out'], 'role':slot['role'],
                            'claim_id':slot['claim_id'], 'seconds':slot['seconds']})
    return {'solver_status':status, 'target_videos':demand.get('target_videos',20),
            'nodes_visited':nodes, 'search_exhausted':status=='INFEASIBLE',
            'optimality_proven':False, 'allocations':allocations,
            'selected_source_ids':sorted({a['source_id'] for a in allocations}),
            'deficits':deficits, 'conflict_diagnosis':None if solution is not None or deficits else
                'joint reuse/opening/overlap constraints; no minimal shortage proved',
            'guidance':('inspect search limits/model before buying more footage' if status=='UNKNOWN' else
                        'infeasible only for supplied shots and demand; revise exact gaps/constraints' if status=='INFEASIBLE' else
                        'assignment witness only; perceptual review and final audio/EDL QA remain required')}


def requirements_summary(demand):
    slots = validate_demand(demand)
    groups = {}
    for slot in slots:
        key = (slot['claim_id'], slot['proof_key'], slot['role'], slot['calibration_group'])
        entry = groups.setdefault(key, {'claim_id':key[0], 'proof_key':key[1], 'role':key[2],
                                       'calibration_group':key[3], 'occurrences':0, 'seconds':0,
                                       'longest_continuous_seconds':0})
        entry['occurrences'] += 1; entry['seconds'] += slot['seconds']
        entry['longest_continuous_seconds'] = max(entry['longest_continuous_seconds'],slot['seconds'])
    return list(groups.values())
