# Product UGC Forge

[中文](README.md) · English

An evidence-backed skill for ecommerce UGC ads on TikTok, Reels, and Shorts. It turns product evidence, an asset library, Japanese narration, product annotations, autonomous editing, and release QA into a reusable local workflow.

## Core workflow

```text
Lock market and evidence
  → analyze visuals and rank shots by selling point
  → write one complete Japanese narration
  → synthesize one complete GEM-3.1-TTS track
  → mute all source-clip audio
  → one unified soft BGM bed (8–12 dB below narration)
  → product annotations (not subtitles)
  → autonomous edit, render, and QA
```

AI owns the timeline by default. The user only confirms high-risk decisions such as market, product claims, and paid provider submission; the agent can generate the EDL, preview, revise, and package the final output.

## Tool split

- `video-use`: visual analysis, selling-point shot ranking, EDL drafting, and visual QA only.
- [Kinocut](https://github.com/KyaniteLabs/kinocut): preferred for typed local rendering, unified audio mixing, preflight, receipts, black-frame, and loudness checks.
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo): orchestration reference for “script → TTS → BGM → export”; it does not override product evidence or claim rules.

## Audio contract

1. Write the complete Japanese narration before timing shots.
2. Use one GEM-3.1-TTS voice to generate one complete narration file.
3. Mute every source-clip audio stream; source ASR is diagnostic only.
4. Use one continuous, soft, instrumental BGM bed; the default candidate is Suno v4.5 instrumental.
5. Measure the final timeline and keep BGM 8–12 dB below narration.
6. Never submit a paid provider task without explicit authorization.

## Reusable resources

- [`SKILL.md`](SKILL.md): full workflow and decision boundaries.
- [`references/product_annotation.schema.json`](references/product_annotation.schema.json): reusable product-annotation schema.
- [`references/product_annotation_template.json`](references/product_annotation_template.json): TikTok-style annotation template.
- [`references/audio_contract.md`](references/audio_contract.md): unified audio and QA contract.
- [`references/audio_providers.md`](references/audio_providers.md): GEM/Suno provider adapter notes.
- [`references/tool_research.md`](references/tool_research.md): Kinocut and MoneyPrinterTurbo findings.
- [`scripts/providers/updrama_client.py`](scripts/providers/updrama_client.py): GEM-3.1-TTS / Suno adapter.
- [`scripts/qa_unified_audio.py`](scripts/qa_unified_audio.py): automated sentence-tail, duplication, loudness, muting, black-frame, and sync checks.
- [`scripts/score_asset_library.py`](scripts/score_asset_library.py): asset-diversity scoring.
- [`scripts/score_dynamic_ending.py`](scripts/score_dynamic_ending.py): dynamic-ending scoring.

## Quick start

Place this directory on an agent skill search path, for example:

```bash
git clone https://github.com/peipeijiang/product-ugc-forge.git ~/.agents/skills/product-ugc-forge
```

Validate the environment and a run:

```bash
python3 ~/.agents/skills/product-ugc-forge/scripts/check_env.py --edit-dir ./edit
python3 ~/.agents/skills/product-ugc-forge/scripts/validate_annotations.py ./edit/product_annotation_plan.json
python3 ~/.agents/skills/product-ugc-forge/scripts/score_asset_library.py ./asset_library/library_manifest.json
python3 ~/.agents/skills/product-ugc-forge/scripts/score_dynamic_ending.py ./edit/final.mp4 --edl ./edit/video_use_edl.json
```

The provider adapter supports dry-run. A real call requires `UPDRAMA_API_KEY` and a separate paid-audio authorization:

```bash
python3 ~/.agents/skills/product-ugc-forge/scripts/providers/updrama_client.py gem \
  'このテントは広くて、日差しや雨の日にも使いやすいです。' \
  --voice-id Zephyr --dry-run
```

## Release gates

The final video must pass complete Japanese sentence tails, no unintended duplicate sentences, annotation coverage, source-audio removal, 8–12 dB BGM separation, black-frame detection, A/V sync, dynamic ending, and market/claim consistency. Failed checks trigger at most three automatic revisions; ambiguous evidence, market, or paid authorization stops the run for confirmation.

## Design boundary

This skill lets AI run the montage end to end, but it does not delegate product truth, evidence, market lock, provider billing, or commercial publication approval to a single editor. Preserve provenance for generated media and complete visual/audio review before publication.

