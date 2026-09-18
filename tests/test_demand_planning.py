"""Synthetic allocation/calibration fixtures; no paid requests or claimed visual QA."""
import copy
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contracts import digest
from demand_planner import solve,validate_demand
from plan_source_budget import plan,planned_supply,calibrate,wilson
from validate_generation_matrix import validate as matrix_check
from audit_budget_outcomes import audit


def fixture(n=20):
    points=[{'id':'a','status':'confirmed','evidence':['fixture-page']}]
    demand={'schema_version':1,'target_videos':n,'market_profile_id':'m','market_profile_sha256':'a'*64,
            'selling_points':points,'constraints':{'max_shot_uses':1,'max_pairwise_overlap':0},'variants':[]}
    for i in range(n):
        demand['variants'].append({'variant_id':f'v{i}','main_claim_id':'a','audience':'fixture',
            'scenario':f'scene{i}','creative_angle':f'angle{i}','script_draft':f'script{i}',
            'runtime_basis':'estimated','runtime_seconds':5,'slots':[
                {'slot_id':'h','role':'hook','claim_id':'a','proof_key':'demo','seconds':3,'calibration_group':'simple'},
                {'slot_id':'e','role':'ending','claim_id':'a','proof_key':'demo','seconds':2,'calibration_group':'simple'}]})
    context={'model':'omni-flash','reference_mode':'omni-reference','category':'fixture',
             'prompt_version':'v1','market_profile_sha256':'a'*64}
    matrix={'model':'omni-flash','reference_mode':'omni-reference','target_videos':n,
            'market_profile_id':'m','market_profile_sha256':'a'*64,'selling_points':points,
            'calibration_context':context,'containers':[]}
    for i in range((n+1)//2):
        c={'container_id':f'c{i}','variant_id':i+1,'duration':10,'claim_ids':['a'],
           'creative_slot_id':f'container{i}','calibration_group':'simple','beats':[]}
        for axis in ('scene_geometry','camera_distance','camera_motion','creator_staging','proof_composition'):
            c[axis]=f'{axis}{i}'
        for j,(a,b,role) in enumerate([(0,3,'hook'),(3,6,'hook'),(6,8,'ending'),(8,10,'ending')]):
            c['beats'].append({'start':a,'end':b,'claim_id':'a','proof_moment':'fixture motion',
                'creative_slot_id':f'c{i}s{j}','proof_key':'demo','roles':[role],
                'payoff_after':2,'dynamic_action':'fixture movement'})
        matrix['containers'].append(c)
    return demand,matrix


class DemandPlanningTests(unittest.TestCase):
    def test_twenty_ads_can_use_ten_sources_with_interior_hooks(self):
        d,m=fixture()
        self.assertEqual(matrix_check(m)[0],[])
        r=plan(d,m)
        self.assertEqual(r['planned_capacity']['solver_status'],'FEASIBLE')
        self.assertEqual(r['planned_feasible_source_count'],10)
        self.assertIsNone(r['predicted_source_count'])
        self.assertFalse(r['release_ready'])

    def test_duration_changes_supply_need_and_explicit_gap(self):
        d,m=fixture(2)
        d['variants'][0]['slots'][1]['seconds']=4
        d['variants'][0]['runtime_seconds']=7
        r=plan(d,m)
        self.assertEqual(r['planned_capacity']['solver_status'],'INFEASIBLE')
        self.assertEqual(r['targeted_gaps'][0]['role'],'ending')
        self.assertEqual(r['targeted_gaps'][0]['seconds'],4)

    def test_timeout_is_unknown_not_shortage(self):
        d,m=fixture(2)
        r=plan(d,m,max_nodes=1)
        self.assertEqual(r['planned_capacity']['solver_status'],'UNKNOWN')
        self.assertFalse(r['planned_capacity']['search_exhausted'])
        self.assertEqual(r['status'],'search_unknown')

    def test_existing_footage_first_and_timeout_does_not_trigger_paid_candidates(self):
        d,m=fixture(2)
        lib={'market_profile_id':'m','market_profile_sha256':'a'*64}
        with patch('plan_source_budget.accepted_shots',return_value=planned_supply(m,d)):
            ready=plan(d,m,library=lib)
            self.assertEqual(ready['predicted_source_count'],0)
            self.assertEqual(ready['selected_container_ids'],[])
            unknown=plan(d,m,library=lib,max_nodes=1)
            self.assertEqual(unknown['status'],'search_unknown')
            self.assertNotIn('selected_container_ids',unknown)
            self.assertNotIn('planned_capacity',unknown)

    def test_joint_infeasibility_not_invented_missing_claim(self):
        d,m=fixture(2)
        shots=planned_supply(m,d)
        shots=[s for s in shots if s['shot_id']!='c0s1']
        r=solve(d,shots)
        self.assertEqual(r['solver_status'],'INFEASIBLE')
        self.assertEqual(r['deficits'],[])
        self.assertIsNotNone(r['conflict_diagnosis'])

    def test_subset_claims_per_ad_and_complex_single_claim_allowed(self):
        d,m=fixture(2)
        d['selling_points'].append({'id':'b','status':'confirmed','evidence':['fixture']})
        d['variants'][1]['main_claim_id']='b'
        for s in d['variants'][1]['slots']: s['claim_id']='b'
        self.assertEqual(len(validate_demand(d)),4)
        c=m['containers'][0]
        c['beats']=[{**c['beats'][0],'start':0,'end':10,'roles':['proof']}]
        self.assertEqual(matrix_check(m)[0],[])

    def test_invalid_runtime_and_duplicate_creative_brief(self):
        d,m=fixture(2)
        d['variants'][0]['runtime_seconds']=99
        with self.assertRaises(ValueError): plan(d,m)
        d,m=fixture(2)
        d['variants'][1]=copy.deepcopy(d['variants'][0])
        d['variants'][1]['variant_id']='different-id'
        with self.assertRaises(ValueError): validate_demand(d)

    def test_calibration_binds_evidence_and_excludes_different_context(self):
        d,m=fixture(2)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); rows=[]
            for i,success in enumerate((True,True,False)):
                p=root/f'review{i}.json'
                p.write_text(json.dumps({'task_id':str(i),'reviewer':'synthetic fixture','evidence':['test only'],
                    'calibration_group':'simple','usable':success,'usable_seconds':10 if success else 0,
                    'independent_hooks':2 if success else 0}))
                rows.append({'context':m['calibration_context'],'task_id':str(i),
                             'review_file':p.name,'review_sha256':digest(p)})
            rows.append({'context':{'model':'different'},'task_id':'ignored'})
            history={'trials':rows}
            r=plan(d,m,history=history,history_root=root)
            self.assertEqual(r['calibration']['simple']['trials'],3)
            self.assertEqual(r['predicted_source_count']['point'],2)
            self.assertGreater(r['predicted_source_count']['conservative'],2)
            self.assertEqual(r['calibration']['simple']['successes'],2)
            history['trials'].append(rows[0])
            with self.assertRaises(ValueError): calibrate(history,root,m['calibration_context'])
            history['trials'].pop()
            (root/'review0.json').write_text('{}')
            with self.assertRaises(ValueError): calibrate(history,root,m['calibration_context'])

    def test_small_sample_interval_not_certainty(self):
        self.assertIsNone(wilson(0,0))
        self.assertLess(wilson(1,1)[0],.3)
        self.assertGreater(wilson(0,1)[1],.7)

    def test_forecast_audit_excludes_unknown_and_rejects_rewritten_prediction(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rows=[]
            for i,prediction in enumerate((None,{'point':10,'conservative':15})):
                path=root/f'budget{i}.json'
                path.write_text(json.dumps({'target_videos':20,'predicted_source_count':prediction}))
                rows.append({'run_id':str(i),'complete':True,'budget_file':path.name,
                             'budget_sha256':digest(path),'actual_generated_sources':12,
                             'actual_delivered_videos':19,'evidence':['fixture outcome']})
            result=audit({'runs':rows},root)
            self.assertEqual(result['evaluated_predictions'],1)
            self.assertEqual(result['mean_absolute_source_count_error'],2)
            self.assertEqual(result['runs'][0]['delivery_shortfall'],1)
            path.write_text('{}')
            with self.assertRaises(ValueError): audit({'runs':rows},root)


if __name__=='__main__':
    unittest.main()
