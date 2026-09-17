---
name: product-ugc-montage
description: "Produce evidence-backed ecommerce UGC montage batches from product URLs or generated clip libraries: plan 20 distinct-opening ads by default, generate 10s Omni reference footage, and edit each with its own narration, product annotations and release QA."
---

# Product UGC Montage

Use this skill for short-form ecommerce UGC ads (TikTok, Reels, Shorts) made from a product URL or an existing product-ugc asset library. It covers evidence capture, product cognition, claim safety, visual asset generation, audio-first editorial, and release QA. It is not a long-form documentary workflow.

## Outcome

Every completed run should contain:

- one or more vertical MP4 variants;
- portable product evidence and a claim ledger;
- a tagged, multi-variant visual asset library with reserve clips;
- a machine-readable EDL/timeline and source audit;
- a separately generated complete target-language narration track, one approved/original BGM track, and a product-annotation plan/render for each final video;
- a QA report covering claim support, audio safety, annotation timing, playable cuts, and market consistency.

## Operating rules

Before executing the library, annotation, audio or release scripts, read [references/executable_contracts.md](references/executable_contracts.md). Its v2 formats and fail-closed gates replace legacy whole-clip manifests and unbound text templates. Use `skill-creator` when maintaining these resources, not when producing an ad.

1. **Market is immutable.** Freeze `analysis/market-profile.json` before prompts, casting, narration, overlays, product annotations, optional subtitles, or CTA. Never mix languages, locale conventions, people, or scene context inside one run.
2. **Evidence beats copy.** Product claims come from the evidence ledger. Separate `confirmed`, `page_claim_needs_visual_proof`, `inferred`, and `rejected`; never invent dimensions, wind ratings, accessories, percentages, or performance guarantees.
3. **Generation requires authorization.** A URL is not permission to spend. Before the first paid request, show the user the market, SKU/colorway, confirmed claims, excluded claims, number of variants, model, duration/aspect, and audio policy. Get explicit confirmation immediately before submission.
4. **Only model-generated footage enters the montage.** Crawled product photos are evidence/reference inputs, never timeline footage: no still-image holds, slideshows, Ken Burns pans, zooms or FFmpeg image-to-video substitutes. Generate every source container as **10 seconds** using **omni-flash / omni-flash-10s, all-purpose references only**. Veo, first/last-frame routes and `omni_flash-10s-fl` are forbidden. Use `scripts/generate_montage_sources.py`, which delegates to canonical `product-ugc-pipeline` adapters with explicit safe options; never inherit that general-purpose pipeline's defaults. Keep model receipts, reference hashes and actual video QC.
5. **Source audio is always muted in this workflow.** Smart editing analyzes picture, motion, composition, identity, and evidence relevance only, then selects shots by selling point. It must not preserve, repair, or remix source speech, room tone, or music. The final master contains one generated narration track and one BGM bed.
6. **Narration defines final runtime; source generation is fixed at 10s.** For each ad, write its own complete target-language narration, then submit its own complete GEM/Doubao TTS job. Obtain its real duration and word/phrase timing, and derive `runtime = narration_duration + headroom_before + clean_tail_after`. Never share narration files/jobs across videos, split one batch recording, or pad to 10/15/25/30 seconds. Use 0.3–0.5 seconds before the first phrase and at least 1 second after the final phrase. Finish on a moving, relevant shot; no accidental frozen frame.
7. **Do not use native-audio cut gates.** Since all source audio is muted, ASR on source clips is diagnostic only. Validate the unified narration against the final picture and reject incomplete sentence tails or audio/picture drift.
8. **Keep evidence and media separate.** Preserve source files. Write derivatives, EDLs, transcripts, renders, and QA under the run's `edit/` (or `renders/`) directory.
9. **Score before choosing.** Run the reusable asset-diversity and dynamic-ending scorers before delivery; use their results to trigger another AI edit pass, not as a replacement for visual review.
10. **Plan backward from 20 final videos by default.** Before any source generation, inventory confirmed claims, choose the batch's relevant selling points, run `scripts/plan_source_budget.py`, and author/validate a source-container matrix with distinct openings and proof beats. An explicit user count overrides 20; do not ask again for an already chosen count. After source QC, run de-duplication and `plan_variant_batch.py` to test actual capacity. A shortage blocks the full batch: report missing opening/proof coverage and obtain authorization for extra generation or a reduced count. Neither the default nor a mathematical combination count authorizes spending or guarantees 20 releasable ads. Read [references/batch_production.md](references/batch_production.md) for budgeting, source receipts and batch gates.
11. **Distinct openings and independent narration are batch invariants.** Every video must have a different accepted visual opening across its first 3 seconds; swapping text, music, crop or the same shot's starting offset is insufficient. Vary hook claim, scene/action/composition and selling-point order. Repeated body footage stays under the pairwise overlap limit. Each variant needs its own EDL, complete script, TTS task/audio, annotations and QA; BGM may be shared selectively. Run `validate_batch.py` before rendering and visually compare all rendered openings before delivery.
12. **Generate clean source footage; add overlays only in final post-production.** Storyboard panels and generated source clips must contain no subtitles, captions, feature badges, callouts, text overlays or graphic overlays. Remove inherited pipeline overlay instructions before submission, leave per-beat overlay fields empty, and omit `--light-overlay`. Add approved product overlays only after the clean picture edit is locked, during final compositing. Every overlay component, including its background and entrance/exit animation, must stay clear of the product and the hands or details demonstrating its use throughout its visible interval.

## Current end-to-end flow

| Phase | Decision | Required outputs |
|---|---|---|
| 0. Route | URL vs local library; target market; product-video vs hybrid | frozen market profile, versioned run directory |
| 1. Evidence | gallery/SKU/detail capture and limitations | product manifest, image analysis, product brief |
| 2. Claims | buyer problem → product intervention → visible proof | claim ledger and benefit ladder |
| 3. Budget → generate | target 20 → confirmed claims → source budget → unique 10s Omni reference containers | source matrix, risk-routed storyboards, provider receipts, observed proof ranges |
| 4. Validate capacity | range QC, perceptual de-dup, distinct 3s openings and claim-order variation | `edit/variant_batch_plan.json`, target/actual capacity and shortfall |
| 5. Per-video audio batch | N complete scripts and N separate GEM/Doubao jobs; selectively shared BGM pool | unique narration files/tasks/hashes, timings and audio provenance |
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

Generate identity and any required usage sheets through `product-ugc-pipeline`. Select the reference route explicitly before starting image generation:

`product cognition → category/traits and identity/usage QC → pipeline risk routing → routed prompts → model-specific reference generation → reference QC → video submission → L1/L2 video QC`

### Physical-generation risk: source and required record

The risk authority is `product-ugc-pipeline/scripts/creative_risk_router.py`, specifically `build_video_feasibility_plan()`. The canonical `generate_ugc_prompts.py::process_product()` invokes it before prompt generation using the product brief plus manifest selling points; `apply_feasibility_route()` records the result on each variant. Direct Codex-authored prompts must use the same assessment and preserve its constraints and records. Montage must not substitute a hand-written `"generation_risk": "high"` label or invent another scoring system.

Read the pipeline's `references/low-risk-video-direction.md`. This is a conservative heuristic for video-generation difficulty, not a product-safety rating or a measured failure probability. The current implementation scans the full brief's usage steps, claims, use cases, proof moments, classification and state-change contract; it is not an independent visual assessment of each final shot. A high product-level score can therefore coexist with simple ready-state B-roll.

The current router sums matched hazard-group weights: topology/connection change 7, configuration change 5, reversal/inversion 6, precision contact 4, material deformation 4, multi-object coordination 4 and occluded contact 3. It also adds points for multiple steps, state transitions and missing intermediate-state evidence. Thresholds are low 0–3, medium 4–8, high 9–13 and critical 14+. Treat the maintained router code as authoritative if these values change. Its configuration-protection flag also activates when a required contract contains transitions, even below the high threshold.

Persist `video_feasibility_plan` in the prompt batch and record each variant's `generation_risk: {level, score, hazards}`, `safe_demo_direction`, `protect_product_configuration`, `continuous_product_state_change_allowed` and `unsafe_actions_omitted`. Present the score, triggers and actual shooting approach before generation. For protected routes, keep the product in one verified ready-to-use configuration; demonstrate benefits with detail, scale, people and camera motion. Any setup/state-transition hard cut is made later between separate endpoint assets or real footage.

### Omni all-purpose references: chronological storyboard submission

For every new montage source, use only `omni-flash` or `omni-flash-10s` through v2 `--reference-mode omni-reference`. The wrapper maps the display alias `omni-flash-10s` to the existing provider ID `omni_flash-10s`; the `-fl` model is not an alias and is forbidden.

1. Use the current risk-routed `storyboard_10s` as the timeline source. Map each planned beat and selling-point proof to panels in one model-generated chronological storyboard image. Keep the frozen market, people, SKU, wardrobe and scene consistent; each panel contains one instance of the product. For a protected route, every panel shows the same verified ready-state configuration.
2. Generate that storyboard through the pipeline's maintained image-provider route, grounded in canonical product evidence and the verified identity grid. Record the actual provider, prompt, reference hashes and image hash in provenance. Do not rename/copy a single first frame into a storyboard or relabel its provenance; a single scene anchor is not the required chronological storyboard.
3. Run storyboard/keyframe QC on the actual storyboard and verify current identity-grid QC. Missing, failed, unknown or malformed QC results do not authorize video submission. Correct the reference or QC issue; do not relax the adapter to accept a substitute reference.
4. Submit the actual chronological storyboard as image 1 and verified product identity grid as image 2 through `generate_montage_sources.py` (canonical provider execution, fixed 10s, explicit Omni reference mode). Include the QC-passed operation grid only when the pipeline's non-protected route and continuous-change evidence allow it. High/critical protected routes omit that grid. The final video must show full-frame moving shots, not a reference grid or animated product-page photo.
5. Before each paid request, report the exact reference filenames, model, reference mode, timing and omitted actions, and enforce the provider's reference-count and prompt-length limits. Retain the reference chain and run L1/L2 video QC before accepting any clip.

### Cost-efficient multi-selling-point containers and visual diversity

A paid ten-second Omni container may cover **two or three compatible selling points** when the physical-risk route permits it. This is a source-container optimization, not permission to show all claims at once. Give each point its own chronological proof beat (typically `0–3s`, `3–6s`, `6–10s`), its own storyboard panel(s), and later its own observed `in/out` shot range. The first beat must be the selected hook selling point and create a clear visual payoff inside the first three seconds. Do not reuse the same spoken sentence in generated source clips; these clips remain visual-only B-roll.

Before storyboard generation, allocate a `creative_slot_id` matrix that materially varies scene geometry, camera distance/angle, creator staging/action, proof composition and hook treatment. Changing only wording, crop, clothing color or camera shake is not a new visual version. Budget at least one distinct opening container per target video plus a configurable rejection reserve; distribute hooks and supporting proof coverage across the selected confirmed claims. Actual QC can recover additional independent hooks from interior beats, but do not assume those exist before generation. The planner's bounded search and mathematical upper bounds are not guaranteed capacity.

Write the plan to a source-container matrix and run `scripts/validate_generation_matrix.py` before paid storyboard/video creation. Each ten-second entry lists 2–3 compatible confirmed claim IDs (one if only one is supported), a hook beat lasting at least 3 seconds with payoff by 3s, contiguous proof beats covering 10 seconds, a unique creative slot and all five visual-diversity axes. Persist planned times separately from observed `in/out`, claim evidence, action, composition, hook eligibility and motion QC for later reuse. The validator rejects forbidden routes, insufficient opening budgets, duplicate visual treatments, unsupported claims and broken timing; it cannot prove generated visuals match the plan.

Omni all-purpose references are the only supported video-generation route for this skill. Use `--reference-mode omni-reference` with the regenerated chronological storyboard and identity grid; do not substitute endpoint stills or relabel a first/last pair as a storyboard. Multi-selling-point containers still need a visible proof beat for each claim and the same configuration-protection rules.

Pass the frozen market profile into every prompt and variant manifest. Use market-appropriate people, wardrobe, locations, gestures, spoken language, and cultural context. If a video model cannot reliably speak the target language, request visual-only B-roll and reserve speech for unified target-language TTS.

Index accepted **shot ranges**, not just whole containers, by selling point. A ten-second multi-benefit container can yield several accepted shots, each with `shot_id`, `source_id`, file/hash, `in`, `out`, probed source duration, `claim_ids`, evidence, market, angle, `creative_slot_id`, reserve flag and range-bound QC. Run `fingerprint_shots.py` on a draft derivative, visually review its clusters, and retain `visual_fingerprint`, `visual_cluster_id` and range-bound de-dup evidence. Exact/near duplicates cannot both remain active: keep the strongest accepted shot and mark the others reserve/rejected. Rejected/superseded shots never enter planning. Do not count overlapping ranges from the same source as independent usable shots. Migrate old manifests only after inspecting actual shot boundaries; never infer them from titles.

### Source-audio policy

Default prompt:

`No spoken dialogue, no narration, no singing, no music. No subtitles, captions, text overlays, feature badges, callouts, graphic overlays or watermarks. Clean source footage only; all approved overlays will be added later in post-production.`

Treat every generated clip as visual-only B-roll. Inventory any source audio for diagnostics, then remove it before concatenation. Omni-Flash/native-audio output may be generated as a **soundtrack reference candidate** when the model is explicitly available and being evaluated, but it is not automatically accepted: extract it, verify no dialogue/vocals, musicality, scene fit, seams, loudness and rights, then compare it with the configured Suno candidates. Only an explicitly approved, QA-passing native track may be used as the final BGM candidate; source speech, room tone and unapproved music never enter the final master. Read `references/audio_contract.md` for the unified-audio contract.

## 3. Build the complete target-language narration and a separate soundtrack lane

For every selected montage video, first plan its picture sequence, hook and selling-point order, then write a complete, natural target-language narration matched to that video's content. Generate a separate full TTS track for each video: N selected videos require N narration scripts and N separately submitted narration jobs. Do not reuse one narration file across the batch, stitch per-shot speech fragments, or generate one long batch recording to split later. Freeze each script before TTS; derive that video's final runtime and precise picture trims from its own returned audio and timings.

The default narration provider is **GEM-3.1-TTS** via the maintained updrama adapter; query the current catalog and choose **market-profile-compatible, conversational commerce** voices for natural prosody, human-like pauses, and low announcer/robotic coloration. Honor the user's voice constraints across every variant (for example, all female voices when requested). Voice and delivery may vary between videos, but each video uses one consistent voice. **Doubao TTS 2.0** is an approved audition/fallback provider; query its live catalog and compare compatible presets as needed. If a video's voice or script changes, generate its complete track again, re-derive its runtime and re-run its audio/visual QA.

Submit the authorized narration jobs as a batch with bounded concurrency, respecting provider limits, rather than waiting for each result before submitting the next. Use one durable journal per logical job and save a batch manifest mapping `variant_id` to `narration_id`, script path/hash, voice/style, journal, task ID, state, audio path/hash, measured duration and timing path. Poll and download each task independently; resume existing receipts after interruption and reconcile uncertain submissions before retrying. Do not resubmit successful jobs. Each render must bind to its own narration and QA artifacts.

Use a BGM **candidate pool**, not one mandatory track for every output. The default candidate is **Suno v4.5 instrumental**; request no vocals and record provenance/license. For a batch, generate or select enough passing candidates to avoid a mechanical same-track export (at minimum two candidates when `N ≥ 4`, unless the user explicitly chooses one shared track). Assign candidates across variants by round-robin or mood mapping, then fit each to the derived runtime. Avoid continuous sine tones, single-frequency drones, unfiltered hums, audible looping seams, vocals, and dramatic drops: these fail the BGM gate. Mix the chosen BGM approximately **8–12 dB below the narration** (measure relative integrated/short-term loudness, not only a raw gain value), add gentle head/tail fades, and keep narration, BGM, and annotation assets separate until each final mix. All source-clip audio is muted before concatenation. If Suno candidates fail musicality, no-vocal, seam, or hum checks, keep them failed and use only a user-provided or license-confirmed local music file; if no such file exists, stop the audio path and report the missing fallback instead of inventing or silently downloading a model. Read [references/audio_providers.md](references/audio_providers.md) and [references/audio_research_industry.md](references/audio_research_industry.md) before submitting a provider task. The adapters live at `scripts/providers/updrama_client.py` and currently cover only `gem`, `doubao`, and `suno`; they must never be called until the paid-audio gate is explicitly confirmed.

Do not bake the final soundtrack into every video-generation request. Native video audio is useful for exploratory previews, dialogue-led concepts, or diegetic sound-effect references, but it is usually not an independently replaceable music stem. Omni-Flash may be run in a dedicated **native soundtrack reference** pass only when that model is explicitly configured for the current run; if its output is genuinely instrumental, coherent across the full cut, free of speech/vocals/hum and commercially usable, it can enter the same scored candidate pool as Suno after extraction and loudness QA. If native audio cannot be disabled, request `no dialogue, no vocals, no music; subtle diegetic ambience only`, then strip it before the final mix. If Suno fails, use only a user-provided or license-confirmed local music file. Do not call Lyria, Lyria RealTime, Stable Audio Open, MusicGen, ACE-Step or other unconfigured models as an implicit fallback; they require a separately approved install/provider task.

### Product annotations, not subtitles

Create annotations as separate post-production assets and composite them only in the final render; never ask the image or video generator to draw them. Determine placement from each shot's actual product position and motion. Treat the product silhouette and key interaction/proof areas, with a visible clearance margin, as exclusion zones for text, cards, shadows and animated paths. A fixed center/lower-middle position is only a preference when clear. If an overlay intersects an exclusion zone at any point, move it to clear space, shorten or retime it within the matching proof beat, or omit it when no clear readable placement exists. Inspect the full visible interval, including cut boundaries and animation, rather than only its first frame.

The default on-screen text is a **product annotation layer** tied to visual proof moments, not a transcription of the narration. Each annotation should be short, evidence-linked and approved in the frozen locale. The market profile controls language/script, voice/casting, typography and font file; no Japanese, CJK font or female-voice default overrides it. Validate against [references/product_annotation.schema.json](references/product_annotation.schema.json). The [style template](references/product_annotation_template.json) is the `style` object, not a complete plan. Use `render_annotations.py` to generate the actual market-bound ASS; do not render the legacy static sample directly. Unknown style/animation options must fail rather than be silently ignored. Use a schema such as:

`{id, start, end, text, claim_id, anchor, style, animation}`

For a TikTok-style treatment based on the supplied reference image:

- use a semi-transparent warm-gray rectangular card in verified clear space, preferring the center/lower-middle safe area only when it does not cover the product or its demonstration;
- use bold white target-language text with a dark outline/shadow;
- highlight the key spec or badge in orange (`#FF6A00`) and keep one annotation per proof beat;
- use quick fade/slide reveals, 1.2–2.8 seconds per card, with no fake TikTok chrome or engagement UI;
- keep clear of the platform's bottom caption/action UI and never place important text at the extreme bottom;
- do not burn full narration sentences as subtitles unless the user explicitly requests subtitles.

If optional subtitles are requested, derive them from the narration timing and apply them after all product annotations and other overlays.

## 4. Editorial integration: video-use

When `video-use` is available, use it only for visual analysis, evidence-aware shot ranking, EDL drafting, and visual QA. It must not choose or retain source audio, synthesize narration, or invent BGM. Resolve its installed `SKILL.md` and `helpers/` relative to the available installation; do not assume a fixed user path. Prefer Kinocut for typed local rendering, audio mixing, preflight, receipts, and release checks when installed. It may not replace product cognition, evidence capture, paid provider submission, or generation QC. Read [references/video_use_risks.md](references/video_use_risks.md) and [references/tool_research.md](references/tool_research.md) before declaring a run fully autonomous.

### AI-managed montage mode

After the market, claim, and paid-generation gates pass, let the AI own the editorial loop:

`target N (default 20) → confirmed claims → source budget and 10s beat matrix → authorized Omni reference generation → observed ranges/QC/de-dup → distinct-opening capacity check → per-video claim order → N complete scripts and N GEM/Doubao tasks → derive each runtime → EDLs/annotations → batch identity gate → mute/concat → selectively shared passing BGM (−8 to −12 dB) → previews → per-video QA + rendered-opening comparison → bounded fixes → final set`

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

- `theoretical_ceiling`: selling-point permutations × shot choices before overlap/de-dup rejection;
- `zero_reuse_batch_found` and `zero_reuse_batch_upper_bound`: bounded-search evidence and the mathematical ceiling for variants without cross-batch visual-cluster reuse;
- `max_pairwise_visual_overlap`: the enforced cross-variant overlap limit (default 0.34);
- `target_videos`: 20 by default, overridden with `--selected-n N` (also increase `--review-cap` for N > 20);
- `reviewable_hard_cap`: candidates actually found with distinct accepted 3s openings and bounded body overlap;
- `candidate_shortfall` / `status`: `expand_library` exits 2 and saves the report when the target is not met; never silently reduce the requested batch;
- `user_choice_required`: false because this workflow already has a default count; planning never authorizes spending.

Candidate variants rotate hook claims, selling-point order and proof shots, and cannot reuse the same opening cluster or overlapping opening source range. No cut may repeat a range/cluster internally; body reuse across the batch remains bounded. Run `validate_edl.py` and `validate_batch.py` before rendering: verify each video's own full script, audio hashes, successful task receipt, cue-proof alignment and unique opening. The batch gate rejects identical scripts/audio/tasks even when renamed; BGM sharing is allowed. Compare actual rendered first-3s contact sheets/playback, since labels and fingerprints alone cannot prove perceptual diversity. Insufficient footage for a returned narration requires extra accepted proof ranges or a rewritten/re-generated full script, never freeze/loop padding. Every annotation must lie over picture proving the same claim.

### Strategy and EDL

Describe the cut strategy in plain language and obtain confirmation before execution, unless the user's current request already specifies the strategy. Build `edit/edl.json` with absolute/portable source paths, `start`, `end`, beat/cue, evidence, reason, and a runtime derived from the narration audio plus explicit headroom/tail. Avoid back-to-back identical compositions. Prefer dynamic final footage over cloned last frames; a final hold is allowed only when intentional, semantically useful, and at least 1 second after speech.

### Render contract

Use `video-use/helpers/render.py` for visual analysis/EDL when available, then use Kinocut's typed workflow or a deterministic FFmpeg fallback for the actual mix/render. If the workspace checkout exists at `./agents/kinocut`, prefer its isolated `./agents/kinocut/.venv/bin/kino` after `kino doctor --json` confirms core readiness:

1. extract each segment separately;
2. apply any grade per segment;
3. strip every source audio stream before concat (`-an` or equivalent);
4. concat the video-only segments;
5. add this variant's separately generated complete GEM narration track and one continuous BGM bed, with BGM 8–12 dB below narration;
6. after the clean picture edit is locked, composite the separate product-annotation/animation layers with shifted PTS as the final overlay stage, checking product exclusion zones across each full overlay interval;
7. apply optional subtitles **last**;
8. preview, then final render.

`video-use` must produce a video-only base. Kinocut/FFmpeg owns the deterministic unified audio mix and release artifact. Keep the same EDL, boundary, annotation-order, optional-subtitle-order, and QA rules.

Run the library diversity scorer before batch planning. A low **library** score triggers review/re-tagging or a request to expand the library under a new generation budget; editing an EDL cannot fix it. After each preview, score the selected edit with `score_asset_library.py <library> --edl <edl>` and the clean ending with `score_dynamic_ending.py <final> --video-only <clean-picture> --edl <edl>`. Selected-edit diversity below 65 or ending below 70 requires visual review and, if actually defective, an EDL revision. Scores are versioned heuristics, not automatic proof of quality; an intentional hold needs a documented review. Tool errors are incomplete QA, never zero-motion or success.

## 5. Shot planning and compile

Give the planner the product evidence, frozen market profile, claim ledger, clip manifest, visual tags, and narration cue ranges. Select a proof for each cue (hook/problem, wide result, material/detail, lifestyle reaction, CTA). Do not reuse source dialogue. Normalize to one aspect ratio (normally 9:16), CFR, SDR, and pixel format. Create product annotations from claim-linked proof moments; add subtitles only when explicitly requested, using output-timeline narration timing and safe margins.

## 6. Release gates and self-evaluation

`qa_unified_audio.py` is a fail-closed aggregator, not an ASR or vision engine. It checks final audio/video stream timestamps, current final-media ASR, actual timeline stems, reconstructed mix, speech-interval loudness, market/claim-bound annotations and semantic EDL. Supply current hash-bound perceptual review for phoneme tails, pops, musical seams, text visibility, rights and market/visual correctness. Missing/errored evidence yields `incomplete` (exit 2), any defect yields `fail` (exit 1); only full `pass` (exit 0) is releasable. Never report checks as performed merely because the workflow lists them.

Run `video-use`/Kinocut self-evaluation on the rendered output at every cut boundary (±1.5 seconds) and sample the first 2 seconds, last 2 seconds, and several midpoints. Automatically check: complete target-language sentence tails against the narration transcript, duplicate sentences, product-annotation/subtitle coverage and overlap, narration/BGM relative loudness (8–12 dB), source-audio absence, black frames, A/V duration and sync, flash/jump, waveform spikes/pops, hidden annotations, wrong overlay frames, unreadable copy, unsupported claim text, and an accidental static ending. Re-render up to three times if needed.

Reject and revise when:

- final ASR does not cover the complete narration script;
- a narration sentence ends mid-word, repeats unexpectedly, or is not present in the final audio;
- any source audio stream remains audible or the BGM is not a single continuous bed;
- narration/BGM separation is outside the 8–12 dB target;
- black-frame detection, duration, or A/V sync checks fail;
- the final frame ends before the narration or the ending is unintentionally frozen;
- a duplicate template sentence appears without intent;
- BGM masks speech or loudness jumps at a cut;
- generated source footage contains subtitles, captions, feature badges, callouts or graphic overlays;
- product annotations are missing without a documented no-clear-space omission, mistimed, cropped, hidden, or detached from their proof moment;
- any overlay text, background, shadow or animation covers the product or a key interaction/proof area at any time;
- optional subtitles are missing, mistimed, cropped, or hidden;
- a visual, annotation, subtitle, CTA, person, location, or voice violates the market lock;
- a claim lacks evidence or exceeds its claim guard.

The release report must include the numeric asset-diversity score and dynamic-ending score, the scorer versions, and any automatic revision that they triggered.

Store the final MP4, EDL, narration text/audio, product-annotation plan/render, optional subtitle sidecar, audio-provider provenance, source hashes, transcript cache, and QA report together. Append the strategy and decisions to `edit/project.md` for the next session.

## Canonical examples

For a Japanese canopy library, typical evidence-backed cues are `coverage_28sqm`, `uv_upf50`, and `water_pu2000`. A strong sequence is:

`wide canopy result → sun/shade detail → rain-beading detail → relaxed group use → dynamic CTA`

Use `最大約28㎡`, `UPF50+・UVカット`, and `PU2000MM耐水` only when supported by the ledger. Do not add storm-proof, exact-SKU area, accessory, or conflicting UV-percentage claims.

For the complete target-language narration, separate soundtrack lane, unified BGM mix, sentence-tail, loudness, black-frame, and A/V-sync contract, read [references/audio_contract.md](references/audio_contract.md). For the industry model/provider comparison and the native-audio decision, read [references/audio_research_industry.md](references/audio_research_industry.md).

For provider payloads, polling, voice selection, and BGM provenance, read [references/audio_providers.md](references/audio_providers.md). For the `video-use` autonomy boundary and known upstream defects, read [references/video_use_risks.md](references/video_use_risks.md).

For the Kinocut and MoneyPrinterTurbo reference implementations and the resulting tool split, read [references/tool_research.md](references/tool_research.md).
