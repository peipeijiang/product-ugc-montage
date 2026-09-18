#!/usr/bin/env python3
"""Backtest frozen budget reports against recorded completed-run outcomes; no API calls."""
import argparse
import json
from pathlib import Path
from contracts import digest


def audit(data, root):
    rows, ids = [], set()
    for run in data.get('runs', []):
        ident=run.get('run_id')
        if not ident or ident in ids:
            raise ValueError('unique run_id required')
        ids.add(ident)
        if run.get('complete') is not True:
            continue
        for key in ('actual_generated_sources','actual_delivered_videos'):
            if type(run.get(key)) is not int or run[key]<0:
                raise ValueError('nonnegative actual run counts required')
        path=Path(run['budget_file'])
        path=path if path.is_absolute() else Path(root)/path
        if digest(path)!=run.get('budget_sha256'):
            raise ValueError('budget changed after prediction; do not backfill forecasts')
        report=json.loads(path.read_text())
        estimate=report.get('predicted_source_count')
        point=estimate.get('point') if isinstance(estimate,dict) else estimate
        if point is not None and (type(point) is not int or point<0):
            raise ValueError('invalid frozen prediction')
        actual=run['actual_generated_sources']
        rows.append({'run_id':ident,'predicted_sources':point,'actual_generated_sources':actual,
                     'signed_count_error':actual-point if point is not None else None,
                     'absolute_count_error':abs(actual-point) if point is not None else None,
                     'delivery_shortfall':max(0,report['target_videos']-run['actual_delivered_videos']),
                     'evidence':run.get('evidence',[])})
        if not run.get('evidence'):
            raise ValueError('actual outcome evidence paths/receipts required')
    errors=[r['absolute_count_error'] for r in rows if r['absolute_count_error'] is not None]
    return {'runs':rows,'evaluated_predictions':len(errors),
            'mean_absolute_source_count_error':sum(errors)/len(errors) if errors else None,
            'warning':'Descriptive audit, not validated predictive accuracy. Include failed/over-budget runs and every attempt; do not cherry-pick.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('outcomes',type=Path)
    ap.add_argument('-o','--output',type=Path,required=True)
    args=ap.parse_args()
    result=audit(json.loads(args.outcomes.read_text()),args.outcomes.parent)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
