#!/usr/bin/env python3
"""Demand-led budget. No fixed source-per-ad ratio, flat reserve or provider calls."""
import argparse
import json
import math
from pathlib import Path
from collections import Counter
from contracts import accepted_shots, digest, number
from demand_planner import ROLES, validate_demand, requirements_summary, solve
from source_policy import model_id
from validate_generation_matrix import validate as validate_matrix


def planned_supply(matrix, demand):
    errors, _ = validate_matrix(matrix)
    if errors:
        raise ValueError('; '.join(errors))
    for key in ('market_profile_id', 'market_profile_sha256'):
        if matrix.get(key) != demand.get(key):
            raise ValueError('matrix/demand mismatch: '+key)
    if matrix.get('target_videos',20) != demand.get('target_videos',20):
        raise ValueError('matrix/demand target mismatch')
    shots, ids = [], set()
    allowed_claims={p['id'] for p in demand['selling_points']}
    for container in matrix['containers']:
        if not container.get('calibration_group'):
            raise ValueError('container calibration_group required')
        for beat in container['beats']:
            if beat['claim_id'] not in allowed_claims:
                raise ValueError('planned proof claim is outside the approved demand ledger')
            sid = beat.get('creative_slot_id')
            roles = beat.get('roles', [])
            if not sid or sid in ids or not beat.get('proof_key') or not roles or not set(roles)<=ROLES:
                raise ValueError('each planned beat needs unique creative_slot_id, proof_key and roles')
            ids.add(sid)
            if 'hook' in roles and (beat['end']-beat['start']<3 or not number(beat.get('payoff_after'))
                                   or not 0<beat['payoff_after']<=3):
                raise ValueError('interior/first hook needs >=3s and independent payoff within 3s')
            if 'ending' in roles and not beat.get('dynamic_action'):
                raise ValueError('ending beat needs a concrete dynamic_action')
            shots.append({'shot_id':sid, 'source_id':container['container_id'],
                'source_sha256':'planned:'+container['container_id'], 'in':beat['start'], 'out':beat['end'],
                'claim_ids':[beat['claim_id']], 'proof_keys':[beat['proof_key']], 'roles':roles,
                'calibration_group':container['calibration_group'], 'visual_cluster_id':'planned:'+sid,
                'hook_eligible':'hook' in roles, 'dynamic_ending':'ending' in roles})
    return shots


def wilson(success, n):
    if not n:
        return None
    z = 1.959963984540054
    p = success/n
    den = 1+z*z/n
    center = (p+z*z/(2*n))/den
    margin = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,center-margin), min(1,center+margin)]


def calibrate(history, root, context):
    """One terminal generation task = one trial; its beats are not IID trials."""
    groups, seen = {}, set()
    if not context or any(not context.get(k) for k in ('model','reference_mode','category','prompt_version','market_profile_sha256')):
        raise ValueError('exact model/route/category/prompt version/market hash calibration_context required')
    for row in history.get('trials', []):
        if row.get('context') != context:
            continue
        task = row.get('task_id')
        if not task or task in seen:
            raise ValueError('duplicate/missing calibration task_id')
        seen.add(task)
        path = Path(row['review_file'])
        path = path if path.is_absolute() else Path(root)/path
        if digest(path) != row.get('review_sha256'):
            raise ValueError('stale calibration review')
        review = json.loads(path.read_text())
        if (review.get('task_id') != task or not review.get('reviewer') or not review.get('evidence')
                or type(review.get('usable')) is not bool or not review.get('calibration_group')
                or not number(review.get('usable_seconds')) or not 0<=review['usable_seconds']<=10
                or type(review.get('independent_hooks')) is not int or not 0<=review['independent_hooks']<=3):
            raise ValueError('task review needs measured outcome/seconds/hooks and actual evidence')
        group = groups.setdefault(review['calibration_group'], {'trials':0,'successes':0,'usable_seconds':0,'hooks':0})
        group['trials']+=1; group['successes']+=int(review['usable'])
        group['usable_seconds']+=review['usable_seconds']; group['hooks']+=review['independent_hooks']
    for group in groups.values():
        n = group['trials']
        group.update(rate=group['successes']/n, wilson_95=wilson(group['successes'],n),
                     mean_usable_seconds=group['usable_seconds']/n, mean_hooks=group['hooks']/n)
    return groups


def plan(demand, matrix=None, library=None, library_root=Path('.'), history=None,
         history_root=Path('.'), max_nodes=20000, seconds=5):
    validate_demand(demand)
    result = {'schema_version':2,'target_videos':demand.get('target_videos',20),
              'requirements':requirements_summary(demand),'paid_authorization':False,
              'predicted_source_count':None,'release_ready':False,
              'status':'needs_source_design', 'assumptions':[
                  'planned creative slots are not observed visual diversity',
                  'solver feasibility does not imply global minimum or generation success',
                  'estimated runtime must be rebound to each complete TTS track before release']}
    observed = []
    if library is not None:
        for key in ('market_profile_id','market_profile_sha256'):
            if library.get(key)!=demand.get(key):
                raise ValueError('library/demand market mismatch')
        observed = accepted_shots(library, library_root, True)
        result['observed_capacity'] = solve(demand, observed, max_nodes, seconds)
        if result['observed_capacity']['solver_status']=='FEASIBLE':
            result.update(status='observed_feasible', predicted_source_count=0, selected_container_ids=[])
            return result
        result['targeted_gaps']=result['observed_capacity']['deficits']
        if result['observed_capacity']['solver_status']=='UNKNOWN':
            result['status']='search_unknown'
            return result  # Never buy new sources merely because existing footage search timed out.
        result['status']='observed_infeasible'
    if matrix is None:
        return result
    planned = planned_supply(matrix,demand)
    for s in planned:
        s['source_id']='new:'+s['source_id']; s['shot_id']='new:'+s['shot_id']
    combined = solve(demand, observed+planned, max_nodes, seconds)
    result['planned_capacity'] = combined
    if combined['solver_status']!='FEASIBLE':
        result['status']='search_unknown' if combined['solver_status']=='UNKNOWN' else 'revise_source_design'
        result['targeted_gaps']=combined['deficits']
        return result
    selected = [s.removeprefix('new:') for s in combined['selected_source_ids'] if s.startswith('new:')]
    result['selected_container_ids']=selected
    result['planned_feasible_source_count']=len(selected)
    result['status']='pilot_required'
    context = matrix.get('calibration_context')
    if context is not None and (model_id(context.get('model'))!=model_id(matrix['model'])
            or context.get('reference_mode')!=matrix['reference_mode']
            or context.get('market_profile_sha256')!=matrix['market_profile_sha256']):
        raise ValueError('calibration context differs from generation route/market')
    stats = calibrate(history,history_root,context) if history is not None else {}
    result['calibration']=stats
    by_id = {c['container_id']:c for c in matrix['containers']}
    needed = Counter(by_id[c]['calibration_group'] for c in selected)
    result['pilot_candidates']=[next(c for c in selected if by_id[c]['calibration_group']==g)
                                for g in needed if g not in stats or stats[g]['rate']==0]
    scenarios = []
    for group,count in needed.items():
        stat = stats.get(group)
        row={'calibration_group':group,'planned_required_containers':count,
             'point_scenario':None,'conservative_scenario':None}
        if stat and stat['rate']>0:
            row.update(point_scenario=math.ceil(count/stat['rate']),
                       conservative_scenario=math.ceil(count/stat['wilson_95'][0]),
                       sample_size=stat['trials'])
        scenarios.append(row)
    result['generation_scenarios']=scenarios
    result['scenario_warning']='Conditional on comparable independent task outcomes; not a batch success probability. Correlated failures, template drift and packing can invalidate extrapolation.'
    if scenarios and all(s['point_scenario'] is not None for s in scenarios):
        result.update(status='calibrated_scenarios', predicted_source_count={
            'point':sum(s['point_scenario'] for s in scenarios),
            'conservative':sum(s['conservative_scenario'] for s in scenarios)})
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('demand',type=Path)
    ap.add_argument('--matrix',type=Path)
    ap.add_argument('--library',type=Path)
    ap.add_argument('--history',type=Path)
    ap.add_argument('--max-nodes',type=int,default=20000)
    ap.add_argument('--search-seconds',type=float,default=5)
    ap.add_argument('-o','--output',type=Path,required=True)
    args=ap.parse_args()
    try:
        read=lambda p: json.loads(p.read_text()) if p else None
        report=plan(read(args.demand),read(args.matrix),read(args.library),args.library.parent if args.library else Path('.'),
                    read(args.history),args.history.parent if args.history else Path('.'),args.max_nodes,args.search_seconds)
        report['demand_sha256']=digest(args.demand)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 2 if report['status'] in ('search_unknown','revise_source_design','observed_infeasible') else 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'status':'blocked','error':str(exc)},ensure_ascii=False))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
