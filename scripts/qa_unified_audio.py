#!/usr/bin/env python3
"""Fail-closed release QA. ASR/review are supplied evidence, never fabricated here."""
from __future__ import annotations
import argparse
import difflib
import json
import math
import re
import subprocess
import unicodedata
from pathlib import Path
from contracts import digest, load_market, number

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:] or 'command failed')
    return p

def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_entries',
        'format=duration:stream=index,codec_type,duration,start_time','-of','json',str(path)]).stdout)

def stream_interval(info,kind):
    rows=[s for s in info.get('streams',[]) if s.get('codec_type')==kind]
    if len(rows)!=1:
        raise ValueError(f'exactly one {kind} stream required')
    row=rows[0]
    start=float(row.get('start_time',0))
    duration=float(row['duration'])
    if not math.isfinite(start+duration) or duration<=0:
        raise ValueError('invalid stream timestamps')
    return start,start+duration

def black_frames(path):
    out=run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-vf',
        'blackdetect=d=0.10:pix_th=0.10','-an','-f','null','-'])
    return re.findall(r'black_start:\s*([0-9.]+).*?black_end:\s*([0-9.]+)',out.stderr)

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold()
                   if unicodedata.category(c)[0] in ('L','N'))

def asr_check(script, asr, media_hash, language, video_end, offset, narration_duration):
    words=asr.get('words',[])
    if (asr.get('media_sha256')!=media_hash or asr.get('language')!=language
            or not words or not asr.get('engine')):
        raise ValueError('current final-media ASR with engine, language and word timestamps required')
    previous=-1
    for w in words:
        if (not number(w.get('start')) or not number(w.get('end'))
                or not 0<=w['start']<w['end']<=video_end+.05
                or w['start']<previous-.05 or not w.get('text')):
            raise ValueError('invalid or out-of-order ASR word timestamps')
        previous=w['end']
    expected=normalized(script)
    actual=normalized(''.join(w['text'] for w in words))
    if not expected:
        raise ValueError('empty narration script')
    matcher=difflib.SequenceMatcher(None,expected,actual,autojunk=False)
    edits=[{'op':op,'expected':expected[a:b],'heard':actual[c:d]}
           for op,a,b,c,d in matcher.get_opcodes() if op!='equal']
    # Strict comparison is deliberate. Normalization handles punctuation/spacing;
    # linguistic equivalence requires a revised, evidenced transcript, not a bypass.
    return {'pass':actual==expected and words[0]['start']>=offset-.15
            and words[-1]['end']<=offset+narration_duration+.15
            and video_end-words[-1]['end']>=.95,
            'edits':edits,'last_word':words[-1],'clean_tail':video_end-words[-1]['end']}

def pcm(path):
    import numpy as np
    p=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0',
                      '-ac','2','-ar','24000','-f','f32le','-'],capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-1000:])
    # Keep both channels: mono downmix can hide unwanted opposite-phase audio.
    return np.frombuffer(p.stdout,dtype='<f4').reshape(-1,2).astype('float64')

def mix_check(final,narration_stem,bgm_stem):
    import numpy as np
    actual,voice,music=(pcm(p) for p in (final,narration_stem,bgm_stem))
    count=min(len(actual),len(voice),len(music))
    if count<2400 or max(len(actual),len(voice),len(music))-count>2400:
        return {'pass':False,'reason':'post-processing stems must cover entire output timeline'}
    expected=voice[:count]+music[:count]
    error=actual[:count]-expected
    signal=float(np.mean(expected**2))
    noise=float(np.mean(error**2))
    snr=10*math.log10(max(signal,1e-15)/max(noise,1e-15))
    return {'pass':signal>1e-10 and snr>=20,'reconstruction_snr_db':round(snr,2),
            'method':'final decoded PCM versus sum of post-gain/duck/fade/delay stems; >=20dB lossy tolerance'}

def loudness(path,start,end):
    out=run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-vn','-af',
             f'atrim=start={start}:end={end},asetpts=PTS-STARTPTS,ebur128=peak=true',
             '-f','null','-'])
    values=re.findall(r'I:\s*(-?\d+(?:\.\d+)?) LUFS',out.stderr)
    if not values:
        raise RuntimeError('no EBU R128 loudness measurement')
    return float(values[-1])

def relative_loudness(voice,bgm,asr):
    # Group adjacent words into phrases; compare only speech-active intervals.
    spans=[]
    for word in asr['words']:
        a,b=word['start'],word['end']
        if spans and a-spans[-1][1]<.4:
            spans[-1][1]=b
        else:
            spans.append([a,b])
    rows=[]
    for a,b in spans:
        if b-a<.4:
            a=max(0,a-.2)
            b+=.2
        v,m=loudness(voice,a,b),loudness(bgm,a,b)
        rows.append({'start':a,'end':b,'voice_lufs':v,'bgm_lufs':m,'gap_db':v-m})
    return {'pass':bool(rows) and all(8<=r['gap_db']<=12 for r in rows),'phrases':rows}

def evaluate(args):
    checks={}
    def check(name,fn):
        try:
            checks[name]=fn()
        except Exception as exc:
            checks[name]={'pass':None,'error':str(exc)}
    final=probe(args.video)
    va,vb=stream_interval(final,'video')
    check('av_stream_sync',lambda: {'pass':abs(stream_interval(final,'audio')[0]-va)<=.1
          and abs(stream_interval(final,'audio')[1]-vb)<=.1,
          'video_interval':[va,vb],'audio_interval':stream_interval(final,'audio')})
    na,nb=stream_interval(probe(args.narration),'audio')
    narration_duration=nb-na
    check('narration_tail',lambda:{'pass':args.narration_offset>=.3
        and vb-(args.narration_offset+narration_duration)>=.95,
        'tail_seconds':vb-args.narration_offset-narration_duration})
    check('source_audio_muted',lambda:{'pass':not any(s.get('codec_type')=='audio'
        for s in probe(args.video_only)['streams']) and
        abs(stream_interval(probe(args.video_only),'video')[1]-vb)<.1})
    check('black_frames',lambda:{'pass':not black_frames(args.video)})
    asr=json.loads(args.final_asr.read_text()) if args.final_asr else {}
    market=load_market(args.market_profile) if args.market_profile else {}
    check('final_asr_coverage',lambda:asr_check(args.script.read_text(),asr,digest(args.video),
        market['language'],vb,args.narration_offset,narration_duration))
    check('mix_reconstruction',lambda:mix_check(args.video,args.narration_stem,args.bgm_stem))
    check('bgm_timeline_coverage',lambda:{'pass':
        stream_interval(probe(args.bgm_stem),'audio')[0]<=.05 and
        stream_interval(probe(args.bgm_stem),'audio')[1]>=vb-.05})
    check('bgm_relative_loudness',lambda:relative_loudness(args.narration_stem,args.bgm_stem,asr))
    def annotations():
        from validate_annotations import validate
        errors,_=validate(json.loads(args.annotations.read_text()),market,digest(args.market_profile),
                          json.loads(args.claim_ledger.read_text()),vb)
        return {'pass':not errors,'errors':errors}
    check('annotations',annotations)
    def semantic_edl():
        from validate_edl import validate
        from contracts import accepted_shots
        library=json.loads(args.library.read_text())
        narration=json.loads(args.narration_manifest.read_text())
        edl=json.loads(args.edl.read_text())
        errors=validate(edl,narration,accepted_shots(library,args.library.parent,True),market['id'])
        if (library['market_profile_sha256']!=digest(args.market_profile)
                or narration.get('market_profile_sha256')!=digest(args.market_profile)):
            errors.append('library/narration market profile changed')
        if narration.get('audio_sha256')!=digest(args.narration) or narration.get('script_sha256')!=digest(args.script):
            errors.append('stale narration inputs')
        if abs(edl.get('runtime',0)-vb)>.05:
            errors.append('EDL runtime differs from final video')
        if edl.get('video_only_sha256')!=digest(args.video_only):
            errors.append('EDL is not bound to the current clean picture')
        # Every annotation must be covered by a shot proving the same claim.
        shots={s['shot_id']:s for s in accepted_shots(library,args.library.parent,True)}
        annotation_plan=json.loads(args.annotations.read_text())
        for ann in annotation_plan['annotations']+annotation_plan.get('omissions',[]):
            covered=0
            for seg in edl['segments']:
                amount=max(0,min(ann['end'],seg['timeline_end'])-max(ann['start'],seg['timeline_start']))
                if ann['claim_id'] in shots[seg['shot_id']]['claim_ids']:
                    covered+=amount
            if covered<ann['end']-ann['start']-.04:
                errors.append('annotation detached from proof: '+ann['id'])
        return {'pass':not errors,'errors':errors}
    check('semantic_edl',semantic_edl)
    def review():
        data=json.loads(args.review.read_text())
        for key,path in [('video_sha256',args.video),('bgm_stem_sha256',args.bgm_stem),
                         ('market_profile_sha256',args.market_profile)]:
            if data.get(key)!=digest(path):
                raise ValueError('stale/missing review hash: '+key)
        required=('sentence_tail_audible','no_unintended_repeated_speech','bgm_no_seams_vocals_hum',
                  'bgm_rights','no_pops_clipping','annotations_visible_readable',
                  'market_consistency','visual_claim_support','narration_cue_sync',
                  'product_unobscured','dynamic_ending',
                  'subtitles_correct_or_not_requested')
        if not data.get('reviewer') or not data.get('evidence'):
            raise ValueError('reviewer and evidence/timecodes required')
        results=data.get('checks',{})
        missing=[k for k in required if results.get(k) not in ('pass','fail')]
        if missing:
            raise ValueError('missing perceptual review: '+','.join(missing))
        return {'pass':all(results[k]=='pass' for k in required),'checks':results}
    check('perceptual_release_review',review)
    failed=[k for k,v in checks.items() if v.get('pass') is False]
    missing=[k for k,v in checks.items() if v.get('pass') is None]
    return {'schema_version':2,'scorer_version':'2.0','video':str(args.video),
            'status':'fail' if failed else ('incomplete' if missing else 'pass'),
            'failed_checks':failed,'incomplete_checks':missing,'checks':checks}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('video',type=Path)
    ap.add_argument('--narration',type=Path,required=True)
    ap.add_argument('--narration-offset',type=float,default=.4)
    for flag in ('script','video-only','narration-stem','bgm-stem','final-asr','annotations',
                 'market-profile','claim-ledger','edl','library','narration-manifest','review','json-out'):
        ap.add_argument('--'+flag,type=Path)
    args=ap.parse_args()
    try:
        report=evaluate(args)
    except Exception as exc:
        report={'status':'incomplete','error':str(exc)}
    payload=json.dumps(report,ensure_ascii=False,indent=2)
    print(payload)
    if args.json_out:
        args.json_out.write_text(payload+'\n')
    return {'pass':0,'fail':1}.get(report['status'],2)

if __name__=='__main__':
    raise SystemExit(main())
