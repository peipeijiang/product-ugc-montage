"""Montage-only generated-source policy; no API calls and no image-to-video fallback."""
import json
import subprocess
from pathlib import Path

MODELS = {'omni-flash': 'omni-flash', 'omni-flash-10s': 'omni_flash-10s',
          'omni_flash-10s': 'omni_flash-10s'}


def model_id(name):
    if name not in MODELS:
        raise ValueError('only omni-flash / omni-flash-10s all-purpose reference generation is allowed')
    return MODELS[name]


def validate_source(path, shot, source_hash):
    from contracts import digest
    path = Path(path)
    record = json.loads(path.with_suffix('.provenance.json').read_text())
    model_id(record.get('model'))
    config = record.get('config', {})
    provider = record.get('provider_record', {})
    if (record.get('sha256') != source_hash or not record.get('actual_prompt')
            or config.get('reference_mode') != 'omni-reference'
            or str(config.get('duration')) != '10'
            or config.get('light_overlay') is not False
            or not provider.get('task_id') or provider.get('reference_qc_override') is not False):
        raise ValueError('current canonical 10s Omni reference provenance without overrides required')
    refs = record.get('reference_hashes', {})
    root = Path(shot['generation_root'])
    if not root.is_absolute() or len(refs) < 2:
        raise ValueError('absolute generation_root and storyboard + identity reference hashes required')
    for name, expected in refs.items():
        ref = Path(name)
        if digest(ref if ref.is_absolute() else root / ref) != expected:
            raise ValueError('stale generation reference')
    media = json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True).stdout)
    videos = [s for s in media['streams'] if s.get('codec_type') == 'video']
    if (len(videos) != 1 or int(videos[0].get('nb_read_frames', 0)) < 2
            or abs(float(videos[0].get('duration', 0)) - 10) > .12
            or abs(float(shot.get('source_duration', 0)) - float(videos[0]['duration'])) > .04):
        raise ValueError('source must be an actual approximately 10s generated video, never a page image')
