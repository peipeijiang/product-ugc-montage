#!/usr/bin/env python3
"""Batch gate: distinct picture openings, unique full narration jobs; shared BGM allowed."""
import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path
from contracts import accepted_shots, digest, overlap
from validate_edl import validate as validate_edl


def validate(data, root, library, library_root):
    def path(value):
        p = Path(value)
        return p if p.is_absolute() else Path(root) / p
    def read(value):
        return json.loads(path(value).read_text())
    target = data.get('target_videos', 20)
    variants = data.get('variants', [])
    errors = []
    if type(target) is not int or target < 1 or len(variants) != target:
        errors.append('batch must contain the requested count (default 20); never silently pad/reduce')
    shots = accepted_shots(library, library_root, True)
    lookup = {s['shot_id']: s for s in shots}
    seen = {k: set() for k in ('variant_id', 'narration_id', 'script', 'audio', 'task', 'opening')}
    openings = []
    for item in variants:
        edl, narration, journal = read(item['edl']), read(item['narration']), read(item['journal'])
        errors.extend(validate_edl(edl, narration, shots, library['market_profile_id']))
        script, audio = path(item['script']), path(item['audio'])
        script_hash, audio_hash = digest(script), digest(audio)
        if narration.get('script_sha256') != script_hash or narration.get('audio_sha256') != audio_hash:
            errors.append('narration hashes do not match this variant files')
        if narration.get('market_profile_sha256') != library['market_profile_sha256']:
            errors.append('narration market hash differs from library')
        receipt = journal.get('receipt', {})
        status = journal.get('last_status', {})
        request = receipt.get('request', {})
        if (receipt.get('model') not in ('gem-3.1-tts', 'doubao-tts-2.0')
                or not receipt.get('task_id') or status.get('state') != 'success'
                or status.get('is_final') is not True
                or str(narration.get('task_id')) != str(receipt.get('task_id'))):
            errors.append('each video requires its own successful complete GEM/Doubao task receipt')
        # TTS prompt may contain delivery instructions; bind exact submitted text
        # separately from the script whose words are checked by final ASR.
        prompt = request.get('prompt', '')
        if not prompt or hashlib.sha256(prompt.encode()).hexdigest() != narration.get('tts_prompt_sha256'):
            errors.append('narration must bind its actual full TTS request prompt')
        segments = edl.get('segments', [])
        first = segments[0] if segments else {}
        shot = lookup.get(first.get('shot_id'), {})
        if (not shot or shot.get('hook_eligible') is not True
                or first.get('timeline_start') != 0 or first.get('timeline_end', 0) < 3):
            errors.append('first three seconds require an accepted independent hook shot')
        elif all(k in first for k in ('in', 'out')):
            openings.append({**shot, 'in': first['in'], 'out': first['in']+3})
        values = {'variant_id': item.get('variant_id'), 'narration_id': narration.get('narration_id'),
                  'script': re.sub(r'\s+', '', script.read_text()), 'audio': audio_hash,
                  'task': str(receipt.get('task_id', '')), 'opening': shot.get('visual_cluster_id')}
        for key, value in values.items():
            if not value or value in seen[key]:
                errors.append('missing/reused batch '+key)
            seen[key].add(value)
    if any(overlap(a, b) for a, b in itertools.combinations(openings, 2)):
        errors.append('opening source ranges overlap across videos')
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('batch', type=Path)
    ap.add_argument('--library', type=Path, required=True)
    ap.add_argument('-o', '--output', type=Path)
    args = ap.parse_args()
    try:
        errors = validate(json.loads(args.batch.read_text()), args.batch.parent,
                          json.loads(args.library.read_text()), args.library.parent)
        result = {'status': 'fail' if errors else 'pass', 'errors': errors,
                  'scope': 'batch identity gate; per-video release QA and rendered-opening visual review still required'}
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(payload+'\n')
        print(payload)
        return 1 if errors else 0
    except Exception as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
