# Kinocut and MoneyPrinterTurbo: reference findings

The repositories are downloaded for local reference under the workspace:

- `agents/kinocut/` — Apache-2.0, typed local FFmpeg/MCP editor.
- `agents/MoneyPrinterTurbo/` — MIT, script-to-video batch workflow.

## What to reuse

### Kinocut

Kinocut is the preferred deterministic render and release-check backend when installed. Its useful patterns are:

- `kino doctor` and structured media inspection before a long render;
- a JSON workflow with validate → plan → render → inspect and provenance receipts;
- typed operations for trim/merge/resize/text/compositing/audio instead of ad-hoc FFmpeg flags;
- audio loudness, black-frame, waveform, quality, and release-check surfaces;
- fail-closed preflight for filter bounds, merge compatibility, mix timing, overlays, and text overflow.

For this skill, Kinocut should receive a **video-only EDL** from the editorial planner, then add the single complete GEM narration and one continuous BGM bed. Keep its human visual/audio review checkpoint even when the surrounding loop is automated.

The local reference checkout can be installed without touching system Python:

```bash
cd ./agents/kinocut
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[image,audio-enhanced]'
PATH="$PWD/.venv/bin:$PATH" kino doctor --json
```

Use `./agents/kinocut/.venv/bin/kino` (or the equivalent absolute path) for this workspace. Core rendering works with FFmpeg alone; Hyperframes, Whisper, Demucs, and Torch remain optional integrations.

### MoneyPrinterTurbo

MoneyPrinterTurbo is useful as an orchestration reference, not as the product-claim or editor authority. Its reusable shape is:

`script → TTS → duration → material allocation → BGM → subtitles → batch export`

It demonstrates provider selection, reusable TTS timing, BGM file/provider selection, subtitle timing modes, and batch task control. Adapt those ideas to this skill with these deliberate changes:

- replace per-provider/default TTS with the formal GEM-3.1-TTS adapter;
- use one complete target-language script/audio file, not per-shot narration fragments;
- disable all source audio and build a single unified final mix;
- use one soft instrumental BGM track at 8–12 dB below narration;
- treat product annotations as the default text layer; subtitles are opt-in and applied last;
- retain evidence-linked claim gates and the asset-diversity/dynamic-ending scorers.

## Resulting tool split

`product-ugc-montage` owns market, evidence, claims, paid authorization, and release policy.

`video-use` owns visual analysis, shot ranking, EDL drafting, and visual QA only.

`Kinocut` owns typed local render, unified audio mix, preflight, receipts, and release checks.

`MoneyPrinterTurbo` remains a reference for batch orchestration and provider-independent sequencing; it is not invoked as a hidden provider or allowed to override the frozen market, claim ledger, or audio contract.

## Research links

- [Kinocut](https://github.com/KyaniteLabs/kinocut)
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)
