# video-use capability boundary

`video-use` is a strong autonomous editorial engine, but it is not a complete product-ad pipeline by itself. It reads transcripts plus on-demand visual composites, emits an EDL, renders with FFmpeg, and can iterate after self-evaluation. Product UGC Forge must keep a supervisory layer around it. For the current workflow, its remit is visual analysis and shot selection; Kinocut is the preferred typed render/mix/receipt backend.

## What it can own

- source inventory and technical probing;
- word-level transcript caching and phrase packing;
- shot/cut selection from an evidence-tagged library;
- EDL creation and per-segment render orchestration;
- overlays/annotations, optional subtitles, grading, and audio mix;
- boundary and end-of-video visual review, retrying a render up to a bounded count.

It must not own narration synthesis, BGM selection, or source-audio preservation. The editorial output handed to the renderer is a video-only EDL.

## What it cannot safely own alone

- product truth, SKU identity, claim approval, or market lock;
- paid generation authorization or provider billing;
- choosing a valid GEM voice or a licensed BGM without a provider contract;
- reliable detection of every codec/audio boundary defect without mechanical QA;
- universal CJK/RTL subtitle rendering across FFmpeg builds and host fonts;
- final legal/commercial approval when evidence or policy is ambiguous.

## Upstream issues to guard against

- [#162 AAC priming can cause clicks after `-c copy` concat](https://github.com/browser-use/video-use/issues/162). Re-encode the continuous final audio or run sample-level boundary QA.
- [#118 subtitle burn-in can fail on macOS and render non-Latin tofu](https://github.com/browser-use/video-use/issues/118). Preflight `libass`, select a known-good CJK font, and prefer product annotations when subtitles are not required.
- [#121 missing preflight/doctor command](https://github.com/browser-use/video-use/issues/121). Product UGC Forge should run its own environment check before paid or long renders.
- [#64 self-evaluation and source-faithful output gaps](https://github.com/browser-use/video-use/issues/64). Pair LLM visual review with mechanical scoring and explicit output profiles.

Kinocut's local `doctor`, workflow receipts, loudness/black-frame checks, and fail-closed preflight are useful compensating controls. MoneyPrinterTurbo's script → TTS → BGM → subtitles → export sequence is a reference for orchestration only; its provider defaults and subtitle-first assumptions do not override this skill's GEM-only narration, unified BGM, and product-annotation policy.

## Recommended autonomy contract

Run the editorial loop automatically after the market/claim/paid gates pass:

`ingest → score library → draft narration → draft annotations → video-use EDL → preview → mechanical QA → visual QA → bounded fix loop → final`

Stop and request user input only for a missing market, unsupported claim, provider/voice ambiguity, paid authorization, or a repeated QA failure after three attempts. This gives the user an AI-managed montage without pretending that unresolved evidence, billing, or codec defects are artistic decisions.
