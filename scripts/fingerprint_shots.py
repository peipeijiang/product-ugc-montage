#!/usr/bin/env python3
"""Compute range-bound visual fingerprints and clusters for a draft v2 library.

This is mechanical near-duplicate detection, not visual/claim QC. The output is
a new manifest; sources are never modified.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
from contracts import digest, number

def dhash(image):
    pixels=list(image.convert('L').resize((9,8)).getdata())
    bits=[]
    for y in range(8):
        row=pixels[y*9:(y+1)*9]
        bits.extend(a>b for a,b in zip(row,row[1:]))
    value=sum(int(bit)<<i for i,bit in enumerate(bits))
    return f'{value:016x}'

def fingerprint(path,start,end):
    values=[]
    with tempfile.TemporaryDirectory(prefix='ugc-fingerprint-') as td:
        for i,ratio in enumerate((.2,.5,.8)):
            frame=Path(td)/f'{i}.png'
            at=start+(end-start)*ratio
            p=subprocess.run(['ffmpeg','-v','error','-ss',f'{at:.6f}','-i',str(path),
                              '-frames:v','1','-vf','scale=320:-1',str(frame)],capture_output=True)
            if p.returncode or not frame.is_file():
                raise ValueError(f'cannot decode shot frame at {at:.3f}s: {path}')
            with Image.open(frame) as im:
                values.append(dhash(im))
    return ''.join(values)

def distance(a,b):
    if len(a)!=len(b):
        raise ValueError('fingerprint lengths differ')
    return sum((int(x,16)^int(y,16)).bit_count() for x,y in zip(
        [a[i:i+16] for i in range(0,len(a),16)],
        [b[i:i+16] for i in range(0,len(b),16)]))

def index(data,root,threshold=18):
    if not isinstance(threshold,int) or isinstance(threshold,bool) or not 0<=threshold<=192:
        raise ValueError('threshold_bits must be an integer in 0..192')
    if data.get('schema_version')!=2 or not isinstance(data.get('shots'),list):
        raise ValueError('draft must be a schema_version=2 shot library')
    representatives=[]
    for shot in data['shots']:
        if shot.get('status') not in ('accepted','reserve'):
            continue
        a,b=shot.get('in'),shot.get('out')
        if not number(a) or not number(b) or not 0<=a<b:
            raise ValueError(f'invalid range: {shot.get("shot_id")}')
        path=Path(shot['file'])
        path=path if path.is_absolute() else Path(root)/path
        path=path.resolve()
        actual=digest(path)
        if shot.get('source_sha256')!=actual:
            raise ValueError(f'stale source hash: {path}')
        # Output may live in another directory; preserve the resolved identity.
        shot['file']=str(path)
        fp=fingerprint(path,a,b)
        cluster=None
        for prior_id,prior_fp in representatives:
            if distance(fp,prior_fp)<=threshold:
                cluster=prior_id
                break
        if cluster is None:
            cluster=f'vc-{len(representatives)+1:04d}'
            representatives.append((cluster,fp))
        shot['visual_fingerprint']=fp
        shot['visual_cluster_id']=cluster
        shot['dedup']={'status':'pass','method':'three-frame-dhash-v1',
                       'threshold_bits':threshold,'source_sha256':actual,
                       'in':a,'out':b,'visual_fingerprint':fp,
                       'visual_cluster_id':cluster}
    return data

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest',type=Path)
    ap.add_argument('--threshold-bits',type=int,default=18)
    ap.add_argument('-o','--output',required=True,type=Path)
    args=ap.parse_args()
    try:
        if args.output.resolve()==args.manifest.resolve():
            raise ValueError('write a reviewed derivative; do not overwrite the draft')
        data=index(json.loads(args.manifest.read_text()),args.manifest.parent,args.threshold_bits)
        args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        duplicates={}
        for shot in data['shots']:
            if shot.get('visual_cluster_id'):
                duplicates.setdefault(shot['visual_cluster_id'],[]).append(shot['shot_id'])
        print(json.dumps({'output':str(args.output),'clusters':duplicates},ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'blocked','error':str(exc)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
