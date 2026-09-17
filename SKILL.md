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
- a separately generated complete target-language narration track, one approved/original BGM track, and a product-annotation plan/render for each final video;
- a QA report covering claim support, audio safety, annotation timing, playable cuts, and market consistency.

## Operating rules

Before executing the library, annotation, audio or release scripts, read [references/executable_contracts.md](references/executable_contracts.md). Its v2 formats and fail-closed gates replace legacy whole-clip manifests and unbound text templates. Use `skill-creator` when maintaining these resources, not when producing an ad.

1. **Market is immutable.** Freeze `analysis/market-profile.json` before prompts, casting, narration, overlays, product annotations, optional subtitles, or CTA. Never mix languages, locale conventions, people, or scene context inside one run.
2. **Evidence beats copy.** Product claims come from the evidence ledger. Separate `confirmed`, `page_claim_needs_visual_proof`, `inferred`, and `rejected`; never invent dimensions, wind ratings, accessories, percentages, or performance guarantees.
3. **Generation requires authorization.** A URL is not permission to spend. Before the first paid request, show the user the market, SKU/colorway, confirmed claims, excluded claims, number of variants, model, duration/aspect, and audio policy. Get explicit confirmation immediately before submission.
4. **Use the canonical generation route.** Product cognition, identity/usage references, prompt generation, keyframes, provider submission, and L1/L2 QC must use the maintained `product-ugc-pipeline` adapters. Do not bypass its reference, payment, retry, or provider gates.
5. **Source audio is always muted in this workflow.** Smart editing analyzes picture, motion, composition, identity, and evidence relevance only, then selects shots by selling point. It must not preserve, repair, or remix source speech, room tone, or music. The final master contains one generated narration track and one BGM bed.
6. **Narration defines runtime; never hard-code a target duration.** First write one complete target-language narration for the whole ad, then synthesize one complete GEM-3.1-TTS track, obtain its real duration and word/phrase timing, and derive `runtime = narration_duration + headroom_before + clean_tail_after`. Choose trims to fill that derived runtime; do not stretch, loop, or pad to 15/25/30 seconds. Use 0.3–0.5 seconds of headroom before the first phrase and at least 1 second after the final phrase. Do not pad a cut with an accidental frozen frame; finish on a moving, semantically relevant shot whenever possible.
7. **Do not use native-audio cut gates.** Since all source audio is muted, ASR on source clips is diagnostic only. Validate the unified narration against the final picture and reject incomplete sentence tails or audio/picture drift.
8. **Keep evidence and media separate.** Preserve source files. Write derivatives, EDLs, transcripts, renders, and QA under the run's `edit/` (or `renders/`) directory.
9. **Score before choosing.** Run the reusable asset-diversity and dynamic-ending scorers before delivery; use their results to trigger another AI edit pass, not as a replacement for visual review.
10. **Plan batch size after the library is complete.** Run visual de-duplication and `scripts/plan_variant_batch.py` only after assets pass QC. Report the valid low-repeat capacity and the TikTok recommendation: minimum meaningful test 3, recommended first batch 6 when supported, review ceiling 12. If the library supports fewer than 3 sufficiently distinct variants, recommend expanding it instead of padding the batch. Require the user to choose `N` before parallel rendering or paid BGM/TTS work unless the current request already chose it.
11. **Parallelize only independent variants.** Once market, claims, narration, provider authorization, and asset gates are shared and frozen, render each selected variant independently. Every variant still needs its own EDL, annotations, BGM assignment, dynamic-ending score, and release QA; never publish raw combinatorial duplicates.
12. **Generate clean source footage; add overlays only in final post-production.** Storyboard panels and generated source clips must contain no subtitles, captions, feature badges, callouts, text overlays or graphic overlays. Remove inherited pipeline overlay instructions before submission, leave per-beat overlay fields empty, and omit `--light-overlay`. Add approved product overlays only after the clean picture edit is locked, during final compositing. Every overlay component, including its background and entrance/exit animation, must stay clear of the product and the hands or details demonstrating its use throughout its visible interval.

## Current end-to-end flow

| Phase | Decision | Required outputs |
|---|---|---|
| 0. Route | URL vs local library; target market; product-video vs hybrid | frozen market profile, versioned run directory |
| 1. Evidence | gallery/SKU/detail capture and limitations | product manifest, image analysis, product brief |
| 2. Claims | buyer problem → product intervention → visible proof | claim ledger and benefit ladder |
| 3. Generate | pipeline risk routing, identity/usage refs, Omni storyboards or model-specific keyframes, visual-only clips | feasibility plan, QC-passed reference pack, accepted asset library and reserve set |
| 4. Batch plan | range-level QC, perceptual de-dup, claim-order/shot combinations, TikTok 3/6/12 recommendation | `edit/variant_batch_plan.json`, low-repeat capacity, user-selected `N` |
| 5. Per-video audio batch | one complete script per planned montage, batch submission of separate GEM-3.1-TTS jobs, passing BGM candidate pool | per-variant narration text/audio, word/phrase timing, task receipts and audio provenance |
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

For new montage assets using `omni-flash` or `omni_flash-10s`, follow the pipeline's v2 `--reference-mode omni-reference` route:

1. Use the current risk-routed `storyboard_10s` as the timeline source. Map each planned beat and selling-point proof to panels in one model-generated chronological storyboard image. Keep the frozen market, people, SKU, wardrobe and scene consistent; each panel contains one instance of the product. For a protected route, every panel shows the same verified ready-state configuration.
2. Generate that storyboard through the pipeline's maintained image-provider route, grounded in canonical product evidence and the verified identity grid. Record the actual provider, prompt, reference hashes and image hash in provenance. Do not rename/copy a single first frame into a storyboard or relabel its provenance; a single scene anchor is not the required chronological storyboard.
3. Run storyboard/keyframe QC on the actual storyboard and verify current identity-grid QC. Missing, failed, unknown or malformed QC results do not authorize video submission. Correct the reference or QC issue; do not relax the adapter to accept a substitute reference.
4. Submit the actual chronological storyboard as image 1 and the verified product identity grid as image 2 using `generate_videos_lk888.py --reference-mode omni-reference`. Include the QC-passed operation grid only when the pipeline's non-protected route and continuous-change evidence allow it. High/critical protected routes omit that grid. The storyboard guides shot order; the final video must show full-frame shots, not the reference grid layout.
5. Before each paid request, report the exact reference filenames, model, reference mode, timing and omitted actions, and enforce the provider's reference-count and prompt-length limits. Retain the reference chain and run L1/L2 video QC before accepting any clip.

### Cost-efficient multi-selling-point containers and visual diversity

A paid ten-second Omni container may cover **two or three compatible selling points** when the physical-risk route permits it. This is a source-container optimization, not permission to show all claims at once. Give each point its own chronological proof beat (typically `0–3s`, `3–6s`, `6–10s`), its own storyboard panel(s), and later its own observed `in/out` shot range. The first beat must be the selected hook selling point and create a clear visual payoff inside the first three seconds. Do not reuse the same spoken sentence in generated source clips; these clips remain visual-only B-roll.

Before storyboard generation, allocate a `creative_slot_id` matrix that materially varies at least the scene geometry, camera distance/angle, creator staging or action, proof composition and hook treatment. Changing only wording, crop, clothing color or camera shake is not a new visual version. Across the library, avoid identical starts, identical storyboard layouts, and repeated ready-state hero compositions. Maintain at least three distinct visual clusters per selling point when budget allows; a six-video batch with little/no shot reuse needs correspondingly more clusters. The planner reports both a mathematical zero-reuse upper bound and how many zero-reuse candidates its bounded search actually found; do not present the upper bound as guaranteed capacity.

Write this plan to a source-container matrix and run `scripts/validate_generation_matrix.py` before paid storyboard/video creation. Each ten-second entry must list 2–3 claim IDs, one balanced hook claim with payoff by 3 seconds, contiguous proof beats covering 10 seconds, one unique creative slot, and all five visual-diversity axes. The validator rejects duplicate visual-treatment signatures, missing proofs, unbalanced hooks and fake timing coverage. It validates the plan structure only; the generated frames/clips still need actual visual QC and fingerprint clustering.

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

`ingest → visual score/rank → plan batch ceiling → user chooses N → plan each montage's picture and claim order → write N complete narration scripts → batch-submit N separate GEM-3.1-TTS jobs → derive each runtime → finalize per-variant EDLs and annotations → mute/concat picture → assign passing BGM candidates (−8 to −12 dB) → parallel preview renders → mechanical QA → visual QA → bounded fix loop → final set`

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
- `tiktok_release_recommendation`: minimum 3, recommended initial 6 when supported, and at most 12 for one review round;
- `reviewable_hard_cap`: the number of actually found candidates satisfying de-dup and overlap limits, capped at 12 by default;
- `user_choice_required`: false only when the already-confirmed `N` is supplied through `--selected-n`; planning never authorizes new spending.

The user chooses `N` from `1..reviewable_hard_cap`, unless already specified. Candidate variants deliberately rotate the first-three-second hook claim, selling-point order and proof shots. No candidate may repeat a source range or visual cluster internally; across the batch, pairwise visual-cluster overlap stays within the configured limit. Every selected video receives its own content-matched complete script, narration ID, separately generated full TTS track, timings and QA through the authorized narration batch. Run `validate_edl.py` before rendering: bind each video's own script/audio hashes, cue claim IDs, shot source ranges and output ranges; reject duplicated footage, cue-proof mismatch and speed changes. Every annotation reuses the matching cue's `claim_id` and must lie wholly over picture ranges supporting that claim. Independent validated renders may run with a bounded worker pool. Theoretical ceilings are not publishing promises: rejected, duplicate, near-duplicate or overlapping ranges never become candidates.

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
