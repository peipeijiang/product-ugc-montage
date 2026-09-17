"""Offline regression coverage for the seven source/batch requirements."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from contracts import digest, accepted_shots
from source_policy import model_id, validate_source
from plan_source_budget import plan as budget
from plan_variant_batch import plan
from validate_generation_matrix import validate as matrix_check
from generate_montage_sources import command
from validate_batch import validate as batch_check


class BatchContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='montage-batch-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def save(self, name, obj):
        p = self.root/name
        p.write_text(json.dumps(obj, ensure_ascii=False))
        return p

    def claims(self, count=3):
        return [{'id': f'p{i}', 'status': 'confirmed', 'evidence': [f'page#{i}']} for i in range(count)]

    def matrix(self, count=3):
        data = {'model': 'omni-flash-10s', 'reference_mode': 'omni-reference',
                'target_videos': count, 'market_profile_id': 'm', 'market_profile_sha256': 'a'*64,
                'selling_points': self.claims(), 'containers': []}
        for i in range(count):
            claims = [f'p{(i+j)%3}' for j in range(3)]
            row = {'container_id': f'c{i}', 'variant_id': i+1, 'duration': 10,
                   'claim_ids': claims, 'hook_claim_id': claims[0], 'hook_payoff_by': 2.5,
                   'creative_slot_id': f'slot{i}', 'beats': [
                       {'start': a, 'end': b, 'claim_id': p, 'proof_moment': f'Observed proof plan {p}'}
                       for a,b,p in zip((0,3,6), (3,6,10), claims)]}
            for axis in ('scene_geometry','camera_distance','camera_motion','creator_staging','proof_composition'):
                row[axis] = f'{axis}-{i}'
            data['containers'].append(row)
        return data

    def library(self, count=24, points=3):
        data = {'schema_version': 2, 'market_profile_id': 'm', 'market_profile_sha256': 'a'*64,
                'selling_points': self.claims(points), 'shots': []}
        for i in range(count):
            src = self.root/f'source{i}.mp4'
            src.write_bytes(f'identity-only fixture {i}'.encode())
            h = digest(src)
            shot = {'shot_id': f's{i}', 'source_id': f'c{i}', 'file': str(src), 'source_sha256': h,
                    'source_duration': 10, 'in': 0, 'out': 3, 'claim_ids': [f'p{i%points}'],
                    'evidence': ['page#proof'], 'angle': f'angle{i}', 'market_profile_id': 'm',
                    'proof_moment': f'proof fixture {i}',
                    'market_profile_sha256': 'a'*64, 'creative_slot_id': f'slot{i}',
                    'visual_fingerprint': f'{i:048x}', 'visual_cluster_id': f'vc{i}',
                    'hook_eligible': True, 'status': 'accepted', 'generation_root': str(self.root),
                    'qc': {'status': 'pass', 'source_sha256': h, 'in': 0, 'out': 3,
                           'generated_motion': True, 'reviewer': 'test', 'evidence': ['fixture']}}
            shot['dedup'] = {'status': 'pass', 'source_sha256': h, 'in': 0, 'out': 3,
                             'visual_fingerprint': shot['visual_fingerprint'], 'visual_cluster_id': shot['visual_cluster_id']}
            data['shots'].append(shot)
        return data

    def test_budget_20_and_no_invented_claims(self):
        ledger = {'claims': self.claims()+[{'id':'fake','status':'inferred','evidence':['guess']}]}
        result = budget(ledger)
        self.assertEqual((result['target_videos'], result['planned_container_count']), (20,25))
        self.assertNotIn('fake', result['confirmed_claim_ids'])
        self.assertTrue(all(row['duration']==10 for row in result['slots']))
        self.assertEqual(budget({'claims':self.claims(1)}, target=2)['claims_per_container'], 1)
        with self.assertRaises(ValueError): budget({'claims':[]})
        broad = budget({'claims':self.claims(10)})
        self.assertGreater(broad['planned_container_count'], result['planned_container_count'])
        self.assertGreaterEqual(min(broad['planned_proof_count_by_claim'].values()), 7)

    def test_matrix_rejects_route_duration_and_shortfall(self):
        matrix = self.matrix()
        self.assertEqual(matrix_check(matrix)[0], [])
        for field, value in [('model','veo3.1'), ('model','omni_flash-10s-fl'),
                             ('reference_mode','first-last'), ('target_videos',20)]:
            bad = {**matrix, field:value}
            self.assertTrue(matrix_check(bad)[0])
        matrix['containers'][0]['duration'] = 8
        self.assertTrue(matrix_check(matrix)[0])

    def test_wrapper_forces_route_and_binds_plan(self):
        matrix = self.matrix()
        matrix_path = self.save('matrix.json', matrix)
        prompts = {'montage_matrix_sha256': digest(matrix_path), 'variants': [
            {'variant_id': c['variant_id'], 'montage_plan': c, 'storyboard_10s': c['beats']}
            for c in matrix['containers']]}
        prompts_path = self.save('prompts.json', prompts)
        pipeline = self.root/'pipeline'
        (pipeline/'scripts').mkdir(parents=True)
        (pipeline/'scripts/generate_videos_lk888.py').write_text('# test stub; not executed')
        self.save('product_manifest.json', {})
        args = argparse.Namespace(matrix=matrix_path, prompts=prompts_path, pipeline=pipeline,
                                  product=self.root, model='omni-flash-10s', workers=2)
        cmd = command(args)
        for flag, expected in [('--model','omni_flash-10s'), ('--duration','10'),
                               ('--reference-mode','omni-reference'), ('--audio-style','none')]:
            self.assertEqual(cmd[cmd.index(flag)+1], expected)
        args.model = 'veo3.1'
        with self.assertRaises(ValueError): command(args)
        args.model = 'omni-flash-10s'
        prompts['variants'][0]['montage_plan'] = {}
        self.save('prompts.json', prompts)
        with self.assertRaises(ValueError): command(args)

    def test_twenty_distinct_openings_and_claim_orders(self):
        with patch('contracts.validate_source'):
            result = plan(self.library(), self.root)
        candidates = result['candidate_preview']
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(len(candidates), 20)
        self.assertEqual(len({c['visual_cluster_ids'][0] for c in candidates}), 20)
        self.assertGreater(len({tuple(c['selling_point_order']) for c in candidates}), 1)

    def test_duplicate_openings_cannot_fill_target_even_if_body_overlap_allowed(self):
        with patch('contracts.validate_source'):
            result = plan(self.library(6), self.root, max_pairwise_overlap=1)
        self.assertEqual(result['status'], 'expand_library')
        self.assertEqual(result['target_videos'], 20)
        self.assertEqual(result['reviewable_hard_cap'], 6)
        self.assertEqual(result['candidate_shortfall'], 14)
        lib = self.library(1,3)
        with patch('contracts.validate_source'):
            missing = plan(lib,self.root)
        self.assertEqual(missing['missing_claim_ids'], ['p1','p2'])
        self.assertEqual(missing['candidate_shortfall'],20)

    def test_source_receipt_and_actual_media_gate(self):
        src = self.root/'motion.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=64x96:rate=10',
                        '-t','10','-pix_fmt','yuv420p',str(src)], check=True, capture_output=True)
        for name in ('storyboard.png','identity.png'):
            (self.root/name).write_bytes(name.encode())  # reference hash fixtures only
        provenance = {'model':'omni_flash-10s', 'sha256':digest(src), 'actual_prompt':'test',
                      'config':{'reference_mode':'omni-reference','duration':'10','light_overlay':False},
                      'provider_record':{'task_id':'fixture-task','reference_qc_override':False},
                      'reference_hashes':{n:digest(self.root/n) for n in ('storyboard.png','identity.png')}}
        self.save('motion.provenance.json', provenance)
        shot = {'generation_root':str(self.root), 'source_duration':10}
        validate_source(src, shot, digest(src))
        for field, value in [('model','veo3.1'), ('model','omni_flash-10s-fl')]:
            self.save('motion.provenance.json', {**provenance, field:value})
            with self.assertRaises(ValueError): validate_source(src, shot, digest(src))
        bad = copy.deepcopy(provenance)
        bad['config']['reference_mode'] = 'first-last'
        self.save('motion.provenance.json', bad)
        with self.assertRaises(ValueError): validate_source(src, shot, digest(src))
        image = self.root/'page.png'
        subprocess.run(['ffmpeg','-v','error','-i',str(src),'-frames:v','1',str(image)], check=True, capture_output=True)
        self.save('page.provenance.json', {**provenance, 'sha256':digest(image)})
        with self.assertRaises(ValueError): validate_source(image, shot, digest(image))

    def test_motion_review_cannot_be_omitted(self):
        lib = self.library(1,1)
        lib['shots'][0]['qc'].pop('generated_motion')
        with patch('contracts.validate_source'), self.assertRaisesRegex(ValueError,'generated motion'):
            accepted_shots(lib,self.root)

    def batch_fixture(self):
        lib = self.library(2,1)
        batch = {'target_videos':2, 'variants':[]}
        for i in range(2):
            script, audio = self.root/f'script{i}.txt', self.root/f'audio{i}.wav'
            script.write_text(f'Complete script {i}.')
            audio.write_bytes(f'audio identity fixture {i}'.encode())
            narration = {'market_profile_id':'m','market_profile_sha256':'a'*64,'narration_id':f'n{i}',
                         'script_sha256':digest(script),'audio_sha256':digest(audio),'task_id':str(i),
                         'tts_prompt_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
                         'cues':[{'id':'cue','start':0,'end':3,'claim_ids':['p0']}]}
            edl = {**narration, 'runtime':3, 'segments':[{'shot_id':f's{i}','in':0,'out':3,
                                                         'timeline_start':0,'timeline_end':3}]}
            journal = {'receipt':{'task_id':str(i),'model':'gem-3.1-tts','request':{'prompt':script.read_text()}},
                       'last_status':{'state':'success','is_final':True}}
            row = {'variant_id':f'v{i}','script':script.name,'audio':audio.name,'bgm':'shared.wav'}
            for key, obj in [('edl',edl),('narration',narration),('journal',journal)]:
                row[key] = self.save(f'{key}{i}.json',obj).name
            batch['variants'].append(row)
        return batch, lib

    def test_batch_independent_jobs_shared_bgm_and_default_count(self):
        batch, lib = self.batch_fixture()
        with patch('contracts.validate_source'):
            self.assertEqual(batch_check(batch,self.root,lib,self.root), [])
            self.assertTrue(batch_check({'variants':batch['variants']},self.root,lib,self.root))
        row = batch['variants'][1]
        first = batch['variants'][0]
        for key in ('audio','script','journal','narration'):
            row[key] = first[key]
        with patch('contracts.validate_source'):
            errors = batch_check(batch,self.root,lib,self.root)
        for kind in ('audio','script','task'):
            self.assertIn('missing/reused batch '+kind, errors)


if __name__ == '__main__':
    unittest.main()
