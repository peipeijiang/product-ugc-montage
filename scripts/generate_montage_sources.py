#!/usr/bin/env python3
"""Policy wrapper around canonical product-ugc-pipeline; dry-run unless --execute."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from contracts import digest
from source_policy import MODELS, model_id
from validate_generation_matrix import validate


def command(args):
    matrix = json.loads(args.matrix.read_text())
    errors, _ = validate(matrix)
    if errors:
        raise ValueError('; '.join(errors))
    if model_id(matrix['model']) != model_id(args.model):
        raise ValueError('model differs from approved source matrix')
    prompts = json.loads(args.prompts.read_text())
    if prompts.get('montage_matrix_sha256') != digest(args.matrix):
        raise ValueError('prompt batch must bind the current source matrix hash')
    ids = []
    variants = {v['variant_id']: v for v in prompts.get('variants', [])}
    for container in matrix['containers']:
        ident = container.get('variant_id')
        if type(ident) is not int or ident < 1 or ident in ids:
            raise ValueError('each container needs a distinct positive pipeline variant_id')
        variant = variants.get(ident, {})
        if variant.get('montage_plan') != container or not variant.get('storyboard_10s'):
            raise ValueError('each routed prompt needs its exact montage_plan and storyboard_10s')
        ids.append(ident)
    script = args.pipeline / 'scripts/generate_videos_lk888.py'
    if not script.is_file():
        raise ValueError('canonical product-ugc-pipeline installation required')
    product = args.product.resolve()
    if not (product / 'product_manifest.json').is_file():
        raise ValueError('exact canonical product directory with product_manifest.json required')
    return [sys.executable, str(script), str(product), '--products', product.name,
            '--prompts-file', str(args.prompts.resolve()), '--variants', ','.join(map(str, ids)),
            '--model', model_id(args.model), '--reference-mode', 'omni-reference',
            '--duration', '10', '--aspect-ratio', '9:16', '--audio-style', 'none',
            '--workers', str(args.workers), '--create-retries', '1']


def main():
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument('product', type=Path)
    ap.add_argument('--matrix', type=Path, required=True)
    ap.add_argument('--prompts', type=Path, required=True)
    ap.add_argument('--pipeline', type=Path, default=Path(__file__).resolve().parents[2]/'product-ugc-pipeline')
    ap.add_argument('--model', choices=MODELS, default='omni-flash-10s')
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--authorized', action='store_true', help='record existing user authorization; not a substitute for it')
    args = ap.parse_args()
    try:
        if not 1 <= args.workers <= 4:
            raise ValueError('workers must be 1..4')
        cmd = command(args)
        if not args.execute:
            print(json.dumps({'dry_run': True, 'command': cmd}, ensure_ascii=False))
            return 0
        if not args.authorized:
            raise ValueError('paid generation requires existing explicit user authorization')
        env = os.environ.copy()
        if env.get('UPDRAMA_API_KEY'):
            env['LK888_API_KEY'] = env['UPDRAMA_API_KEY']
        return subprocess.run(cmd, check=False, env=env).returncode
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
