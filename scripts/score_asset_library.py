#!/usr/bin/env python3
"""Score accepted shot diversity; --edl scores the selected edit, not the library."""
import argparse
import json
import re
from pathlib import Path
from contracts import accepted_shots, overlap
import itertools

def token_set(text):
    return set(re.findall(r'\w+',text.casefold(),re.UNICODE))

def score(shots):
    if not shots:
        return 0
    angles={s['angle'] for s in shots}
    ranges={(s['source_sha256'],s['in'],s['out']) for s in shots}
    tokens=set().union(*(token_set(s['angle']) for s in shots))
    coverage=min(1,len(ranges)/3)
    return round(100*(.35*len(angles)/len(shots)+.25*len(ranges)/len(shots)+
                      .2*min(1,len(tokens)/3)+.2*coverage),1)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest',type=Path)
    ap.add_argument('--edl',type=Path)
    ap.add_argument('-o','--output',type=Path)
    args=ap.parse_args()
    try:
        data=json.loads(args.manifest.read_text())
        shots=accepted_shots(data,args.manifest.parent,True)
        if args.edl:
            lookup={s['shot_id']:s for s in shots}
            edl=json.loads(args.edl.read_text())
            selected=[]
            for seg in edl['segments']:
                shot=lookup[seg['shot_id']]
                if not shot['in']<=seg['in']<seg['out']<=shot['out']:
                    raise ValueError('EDL range outside accepted shot')
                selected.append({**shot,'in':seg['in'],'out':seg['out']})
            duplicate=(any(overlap(a,b) for a,b in itertools.combinations(selected,2))
                       or len({s['visual_cluster_id'] for s in selected})!=len(selected))
            value=score(selected) if not duplicate else 0
            details=[]
            target='edl'
            recommendation='Revise selected shot ranges/compositions; keep narration cue order.'
        else:
            details=[{'id':p['id'],'score':score([s for s in shots if p['id'] in s['claim_ids']])}
                     for p in data.get('selling_points',[])]
            value=round(sum(r['score'] for r in details)/max(1,len(details)),1)
            target='library'
            recommendation='Re-tag/review available assets or seek approval to expand the library; changing EDL cannot change this score.'
        report={'scorer_version':'2.0','target':target,'score':value,'selling_points':details,
                'grade':'usable' if value>=65 else 'needs_review',
                'heuristic_only':True,'recommendation':recommendation}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if args.output:
            args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        return 0
    except Exception as exc:
        print(json.dumps({'status':'incomplete','error':str(exc)}))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
