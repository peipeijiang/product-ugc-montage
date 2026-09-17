"""Shared, fail-closed local contracts. No provider calls on import."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def load_market(path):
    market = json.loads(Path(path).read_text())
    for key in ('id', 'country', 'locale', 'language', 'script', 'casting_profile', 'scene_context', 'voice_profile', 'typography'):
        if not market.get(key):
            raise ValueError(f'market profile missing {key}')
    font = market['typography']
    if not isinstance(font, dict) or not font.get('font_family') or not font.get('font_file'):
        raise ValueError('market typography requires font_family and font_file')
    font_path = Path(font['font_file'])
    if not font_path.is_absolute():
        font_path = Path(path).resolve().parent / font_path
    if not font_path.is_file():
        raise ValueError(f'market font does not exist: {font_path}')
    font['font_file'] = str(font_path)
    return market

def accepted_shots(data, root, include_reserve=False):
    """Reject ambiguous legacy whole-clip manifests; do not invent shot ranges."""
    if data.get('schema_version') != 2 or not isinstance(data.get('shots'), list):
        raise ValueError('migrate to schema_version=2 with shots/source_id/in/out/claim_ids/QC')
    if not data.get('market_profile_id') or len(str(data.get('market_profile_sha256',''))) != 64:
        raise ValueError('library requires market_profile_id and market_profile_sha256')
    ids, slots, signatures, clusters, result, hashes = set(), set(), set(), set(), [], {}
    for shot in data['shots']:
        if shot.get('status') != 'accepted' or (shot.get('reserve') and not include_reserve):
            continue
        required = ('shot_id', 'source_id', 'file', 'source_sha256', 'claim_ids', 'angle',
                    'market_profile_id', 'creative_slot_id', 'visual_fingerprint', 'visual_cluster_id')
        if any(not shot.get(k) for k in required):
            raise ValueError('accepted shot missing identity, evidence or market metadata')
        if shot['shot_id'] in ids:
            raise ValueError('duplicate shot_id')
        ids.add(shot['shot_id'])
        if shot['creative_slot_id'] in slots:
            raise ValueError(f'duplicate creative_slot_id: {shot["creative_slot_id"]}')
        slots.add(shot['creative_slot_id'])
        a, b = shot.get('in'), shot.get('out')
        if not number(a) or not number(b) or not 0 <= a < b:
            raise ValueError(f'invalid shot range: {shot["shot_id"]}')
        if not number(shot.get('source_duration')) or b > shot['source_duration']:
            raise ValueError('shot exceeds probed source_duration')
        if shot['market_profile_id'] != data['market_profile_id']:
            raise ValueError('shot market differs from library market')
        if shot.get('market_profile_sha256') != data['market_profile_sha256']:
            raise ValueError('shot market profile hash differs from library')
        if not isinstance(shot['claim_ids'], list) or not shot.get('evidence'):
            raise ValueError('shot claim_ids/evidence required')
        path = Path(shot['file'])
        path = path if path.is_absolute() else Path(root) / path
        path = path.resolve()
        if path not in hashes:
            hashes[path] = digest(path)
        if hashes[path] != shot['source_sha256']:
            raise ValueError(f'stale source hash: {path}')
        signature = (hashes[path], a, b)
        if signature in signatures:
            raise ValueError(f'duplicate accepted source range: {shot["shot_id"]}')
        signatures.add(signature)
        if shot['visual_cluster_id'] in clusters:
            raise ValueError(
                f'near-duplicate visual cluster is active more than once: {shot["visual_cluster_id"]}; '
                'keep one accepted and mark the rest reserve/rejected'
            )
        clusters.add(shot['visual_cluster_id'])
        qc = shot.get('qc', {})
        if (qc.get('status') != 'pass' or qc.get('source_sha256') != hashes[path]
                or qc.get('in') != a or qc.get('out') != b):
            raise ValueError(f'current range-level QC required: {shot["shot_id"]}')
        dedup = shot.get('dedup', {})
        if (dedup.get('status') != 'pass'
                or dedup.get('source_sha256') != hashes[path]
                or dedup.get('in') != a or dedup.get('out') != b
                or dedup.get('visual_fingerprint') != shot['visual_fingerprint']
                or dedup.get('visual_cluster_id') != shot['visual_cluster_id']):
            raise ValueError(f'current visual de-dup record required: {shot["shot_id"]}')
        result.append({**shot, 'file': str(path)})
    return result

def overlap(a, b):
    return a['source_sha256'] == b['source_sha256'] and max(a['in'], b['in']) < min(a['out'], b['out']) - 1e-6
