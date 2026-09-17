#!/usr/bin/env python3
"""Heuristic motion QA on clean picture, never text overlays or container names."""
import argparse
import json
import subprocess
import math
from pathlib import Path
import numpy as np
from contracts import digest

def duration(path):
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                      '-of','default=nw=1:nk=1',str(path)],capture_output=True,text=True,check=True)
    value=float(p.stdout)
    if not math.isfinite(value) or value<=0:
        raise ValueError('video duration must be finite and positive')
    return value

def measure(video, length):
    start=max(0,length-2)
    cmd=['ffmpeg','-v','error','-ss',str(start),'-i',str(video),'-t',str(length-start),
         '-an','-vf','fps=8,scale=160:160,format=gray','-f','rawvideo','-']
    p=subprocess.run(cmd,capture_output=True,check=True)
    if len(p.stdout)%(160*160):
        raise ValueError('malformed decoded frames')
    frames=np.frombuffer(p.stdout,dtype=np.uint8).reshape(-1,160,160).astype(float)/255
    if len(frames)<4:
        raise ValueError('insufficient ending frames')
    # Spatial gradients remove uniform exposure shifts; normalized gradients
    # reduce contrast/fade sensitivity. Still a heuristic, not optical-flow proof.
    gx=np.diff(frames,axis=2,append=frames[:,:,-1:])
    gy=np.diff(frames,axis=1,append=frames[:,-1:,:])
    edges=np.sqrt(gx*gx+gy*gy)
    energy=edges.mean(axis=(1,2))
    edges=edges/np.maximum(energy[:,None,None],.01)
    changes=np.mean(np.abs(np.diff(edges,axis=0)),axis=(1,2))
    # Ignore the largest cut flash; require sustained motion, including the tail.
    sustained=float(np.median(changes))
    tail=float(np.median(changes[-3:]))
    value=round(min(100, min(sustained,tail)*240),1)
    return value,{'sustained_edge_change':sustained,'last_frames_edge_change':tail,
                  'samples':len(frames),'mean_texture_energy':float(energy.mean())}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('video',type=Path)
    ap.add_argument('--video-only',required=True,type=Path,help='clean pre-overlay picture used in the render')
    ap.add_argument('--edl',required=True,type=Path)
    ap.add_argument('-o','--output',type=Path)
    args=ap.parse_args()
    try:
        length=duration(args.video)
        if abs(duration(args.video_only)-length)>.05:
            raise ValueError('clean picture/final duration mismatch')
        edl=json.loads(args.edl.read_text())
        if edl.get('video_only_sha256')!=digest(args.video_only):
            raise ValueError('EDL must bind the current clean picture hash')
        tail=[s for s in edl['segments'] if s['timeline_end']>max(0,length-2)
              and s['timeline_start']<length]
        if not tail or abs(tail[-1]['timeline_end']-length)>.05:
            raise ValueError('EDL has no complete output-tail coverage')
        value,details=measure(args.video_only,length)
        report={'scorer_version':'2.0','video':str(args.video),'video_only_sha256':digest(args.video_only),
                'score':value,'grade':'dynamic' if value>=70 else 'needs_visual_review',
                'tail_shot_ids':[s['shot_id'] for s in tail],'measurements':details,
                'heuristic_only':True,'action':'Review actual tail motion. Change EDL only for an unintended static ending; intentional holds need recorded review.'}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if args.output:
            args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        return 0
    except Exception as exc:
        print(json.dumps({'status':'incomplete','error':str(exc)}))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
