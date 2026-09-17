"""Offline regression tests. Synthetic media are test fixtures, not production assets."""
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from contracts import accepted_shots,digest,load_market
from plan_variant_batch import plan
from validate_edl import validate as validate_edl
from validate_annotations import validate as validate_annotations
from render_annotations import render
from qa_unified_audio import asr_check,evaluate,mix_check,black_frames,relative_loudness
from providers.updrama_client import UpdramaClient,UpdramaError,build_request
from fingerprint_shots import index as fingerprint_index
from validate_generation_matrix import validate as validate_generation_matrix

def ff(*args):
    subprocess.run(['ffmpeg','-v','error','-y',*map(str,args)],check=True,capture_output=True)

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='montage-regression-')
        self.root=Path(self.tmp.name)
        self.source=self.root/'source.mp4'
        self.source.write_bytes(b'not video: identity-only unit fixture')
        # These unit fixtures test range/EDL logic, not media provenance.
        self.source_gate=patch('contracts.validate_source')
        self.source_gate.start()
        self.addCleanup(self.source_gate.stop)
    def tearDown(self):
        self.tmp.cleanup()
    def library(self):
        shots=[]
        for i in range(6):
            a,b=(i%3)*3,(i%3)*3+3
            source=self.root/f'container-{i//3}.mp4'
            source.write_bytes(f'identity-only fixture {i//3}'.encode())
            shots.append({'shot_id':f's{i}','source_id':f'container-{i//3}','file':str(source),
                'source_sha256':digest(source),'source_duration':10,'in':a,'out':b,'hook_eligible':True,
                'claim_ids':['a' if i<3 else 'b'],'evidence':['page#claim'],'angle':f'角度 {i}',
                'proof_moment':f'proof fixture {i}',
                'creative_slot_id':f'slot-{i}','visual_fingerprint':f'{i+1:048x}',
                'visual_cluster_id':f'vc-{i}',
                'market_profile_id':'market','market_profile_sha256':'a'*64,'status':'accepted','reserve':False,
                'qc':{'status':'pass','source_sha256':digest(source),'in':a,'out':b,
                      'generated_motion':True,'reviewer':'test','evidence':['synthetic test only']},
                'dedup':{'status':'pass','source_sha256':digest(source),'in':a,'out':b,
                         'visual_fingerprint':f'{i+1:048x}','visual_cluster_id':f'vc-{i}'}})
        return {'schema_version':2,'market_profile_id':'market','market_profile_sha256':'a'*64,
                'selling_points':[{'id':'a'},{'id':'b'}],'shots':shots}
    def market(self,locale='en-US'):
        from fontTools.ttLib import TTFont
        if locale=='ja-JP':
            fonts=list(Path('/System/Library/Fonts').glob('*W3.ttc'))
            if not fonts:
                self.skipTest('Japanese fixture font unavailable')
            font=fonts[0]
        else:
            font=Path('/System/Library/Fonts/Helvetica.ttc')
            if not font.exists():
                self.skipTest('fixture font unavailable')
        tt=TTFont(font,fontNumber=0)
        name=next(r.toUnicode() for r in tt['name'].names if r.nameID==1)
        tt.close()
        return {'id':'market','country':'JP' if locale=='ja-JP' else 'US','locale':locale,
                'language':locale[:2],'script':'Jpan' if locale=='ja-JP' else 'Latn',
                'casting_profile':{'context':'local'},'scene_context':{'scene':'camp'},
                'voice_profile':{'style':'relaxed'},'typography':{'font_family':name,'font_file':str(font)}}
    def annotation(self,locale='en-US'):
        text='広々スペース' if locale=='ja-JP' else 'Room to relax'
        style=json.loads((ROOT/'references/product_annotation_template.json').read_text())
        data={'version':2,'market_profile_id':'market','market_profile_sha256':'a'*64,
              'locale':locale,'canvas':'1080x1920','style':style,'annotations':[
              {'id':'ann1','start':.5,'end':2.5,'text':text,'claim_id':'a','evidence':['page#a'],
               'anchor':'lower-middle','animation':'slide-up','accent_text':text[:2]}]}
        ledger={'claims':[{'id':'a','status':'confirmed','evidence':['page#a'],
                           'approved_copy':{locale:[text]}}]}
        return data,ledger
    def test_rejected_and_stale_shots(self):
        lib=self.library()
        lib['shots'][0]['status']='rejected'
        self.assertEqual(len(accepted_shots(lib,self.root)),5)
        lib['shots'][1]['qc']['out']=11
        with self.assertRaises(ValueError): accepted_shots(lib,self.root)
    def test_diverse_planning_and_existing_user_n(self):
        result=plan(self.library(),self.root,cap=6,selected=3)
        self.assertFalse(result['user_choice_required'])
        self.assertEqual(result['theoretical_ceiling'],18)
        self.assertEqual(result['tiktok_release_recommendation']['recommended_initial_batch'],3)
        chosen=result['candidate_preview'][:3]
        self.assertEqual(len({next(x['shot']['shot_id'] for x in c['ordered_shots']
                                   if x['claim_id']=='a') for c in chosen}),3)
        self.assertEqual({c['hook_claim_id'] for c in chosen},{'a','b'})
    def test_duplicate_overlap_blocks(self):
        lib=self.library()
        lib['shots']=lib['shots'][:1]
        lib['shots'][0]['claim_ids']=['a','b']
        self.assertEqual(plan(lib,self.root)['status'],'expand_library')
    def test_near_duplicate_active_clusters_block(self):
        lib=self.library()
        lib['shots'][1]['visual_cluster_id']=lib['shots'][0]['visual_cluster_id']
        lib['shots'][1]['dedup']['visual_cluster_id']=lib['shots'][0]['visual_cluster_id']
        with self.assertRaisesRegex(ValueError,'near-duplicate visual cluster'):
            accepted_shots(lib,self.root)
    def test_six_tiktok_recommendation_when_library_supports_it(self):
        lib=self.library()
        lib['selling_points']=[{'id':f'p{i}'} for i in range(6)]
        lib['shots']=[]
        for p in range(6):
            for v in range(4):
                i=p*4+v
                a=0; b=3
                source=self.root/f'proof-{i}.mp4'
                source.write_bytes(f'test identity {i}'.encode())
                fp=f'{i+100:048x}'; cluster=f'vc-{i}'
                lib['shots'].append({'shot_id':f's{i}','source_id':f'container-{i//3}',
                  'file':str(source),'source_sha256':digest(source),'source_duration':10,
                  'in':a,'out':b,'hook_eligible':True,'claim_ids':[f'p{p}'],'evidence':['page#claim'],
                  'angle':f'angle {v}','creative_slot_id':f'slot-{i}','proof_moment':f'proof fixture {i}',
                  'visual_fingerprint':fp,'visual_cluster_id':cluster,
                  'market_profile_id':'market','market_profile_sha256':'a'*64,
                  'status':'accepted','reserve':False,
                  'qc':{'status':'pass','source_sha256':digest(source),'in':a,'out':b,
                        'generated_motion':True,'reviewer':'test','evidence':['fixture only']},
                  'dedup':{'status':'pass','source_sha256':digest(source),'in':a,'out':b,
                           'visual_fingerprint':fp,'visual_cluster_id':cluster}})
        result=plan(lib,self.root,cap=12,recommended=6)
        self.assertEqual(result['tiktok_release_recommendation']['recommended_initial_batch'],6)
        self.assertEqual(len(result['candidate_preview']),12)
        for left,right in __import__('itertools').combinations(result['candidate_preview'],2):
            overlap=len(set(left['visual_cluster_ids'])&set(right['visual_cluster_ids']))/6
            self.assertLessEqual(overlap,.34)
    def test_multi_claim_ten_second_source_is_range_indexed(self):
        lib=self.library()
        # One 10-second container contributes distinct, non-overlapping proof beats.
        self.assertEqual(len({s['source_id'] for s in lib['shots']}),2)
        self.assertEqual(len(accepted_shots(lib,self.root)),6)
    def test_multi_claim_generation_matrix_and_hook_balance(self):
        plan={'market_profile_id':'market','market_profile_sha256':'a'*64,
              'model':'omni-flash-10s','reference_mode':'omni-reference','target_videos':3,
              'selling_points':[{'id':p,'status':'confirmed','evidence':['page#'+p]} for p in 'abc'],'containers':[]}
        pairs=[('a','b'),('b','c'),('c','a')]
        for i,(hook,other) in enumerate(pairs):
            plan['containers'].append({'container_id':f'c{i}','duration':10,
              'claim_ids':[hook,other],'hook_claim_id':hook,'hook_payoff_by':3,
              'creative_slot_id':f'slot-{i}','scene_geometry':f'geo-{i}',
              'camera_distance':f'distance-{i}','camera_motion':f'move-{i}',
              'creator_staging':f'stage-{i}','proof_composition':f'proof-{i}',
              'beats':[{'start':0,'end':4,'claim_id':hook,'proof_moment':'hook proof'},
                       {'start':4,'end':10,'claim_id':other,'proof_moment':'second proof'}]})
        errors,summary=validate_generation_matrix(plan)
        self.assertEqual(errors,[])
        self.assertEqual(summary['unique_visual_treatments'],3)
        duplicate=copy.deepcopy(plan)
        for axis in ('scene_geometry','camera_distance','camera_motion','creator_staging','proof_composition'):
            duplicate['containers'][1][axis]=duplicate['containers'][0][axis]
        self.assertTrue(validate_generation_matrix(duplicate)[0])
    def test_fingerprint_detects_identical_visuals(self):
        video=self.root/'still.mp4'
        ff('-f','lavfi','-i','color=c=red:s=160x160:d=2','-r','15','-pix_fmt','yuv420p',video)
        h=digest(video)
        draft={'schema_version':2,'shots':[
            {'shot_id':'one','file':str(video),'source_sha256':h,'in':0,'out':.8,'status':'accepted'},
            {'shot_id':'two','file':str(video),'source_sha256':h,'in':1,'out':1.8,'status':'reserve'}]}
        indexed=fingerprint_index(draft,self.root)
        self.assertEqual(indexed['shots'][0]['visual_cluster_id'],indexed['shots'][1]['visual_cluster_id'])
        self.assertTrue(Path(indexed['shots'][0]['file']).is_absolute())
        with self.assertRaises(ValueError): fingerprint_index(draft,self.root,threshold=193)
    def test_legacy_library_blocks(self):
        with self.assertRaises(ValueError): plan({'selling_points':[]},self.root)
    def test_edl_semantics_and_speed(self):
        shots=accepted_shots(self.library(),self.root)
        narration={'market_profile_id':'market','narration_id':'n1','script_sha256':'x',
                   'market_profile_sha256':'a'*64,
                   'audio_sha256':'y','cues':[{'id':'c1','start':0,'end':1,'claim_ids':['a']}]}
        edl={k:narration[k] for k in ('market_profile_id','narration_id','script_sha256','audio_sha256','market_profile_sha256')}
        edl.update(runtime=1,segments=[{'shot_id':'s0','in':0,'out':1,'timeline_start':0,'timeline_end':1}])
        self.assertEqual(validate_edl(edl,narration,shots,'market'),[])
        edl['segments'][0].update(shot_id='s3',**{'in':0,'out':1})
        self.assertTrue(validate_edl(edl,narration,shots,'market'))
        edl['segments'][0]['speed']=1.2
        self.assertIn('speed changes/freeze padding are not allowed',validate_edl(edl,narration,shots,'market'))
        shots2=[dict(s) for s in shots]
        shots2[1]={**shots2[1],'visual_cluster_id':shots2[0]['visual_cluster_id']}
        self.assertIn('repeated visual cluster inside the edit', validate_edl(
            {**edl,'runtime':2,'segments':[
                {'shot_id':'s0','in':0,'out':1,'timeline_start':0,'timeline_end':1},
                {'shot_id':'s1','in':3,'out':4,'timeline_start':1,'timeline_end':2}]},
            {**narration,'cues':[{'id':'c1','start':0,'end':2,'claim_ids':['a']}]},shots2,'market'))
    def test_market_languages_and_all_animation_modes(self):
        for locale in ('en-US','ja-JP'):
            market=self.market(locale)
            data,ledger=self.annotation(locale)
            errors,layout=validate_annotations(data,market,'a'*64,ledger,3)
            self.assertEqual(errors,[])
            for mode in ('none','fade','slide-up','slide-left','scale-in'):
                data['annotations'][0]['animation']=mode
                output=render(data,market,layout)
                self.assertIn(market['typography']['font_family'],output)
                self.assertIn('Dialogue: 0',output)
                self.assertIn('Dialogue: 1',output)
                self.assertIn('\\p1',output)
                if mode.startswith('slide'): self.assertIn('\\move',output)
                if mode=='scale-in': self.assertIn('\\t(0,180',output)
            data['locale']='fr-FR'
            self.assertTrue(validate_annotations(data,market,'a'*64,ledger,3)[0])
    def test_annotation_invalid_style_and_overflow(self):
        data,ledger=self.annotation()
        market=self.market()
        data['style']['animation']['easing']='ease_out_cubic'
        self.assertTrue(validate_annotations(data,market,'a'*64,ledger,3)[0])
        data['style']['animation']['easing']='linear'
        data['style']['safe_zone']['x_max']=.10
        self.assertTrue(validate_annotations(data,market,'a'*64,ledger,3)[0])
        data['style']['safe_zone']['x_max']='bad'
        self.assertTrue(validate_annotations(data,market,'a'*64,ledger,3)[0])
    def test_asr_tail_duplicate_and_stale(self):
        asr={'media_sha256':'x','engine':'test','language':'en','words':[
            {'text':'Relax','start':.5,'end':1},{'text':'outside','start':1,'end':2}]}
        self.assertTrue(asr_check('Relax outside.',asr,'x','en',3.5,.4,2)['pass'])
        self.assertFalse(asr_check('Relax outside today.',asr,'x','en',3.5,.4,2)['pass'])
        self.assertFalse(asr_check('Relax outside outside.',asr,'x','en',3.5,.4,2)['pass'])
        with self.assertRaises(ValueError): asr_check('Relax outside',asr,'wrong','en',3.5,.4,2)
    def test_broken_blackdetect_is_not_pass(self):
        with self.assertRaises(RuntimeError): black_frames(self.source)
    def test_missing_audio_evidence_never_passes(self):
        args=argparse.Namespace(video=self.source,narration=self.source,narration_offset=.4)
        for key in ('script','video_only','narration_stem','bgm_stem','final_asr','annotations',
                    'market_profile','claim_ledger','edl','library','narration_manifest','review'):
            setattr(args,key,None)
        final={'streams':[{'codec_type':'video','duration':'11.4','start_time':'0'},
                          {'codec_type':'audio','duration':'1','start_time':'0'}]}
        narration={'streams':[{'codec_type':'audio','duration':'10','start_time':'0'}]}
        with patch('qa_unified_audio.probe',side_effect=[final,narration]),patch('qa_unified_audio.black_frames',return_value=[]):
            result=evaluate(args)
        self.assertEqual(result['status'],'fail')
        self.assertIn('av_stream_sync',result['failed_checks'])
        self.assertIn('final_asr_coverage',result['incomplete_checks'])
    def test_provider_resume_never_reposts(self):
        client=UpdramaClient(api_key='test-not-real',journal=self.root/'task.json')
        with patch.object(client,'_request',return_value={'data':{'task_id':7}}) as req:
            a=client.create_gem_tts('Hello','voice')
            b=client.create_gem_tts('Hello','voice')
            self.assertEqual(a.task_id,b.task_id)
            self.assertEqual(req.call_count,1)
            self.assertEqual(client.resume().task_id,'7')
        with self.assertRaises(UpdramaError): client.create_gem_tts('Different','voice')
    def test_provider_uncertain_create_blocks_second_post(self):
        client=UpdramaClient(api_key='test-not-real',journal=self.root/'uncertain.json')
        with patch.object(client,'_request',side_effect=UpdramaError('connection lost')) as req:
            with self.assertRaises(UpdramaError): client.create_gem_tts('Hello','voice')
            with self.assertRaises(UpdramaError): client.create_gem_tts('Hello','voice')
            self.assertEqual(req.call_count,1)

    def test_provider_contract_rejects_unconfigured_or_invalid_paid_request(self):
        with self.assertRaises(UpdramaError): build_request('musicgen','x',{})
        with self.assertRaises(UpdramaError): build_request('gem-3.1-tts','x',{})
        with self.assertRaises(UpdramaError): build_request('suno-v4.5','x',{'make_instrumental':'song'})
        request=build_request('doubao-tts-2.0','x',{'voice_id':'v','emotion':'auto','emotion_scale':'5'})
        self.assertNotIn('emotion_scale',request['params'])
    def test_status_wrapping_and_recording(self):
        client=UpdramaClient(api_key='test-not-real',journal=self.root/'status.json')
        with patch.object(client,'_request',return_value={'data':{'task_id':9}}):
            client.create_gem_tts('Hello','voice')
        with patch.object(client,'_request',return_value={'data':{'state':'running','is_final':False}}):
            self.assertEqual(client.status('9')['state'],'running')
        self.assertEqual(json.loads(client.journal.read_text())['last_status']['state'],'running')
    def test_real_mix_and_annotation_render(self):
        # Two synthetic tones only exercise the numeric mixer, not BGM quality.
        voice,music,mixed=(self.root/x for x in ('voice.wav','music.wav','mix.wav'))
        ff('-f','lavfi','-i','sine=frequency=500:duration=3','-af','volume=0.5',voice)
        ff('-f','lavfi','-i','sine=frequency=1000:duration=3','-af','volume=0.12',music)
        ff('-i',voice,'-i',music,'-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0',mixed)
        self.assertTrue(mix_check(mixed,voice,music)['pass'])
        self.assertFalse(mix_check(voice,voice,music)['pass'])
        for locale in ('en-US','ja-JP'):
            data,ledger=self.annotation(locale)
            market=self.market(locale)
            errors,layout=validate_annotations(data,market,'a'*64,ledger,3)
            self.assertEqual(errors,[])
            ass=self.root/f'{locale}.ass'
            ass.write_text(render(data,market,layout))
            output=self.root/f'{locale}.png'
            ff('-f','lavfi','-i','color=c=blue:s=1080x1920:d=3',
               '-vf',f'ass={ass}','-ss','1','-frames:v','1',output)
            self.assertGreater(output.stat().st_size,10000)

if __name__=='__main__':
    unittest.main()
