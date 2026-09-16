---
name: product-ugc-montage
description: "Produce evidence-backed ecommerce UGC ads from a product URL or prepared asset library: lock the market, build a tagged visual library, then edit with GEM-3.1-TTS narration, BGM, product annotations, and video-use/FFmpeg QA."
---

# Product UGC Montage

Use this skill for short-form ecommerce UGC ads (TikTok, Reels, Shorts) made from a product URL or an existing product-ugc asset library. It covers evidence capture, product cognition, claim safety, visual asset generation, audio-first editorial, and release QA. It is not a long-form documentary workflow.

## Outcome

Every completed run should contain:

- one or more vertical MP4 variants;
- portable product evidence and a claim ledger;
- a tagged, multi-variant visual asset library with reserve clips;
- a machine-readable EDL/timeline and source audit;
- one complete target-language narration track, one approved/original BGM track, and a product-annotation plan/render;
- a QA report covering claim support, audio safety, annotation timing, playable cuts, and market consistency.

## Operating rules

1. **Market is immutable.** Freeze `analysis/market-profile.json` before prompts, casting, narration, overlays, product annotations, optional subtitles, or CTA. Never mix languages, locale conventions, people, or scene context inside one run.
2. **Evidence beats copy.** Product claims come from the evidence ledger. Separate `confirmed`, `page_claim_needs_visual_proof`, `inferred`, and `rejected`; never invent dimensions, wind ratings, accessories, percentages, or performance guarantees.
3. **Generation requires authorization.** A URL is not permission to spend. Before the first paid request, show the user the market, SKU/colorway, confirmed claims, excluded claims, number of variants, model, duration/aspect, and audio policy. Get explicit confirmation immediately before submission.
4. **Use the canonical generation route.** Product cognition, identity/usage references, prompt generation, keyframes, provider submission, and L1/L2 QC must use the maintained `product-ugc-pipeline` adapters. Do not bypass its reference, payment, retry, or provider gates.
5. **Source audio is always muted in this workflow.** Smart editing analyzes picture, motion, composition, identity, and evidence relevance only, then selects shots by selling point. It must not preserve, repair, or remix source speech, room tone, or music. The final master contains one generated narration track and one BGM bed.
6. **Narration defines runtime; never hard-code a target duration.** First write one complete Japanese narration for the whole ad, then synthesize one complete GEM-3.1-TTS track, obtain its real duration and word/phrase timing, and derive `runtime = narration_duration + headroom_before + clean_tail_after`. Choose trims to fill that derived runtime; do not stretch, loop, or pad to 15/25/30 seconds. Use 0.3–0.5 seconds of headroom before the first phrase and at least 1 second after the final phrase. Do not pad a cut with an accidental frozen frame; finish on a moving, semantically relevant shot whenever possible.
7. **Do not use native-audio cut gates.** Since all source audio is muted, ASR on source clips is diagnostic only. Validate the unified narration against the final picture and reject incomplete sentence tails or audio/picture drift.
8. **Keep evidence and media separate.** Preserve source files. Write derivatives, EDLs, transcripts, renders, and QA under the run's `edit/` (or `renders/`) directory.
9. **Score before choosing.** Run the reusable asset-diversity and dynamic-ending scorers before delivery; use their results to trigger another AI edit pass, not as a replacement for visual review.
10. **Plan batch size after the library is complete.** Run `scripts/plan_variant_batch.py` after visual assets pass QC. Report the theoretical combination ceiling, a conservative reviewable hard cap, and a recommended starting batch; require the user to choose `N` before parallel rendering or paid BGM/TTS work.
11. **Parallelize only independent variants.** Once market, claims, narration, provider authorization, and asset gates are shared and frozen, render each selected variant independently. Every variant still needs its own EDL, annotations, BGM assignment, dynamic-ending score, and release QA; never publish raw combinatorial duplicates.

## Current end-to-end flow

| Phase | Decision | Required outputs |
|---|---|---|
| 0. Route | URL vs local library; target market; product-video vs hybrid | frozen market profile, versioned run directory |
| 1. Evidence | gallery/SKU/detail capture and limitations | product manifest, image analysis, product brief |
| 2. Claims | buyer problem → product intervention → visible proof | claim ledger and benefit ladder |
| 3. Generate | identity/usage refs, keyframes, visual-only clips | accepted asset library and reserve set |
| 4. Batch plan | diversity score, accepted/reserve counts, theoretical combinations, review cap | `edit/variant_batch_plan.json`, user-selected `N` |
| 5. Audio first | complete Japanese script, one GEM-3.1-TTS track, passing BGM candidate pool | narration text/audio, word/phrase timing, audio provenance |
| 6. Video-use edit | inventory, transcript cache, visual checks, EDLs, strategy confirmation | `edit/transcripts/`, `takes_packed.md`, one EDL per variant, annotation plans |
| 7. Render | parallel per-variant extraction, narration-derived runtime, annotations, BGM assignment, optional subtitles last | preview and final MP4 set |
| 8. Release QA | technical, semantic, audio, market and dynamic-ending checks per variant | QA reports, hashes, delivery manifest |

## 0. Route and initialize

When the request starts with a product URL, read [references/product_pipeline.md](references/product_pipeline.md) for the route, evidence, market-lock, generation-authorization, and ownership gates.

If a product URL is supplied, ask one focused question before crawling: **which country/market is this video for?** If the user already specified it, lock that answer. A bare URL is the `product_video` route; a URL plus local videos is the `hybrid` route.

Echo the route before collection:

`ChronoForge → product-ugc-pipeline → ego-browser evidence capture`

Create and freeze `analysis/market-profile.json` with country, region, locale, target language/script, currency/claim conventions, subtitle style, voice/casting profile, and scene-context rules. For TikTok Shop or another session/region-sensitive page, use `ego-browser`; capture the complete gallery, SKU/colorway images, detail-description images, packaging/posters, source URLs, extraction method, and limitations. Do not start from one visible image or a generic HTTP shell.

Portable product artifacts:

`evidence/product/product_manifest.json`, `evidence/product/image_analysis.json`, `evidence/product/product_brief.json`, `analysis/claim-ledger.json`, and `manifests/timeline.json`.

## 1. Product cognition and claims

Run built-in vision over every downloaded product image. Classify the production family and physical traits, then synthesize the product brief. Build the claim ledger and a benefit ladder for each confirmed selling point:

`buyer problem → supported product intervention → buyer-visible result → proof moment`

Do not promote inferred claims into narration or on-screen copy. Keep rejected/conflicting claims recorded so later prompts cannot reintroduce them.

## 2. Generate and form the asset library

Generate identity and usage sheets before video jobs and pass keyframe QC. Then run the maintained pipeline in order:

`product cognition → category/trait/risk routing → identity/usage sheets → prompts → Image2 keyframes → keyframe QC → video submission → L1/L2 video QC`

Pass the frozen market profile into every prompt and variant manifest. Use market-appropriate people, wardrobe, locations, gestures, spoken language, and cultural context. If a video model cannot reliably speak the target language, request visual-only B-roll and reserve speech for unified target-language TTS.

Organize accepted clips by selling point (for example `coverage_28sqm/`, `uv_upf50/`, `water_pu2000/`). Record variant ID, evidence, duration, model, provenance, audio mode, QC status, and reserve status. Failed or superseded clips never enter the active library.

### Source-audio policy

Default prompt:

`No spoken dialogue, no narration, no singing, no music.`

Treat every generated clip as visual-only B-roll. Inventory any source audio for diagnostics, then remove it before concatenation. Do not offer a native-audio exception inside this product-ad workflow; source speech, room tone, and music are never part of the final master. Read `references/audio_contract.md` for the unified-audio contract.

## 3. Build the complete Japanese narration and unified audio first

Write one complete, natural Japanese narration for the whole ad in the frozen market profile. Do not generate per-shot fragments and do not let shot selection rewrite the script after TTS. The default narration provider is **GEM-3.1-TTS** via the maintained updrama adapter; use one provider-supported voice for the entire run. Retain the task receipt, returned audio, script, and word-level timing.

Use a BGM **candidate pool**, not one mandatory track for every output. The default candidate is **Suno v4.5 instrumental**; request no vocals and record provenance/license. For a batch, generate or select enough passing candidates to avoid a mechanical same-track export (at minimum two candidates when `N ≥ 4`, unless the user explicitly chooses one shared track). Assign candidates across variants by round-robin or mood mapping, then fit each to the derived runtime. Avoid continuous sine tones, single-frequency drones, unfiltered hums, audible looping seams, vocals, and dramatic drops: these fail the BGM gate. Mix the chosen BGM approximately **8–12 dB below the narration** (measure relative integrated/short-term loudness, not only a raw gain value), add gentle head/tail fades, and keep narration, BGM, and annotation assets separate until each final mix. All source-clip audio is muted before concatenation. If Suno candidates fail musicality, no-vocal, seam, or hum checks, keep Suno as a failed candidate and switch to an approved/licensed provider or clearly labeled original instrumental fallback; do not silently reuse a bad bed. Read [references/audio_providers.md](references/audio_providers.md) before submitting either provider task. The adapters live at `scripts/providers/updrama_client.py`; they must never be called until the paid-audio gate is explicitly confirmed.

### Product annotations, not subtitles

The default on-screen text is a **product annotation layer** tied to visual proof moments, not a transcription of the narration. Each annotation should be short (usually one benefit or spec), evidence-linked, and timed to the shot that demonstrates it. Validate the plan against [references/product_annotation.schema.json](references/product_annotation.schema.json) and start from [references/product_annotation_template.json](references/product_annotation_template.json) (ASS fallback: [references/product_annotation_template.ass](references/product_annotation_template.ass)). Use a schema such as:

`{id, start, end, text, claim_id, anchor, style, animation}`

For a TikTok-style treatment based on the supplied reference image:

- use a semi-transparent warm-gray rectangular card around the center/lower-middle safe area;
- use bold white Japanese text with a dark outline/shadow;
- highlight the key spec or badge in orange (`#FF6A00`) and keep one annotation per proof beat;
- use quick fade/slide reveals, 1.2–2.8 seconds per card, with no fake TikTok chrome or engagement UI;
- keep clear of the platform's bottom caption/action UI and never place important text at the extreme bottom;
- do not burn full narration sentences as subtitles unless the user explicitly requests subtitles.

If optional subtitles are requested, derive them from the narration timing and apply them after all product annotations and other overlays.

## 4. Editorial integration: video-use

When `video-use` is available, use it only for visual analysis, evidence-aware shot ranking, EDL drafting, and visual QA. It must not choose or retain source audio, synthesize narration, or invent BGM. Resolve its installed `SKILL.md` and `helpers/` relative to the available installation; do not assume a fixed user path. Prefer Kinocut for typed local rendering, audio mixing, preflight, receipts, and release checks when installed. It may not replace product cognition, evidence capture, paid provider submission, or generation QC. Read [references/video_use_risks.md](references/video_use_risks.md) and [references/tool_research.md](references/tool_research.md) before declaring a run fully autonomous.

### AI-managed montage mode

After the market, claim, and paid-generation gates pass, let the AI own the editorial loop:

`ingest → visual score/rank → plan batch ceiling → user chooses N → write complete Japanese narration → GEM-3.1-TTS → derive runtime → draft variant annotations → video-use EDLs → mute/concat picture → assign passing BGM candidates (−8 to −12 dB) → parallel preview renders → mechanical QA → visual QA → bounded fix loop → final set`

The user does not need to touch a timeline. Stop only for a missing market, unsupported claim, provider/voice ambiguity, paid authorization, or the same QA failure after three fixes. This is an AI-managed montage, not an unconditional hands-off license to spend or publish.

### Inventory and transcript cache

- `ffprobe` every candidate for duration, frame rate, resolution, audio streams, sample rate, and channel layout.
- For sources with audio, obtain **word-level verbatim** ASR only when it helps understand the picture or diagnose a generated clip; cache it in `edit/transcripts/` and do not re-transcribe unchanged sources. Never use source ASR to preserve source sound.
- Pack phrase-level reading material into `edit/takes_packed.md` for editorial reasoning, while retaining raw word timestamps for cut gates.
- Use `timeline_view` only at decision points: ambiguous pauses, candidate cuts, identity continuity, and every final cut boundary.

All B-roll is visual-only: set source audio to `-an`/mute before concat and do not repair generated dialogue. There is no native-audio assembly mode in this workflow.

### Batch variant planning and parallel rendering

After accepted assets and reserve clips are scored, run:

```bash
python3 scripts/plan_variant_batch.py <library_manifest.json> --include-reserve -o edit/variant_batch_plan.json
```

The planner reports:

- `theoretical_combinations`: the Cartesian ceiling across selling-point clip choices;
- `reviewable_hard_cap`: a conservative cap (default 12) that keeps claim, visual, audio, and release review tractable;
- `recommended_batch`: a smaller starting batch (default 6) for A/B testing;
- `user_choice_required`: always true.

The user chooses `N` from `1..reviewable_hard_cap`. The orchestrator then creates `N` independent EDLs by varying hook, proof order, reserve usage, annotation timing, and BGM candidate assignment. It may render those jobs concurrently with a bounded worker pool (default `min(N, 4)`, configurable to host CPU/GPU capacity), but shared narration and evidence remain immutable. A variant is TikTok-ready only after its own source-audio, sentence-tail, annotation, loudness, black-frame, A/V-sync, diversity, and dynamic-ending checks pass. Theoretical combinations are not a promise to publish them all: collapse near-duplicates and reject unsupported or visually weak combinations.

### Strategy and EDL

Describe the cut strategy in plain language and obtain confirmation before execution, unless the user's current request already specifies the strategy. Build `edit/edl.json` with absolute/portable source paths, `start`, `end`, beat/cue, evidence, reason, and a runtime derived from the narration audio plus explicit headroom/tail. Avoid back-to-back identical compositions. Prefer dynamic final footage over cloned last frames; a final hold is allowed only when intentional, semantically useful, and at least 1 second after speech.

### Render contract

Use `video-use/helpers/render.py` for visual analysis/EDL when available, then use Kinocut's typed workflow or a deterministic FFmpeg fallback for the actual mix/render. If the workspace checkout exists at `./agents/kinocut`, prefer its isolated `./agents/kinocut/.venv/bin/kino` after `kino doctor --json` confirms core readiness:

1. extract each segment separately;
2. apply any grade per segment;
3. strip every source audio stream before concat (`-an` or equivalent);
4. concat the video-only segments;
5. add the single complete GEM narration track and one continuous BGM bed, with BGM 8–12 dB below narration;
6. composite product-annotation/animation layers with shifted PTS;
7. apply optional subtitles **last**;
8. preview, then final render.

`video-use` must produce a video-only base. Kinocut/FFmpeg owns the deterministic unified audio mix and release artifact. Keep the same EDL, boundary, annotation-order, optional-subtitle-order, and QA rules.

After the first preview of every selected variant, run `scripts/score_asset_library.py <library_manifest.json>`, `scripts/score_dynamic_ending.py <rendered.mp4> --edl <edl.json>`, and the unified audio QA. Treat `diversity < 65` or `dynamic ending < 70` as an automatic prompt to revise that variant's EDL; a borderline score requires a visual review before delivery.

## 5. Shot planning and compile

Give the planner the product evidence, frozen market profile, claim ledger, clip manifest, visual tags, and narration cue ranges. Select a proof for each cue (hook/problem, wide result, material/detail, lifestyle reaction, CTA). Do not reuse source dialogue. Normalize to one aspect ratio (normally 9:16), CFR, SDR, and pixel format. Create product annotations from claim-linked proof moments; add subtitles only when explicitly requested, using output-timeline narration timing and safe margins.

## 6. Release gates and self-evaluation

Run `video-use`/Kinocut self-evaluation on the rendered output at every cut boundary (±1.5 seconds) and sample the first 2 seconds, last 2 seconds, and several midpoints. Automatically check: complete Japanese sentence tails against the narration transcript, duplicate sentences, product-annotation/subtitle coverage and overlap, narration/BGM relative loudness (8–12 dB), source-audio absence, black frames, A/V duration and sync, flash/jump, waveform spikes/pops, hidden annotations, wrong overlay frames, unreadable copy, unsupported claim text, and an accidental static ending. Re-render up to three times if needed.

Reject and revise when:

- final ASR does not cover the complete narration script;
- a narration sentence ends mid-word, repeats unexpectedly, or is not present in the final audio;
- any source audio stream remains audible or the BGM is not a single continuous bed;
- narration/BGM separation is outside the 8–12 dB target;
- black-frame detection, duration, or A/V sync checks fail;
- the final frame ends before the narration or the ending is unintentionally frozen;
- a duplicate template sentence appears without intent;
- BGM masks speech or loudness jumps at a cut;
- product annotations are missing, mistimed, cropped, hidden, or detached from their proof moment;
- optional subtitles are missing, mistimed, cropped, or hidden;
- a visual, annotation, subtitle, CTA, person, location, or voice violates the market lock;
- a claim lacks evidence or exceeds its claim guard.

The release report must include the numeric asset-diversity score and dynamic-ending score, the scorer versions, and any automatic revision that they triggered.

Store the final MP4, EDL, narration text/audio, product-annotation plan/render, optional subtitle sidecar, audio-provider provenance, source hashes, transcript cache, and QA report together. Append the strategy and decisions to `edit/project.md` for the next session.

## Canonical examples

For a Japanese canopy library, typical evidence-backed cues are `coverage_28sqm`, `uv_upf50`, and `water_pu2000`. A strong sequence is:

`wide canopy result → sun/shade detail → rain-beading detail → relaxed group use → dynamic CTA`

Use `最大約28㎡`, `UPF50+・UVカット`, and `PU2000MM耐水` only when supported by the ledger. Do not add storm-proof, exact-SKU area, accessory, or conflicting UV-percentage claims.

For the complete Japanese narration, unified BGM mix, sentence-tail, loudness, black-frame, and A/V-sync contract, read [references/audio_contract.md](references/audio_contract.md).

For provider payloads, polling, voice selection, and BGM provenance, read [references/audio_providers.md](references/audio_providers.md). For the `video-use` autonomy boundary and known upstream defects, read [references/video_use_risks.md](references/video_use_risks.md).

For the Kinocut and MoneyPrinterTurbo reference implementations and the resulting tool split, read [references/tool_research.md](references/tool_research.md).
