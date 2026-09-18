# Executable contracts (v2)

Read before invoking local helpers. These helpers do not create a complete ad on their own; the agent still performs product vision, approved copywriting, actual ASR and perceptual review. Never fabricate their evidence to satisfy a gate. All files live under the current run; old renders remain untouched.

Read [batch_production.md](batch_production.md) for the default-20 pre-generation budget, mandatory Omni/10s/all-purpose route, canonical source provenance and independent narration/opening batch gate. These requirements also apply to existing libraries; missing evidence is not grandfathered in.

## Market binding

Freeze `market-profile.json` with `id`, `country`, `region`, `locale` (BCP-47, e.g. `ja-JP` or `en-US`), `language` (ASR language code, e.g. `ja` or `en`), `script`, `currency`, `casting_profile`, `scene_context`, `voice_profile`, `subtitle_style`, and `typography: {font_family, font_file, font_index: 0}`. Font path may be absolute or relative to the profile. Select a locally installed font that covers the actual copy. Neither Japanese nor a female voice is a global default. Gender/style, pronunciation, persons, scene and all generated spoken/visible language come from this profile.

Hash the profile and pass it to generation prompts, narration, EDL and annotations. Translation is an explicit copywriting step: changing the locale label does not translate the text. Claims require `approved_copy` for that exact locale. For Arabic/RTL/complex scripts, additionally inspect the rendered shaping; a glyph-coverage check is not enough.

## Shot library and narration-aligned EDL

Before generation, read `batch_production.md` and author a demand manifest with one creative brief per requested ad. Budget from individual claim/proof/role/seconds needs, then author compatible 10s source candidates. Sources can hold one complex claim or multiple proofs; interior beats can be independent hooks. No one-source-per-ad minimum or fixed reserve applies. Each submitted matrix binds `demand_sha256`, and every planned beat has `creative_slot_id`, `proof_key`, roles and hook/ending requirements. Use the matrix validator plus demand allocator; a pilot/supplement may cover only targeted gaps.

```bash
python3 scripts/validate_generation_matrix.py edit/source-container-plan.json \
  -o edit/source-container-plan.validation.json
```

Library shape:

```json
{"schema_version":2,"market_profile_id":"jp-run-01","market_profile_sha256":"<profile SHA256>",
 "selling_points":[{"id":"coverage"}],
 "shots":[{"shot_id":"s01","source_id":"container-01","file":"clips/01.mp4",
 "source_sha256":"<actual SHA256>","source_duration":10.0,"in":0.0,"out":3.1,
 "generation_root":"/absolute/canonical/product","hook_eligible":true,
 "proof_keys":["coverage-wide"],"roles":["hook","proof"],"calibration_group":"wide-ready-state-v1","dynamic_ending":false,
 "claim_ids":["coverage"],"evidence":["product-brief#coverage"],"angle":"wide result",
 "proof_moment":"observed wide view demonstrating coverage",
 "creative_slot_id":"coverage-wide-family-A","visual_fingerprint":"<three-frame dHash>",
 "visual_cluster_id":"vc-0001","market_profile_id":"jp-run-01",
 "market_profile_sha256":"<profile SHA256>","status":"accepted","reserve":false,
 "qc":{"status":"pass","source_sha256":"<same SHA256>","in":0.0,"out":3.1,
 "generated_motion":true,"reviewer":"actual reviewer","evidence":["observed product/action motion"]},
 "dedup":{"status":"pass","method":"three-frame-dhash-v1","source_sha256":"<same SHA256>",
 "in":0.0,"out":3.1,"visual_fingerprint":"<same fingerprint>","visual_cluster_id":"vc-0001"}}]}
```

Probe the actual source duration and inspect each accepted range before recording it. One ten-second source may contain two or three non-overlapping claim proofs; these are different shots. QC for a different range/hash is stale. First create a draft with source/range fields, then run `fingerprint_shots.py draft.json -o indexed.json`; visually verify the groupings before accepting/rejecting shots. Mechanical dHash is deliberately conservative and does not replace visual review. Active `creative_slot_id`, source-range signatures and visual clusters must be unique; duplicate/near-duplicate alternatives belong in reserve/rejected. Legacy whole-container manifests must be migrated from observed boundaries, not mechanically guessed.

Use `plan_variant_batch.py library.json --demand edit/creative-demand.json` for production. It checks per-video claim subsets, proof keys, continuous seconds, hooks/endings, reuse and duration-weighted overlap. FEASIBLE is a witness; INFEASIBLE is relative to supplied demand/footage; UNKNOWN means search limits, not a proved shortage. Legacy `--explore` is non-production only. After full per-video TTS, freeze measured timing and reallocate; `validate_batch.py --demand` verifies the actual EDL and independent narration jobs.

Narration manifest: `market_profile_id`, `narration_id`, `script_sha256`, `audio_sha256`, and `cues: [{id,start,end,claim_ids}]`. Cue times are on the **output timeline**, including narration delay. Split mixed-claim sentences into smaller semantic cues. A claim-neutral hook/lifestyle/CTA must also have an explicitly approved semantic tag in both cue and shot metadata; never assign false product claims merely to pass.

EDL: same market/narration/script/audio identifiers, `runtime`, and `segments: [{shot_id,in,out,timeline_start,timeline_end,speed:1}]`. Segments are contiguous; source and output durations match. Every moment of a cue must have a shot supporting that cue's claim IDs. Bind each selected video's EDL to its own separately generated narration and measured runtime. A changed spoken hook or proof order requires regeneration of that video's complete narration. Correcting claim-equivalent picture within the same video does not require resubmitting its unchanged successful TTS job. Store `video_only_sha256` after rendering the clean picture for ending QA.

```bash
python3 scripts/validate_edl.py --edl edit/edl.json --library library.json \
  --narration edit/narration.json --script edit/narration.txt --audio edit/narration.wav
python3 scripts/score_asset_library.py library.json -o edit/library-score.json
python3 scripts/score_asset_library.py library.json --edl edit/edl.json -o edit/edit-score.json
```

Do not try to fix low library diversity by editing an EDL. Reassess available assets or seek authorization for more generation. A low selected-edit score may justify changing shots while preserving cue alignment.

## Annotation schema and rendering

`product_annotation_template.json` is only the `style` object. Wrap it in a plan with `version:2`, `market_profile_id`, `market_profile_sha256`, `locale`, `canvas`, `style`, and `annotations`. Each annotation has `id,start,end,text,claim_id,evidence,anchor,animation` and optional `accent_text,proof_moment`. Approved ledger shape: `claims: [{id,status:"confirmed",evidence:[...],approved_copy:{"ja-JP":["approved short copy"],"en-US":["approved translation"]}}]`.

Style supports card color/opacity/padding/rounded corners; text color/size/bold/outline color and width/shadow; accent; normalized safe zone; entrance `none|fade|slide-up|slide-left|scale-in` and exit `none|fade`, durations and **linear** easing. Each annotation explicitly selects its entrance animation; `style.animation.in` is the default to copy when drafting those entries. Nonlinear easing is not implemented and is rejected (the old `ease_out_cubic` declaration was misleading). No unknown options are silently ignored. Fonts come exclusively from the market, not the template. Long copy is rejected if it does not fit; explicitly shorten or line-break approved copy instead of silently shrinking it.

```bash
python3 scripts/validate_annotations.py edit/annotations.json \
  --market-profile analysis/market-profile.json --claim-ledger analysis/claim-ledger.json --duration 34.7
python3 scripts/render_annotations.py edit/annotations.json \
  --market-profile analysis/market-profile.json --claim-ledger analysis/claim-ledger.json --duration 34.7 \
  -o edit/annotations.ass
```

The runtime in commands is the measured narration-derived runtime, never a fixed target. The renderer creates separate ASS drawing and text layers, plus a hash-bound layout/font receipt. Load the exact font into the render's `fontsdir` (no system font installation necessary) and inspect FFmpeg/libass font selection and rendered samples. ASS generation alone does not prove the final text is visible. Inspect the beginning/middle/end of every animated card, including RTL shaping and safe-zone bounds.

## Omni chronological reference gate

`product-ugc-pipeline/scripts/generate_videos_lk888.py` no longer accepts the scene-anchor bypass. The storyboard must have current provenance (image hash, provider, actual prompt and reference hashes), current identity/keyframes QC, and an actual visual inspection saved as `qc/storyboards/<storyboard-stem>.json`:

`{status:"pass",sha256:<image hash>,timeline_sha256:<routed storyboard hash>,panel_count:<observed count >=2>,chronological:true,singleton_per_panel:true,reviewer:<engine/person>,evidence:[<panel-specific observations>]}`.

Compute timeline SHA256 from UTF-8 `json.dumps(variant["storyboard_10s"],ensure_ascii=False,sort_keys=True,separators=(",",":"))`. Inspect the real image before writing the report. A renamed endpoint, a changed timeline or missing/unknown QC blocks paid submission. Do not regenerate paid media just to migrate metadata: first inspect existing references; reuse only if they genuinely meet the contract.

## Audio task durability

`UpdramaClient(journal=<per-logical-task path>)` is required before `create_*`. CLI needs `--journal`. It writes and fsyncs an exclusive intent **before POST**, immediately persists the returned task ID, and reuses that receipt for the same request. A pending/failed/uncertain create never auto-creates a replacement. Changed requests require a separate authorized operation. Do not delete a journal to retry.

Use `--resume --journal <existing>` to retrieve the receipt without POST, then `--wait --output <file>` to poll/download. Provider/prompt positional arguments are still required by the CLI but ignored during resume; the journal's request is authoritative. GET status errors retry within a bounded timeout; local timeout is not provider failure. Both top-level and `data`-wrapped statuses are accepted, but only `is_final=true,state=success` may be downloaded. If creation ended ambiguously without a task ID, reconcile in the provider account before proceeding; do not infer failure from a dropped connection. The client is not a substitute for paid authorization.

## Fail-closed release QA

Save **post-processing timeline stems**: narration with actual delay/gain and BGM with actual trim/loop/duck/fades, both covering the full output duration. Final master is their sum; if using a nonlinear master limiter, render its contribution into stems or use a documented mix method that can be reconstructed. `qa_unified_audio.py` verifies decoded final PCM against the sum (lossy SNR tolerance), not unprocessed source volumes. It measures EBU R128 over speech-active phrases, checks final audio/video stream starts/ends and BGM timeline coverage, and fails if speech/BGM gap is outside 8–12 dB.

Final ASR JSON: `{media_sha256:<final MP4 hash>,language:<profile language>,engine:<actual engine>,words:[{text,start,end}]}`. Run ASR on the actual final soundtrack. Full normalized text must match the approved script in order, including repetitions and last word; differences require genuine review/retranscription or a fix, not a fabricated transcript. Text equality does not prove an intact final phoneme.

Perceptual review JSON binds `video_sha256`, `bgm_stem_sha256`, `market_profile_sha256`, `reviewer` and `evidence` (observations/timecodes). Required `checks` values are `pass|fail`: `sentence_tail_audible`, `no_unintended_repeated_speech`, `bgm_no_seams_vocals_hum`, `bgm_rights`, `no_pops_clipping`, `annotations_visible_readable`, `market_consistency`, `visual_claim_support`, `narration_cue_sync`, `product_unobscured`, `dynamic_ending`, `subtitles_correct_or_not_requested`. Actual listening/vision or a capable review engine must supply these, not the numerical heuristic scripts.

```bash
python3 scripts/qa_unified_audio.py edit/final.mp4 --narration edit/narration.wav \
 --narration-offset 0.4 --script edit/narration.txt --video-only edit/picture.mp4 \
 --narration-stem edit/voice-timeline.wav --bgm-stem edit/music-timeline.wav \
 --final-asr edit/final-asr.json --market-profile analysis/market-profile.json \
 --annotations edit/annotations.json --claim-ledger analysis/claim-ledger.json \
 --edl edit/edl.json --library library.json --narration-manifest edit/narration.json \
 --review edit/perceptual-review.json --json-out edit/qa.json
python3 scripts/score_dynamic_ending.py edit/final.mp4 --video-only edit/picture.mp4 \
 --edl edit/edl.json -o edit/ending-score.json
```

Exit 0 = all supplied required checks pass; 1 = defect; 2 = missing/error/incomplete. Never ship on exit 1/2. Missing ASR/review cannot be substituted with punctuation or a duration comparison. Ending scores use clean picture and actual last-two-second EDL ranges, not animated overlays or filename guesses; they remain heuristics requiring visual review.

Local dependencies: FFmpeg/ffprobe with libass, Pillow, fontTools, jsonschema, NumPy. `check_env.py --market-profile <profile>` checks readiness; do not install or spend without appropriate scope. Regression tests are offline and write only temporary fixtures, not product outputs.
