# Demand-led batches: default 20

This contract supersedes the old 3/6/12 guidance. Twenty is the requested production target, not permission to spend or a guarantee of TikTok approval. An explicit user count wins. All model creation is subject to the existing paid-generation gate.

## Before generating anything

1. Inspect the evidence ledger. Select the genuinely relevant, confirmed selling points for this batch; keep excluded/uncertain points recorded. Do not invent claims to fill a matrix. For many claims, split into coherent campaign groups; each group's library `selling_points` is exactly the set the variant planner should cover, not the entire product taxonomy.
2. Run the offline budgeter on that selected ledger:

```bash
python3 scripts/plan_source_budget.py analysis/selected-claim-ledger.json \
  --target 20 -o edit/source-budget.json
```

The conservative estimate reserves **one independent opener per source container**, plus 25% rejection reserve by default. With three confirmed compatible claims and target 20, this means 20 base + 5 reserve = **25 proposed 10s requests**, with up to 75 planned proof ranges. This is an explicit planning assumption, not a mathematical minimum, a fixed universal source count, or a promise that all footage will pass. Change the reserve ratio to match approved budget/risk. Other claim counts require sufficient coverage; measured narration runtime, failed generation, overlap limits and rejected motion can increase the actual need. Interior beats may yield extra hooks after QC and reduce supplemental generation, not retroactively justify fake capacity.
For P selected claims and N requested ads, the budgeter's base count is `max(N, P, ceil(P × ceil(N / 3) / min(3, P)))`: enough opening slots and proof coverage assuming at most three uses per proof for budgeting. Add the configured rejection reserve afterward. It reports per-claim proof counts; actual reuse/overlap and duration are validated later. All selected claims are covered by each planner candidate; select a coherent smaller claim group when the full product ledger would make the ad too long.

3. Author `source-container-plan.json`: top-level market ID/hash, `target_videos`, `model`, `reference_mode:"omni-reference"`, `selling_points:[{id,status:"confirmed",evidence:[...]}]`, `containers`. Each container has `variant_id` (positive canonical pipeline ID), `container_id`, `duration:10`, claim IDs, hook claim/payoff, creative slot, all five creative axes, and contiguous beats with claim/proof. Use 0–3 / 3–6 / 6–10s as one example, not a mandatory pacing template. Only one confirmed claim permits a one-claim container with distinct proof treatments.
4. Design actual differences in scene, camera/action and proof composition. Changing IDs is not creative variation. Balance hook claims. The first beat needs at least 3s of independently intelligible proof. Save planned beats now and actual observed shot ranges after generation; never copy ideal timestamps into QC without viewing.
5. Validate the matrix, then bind it to canonical routed prompts: top-level `montage_matrix_sha256`, each variant's exact container object in `montage_plan`, and risk-routed `storyboard_10s`. Preserve canonical identity/usage locks and reference QC. Strip inherited narration/overlay instructions. Submit the chronological storyboard plus identity grid as all-purpose references, not endpoint frames.

```bash
python3 scripts/validate_generation_matrix.py edit/source-container-plan.json
python3 scripts/generate_montage_sources.py /absolute/run/01-product \
  --matrix edit/source-container-plan.json --prompts /absolute/run/01-product/ugc_prompts.json
# Default is dry-run. Only with actual paid authorization, add --execute --authorized.
```

The wrapper fixes duration=10, reference mode=omni-reference, audio-style=none, clean 9:16 source footage and one create attempt (ambiguous submission must be reconciled, not blindly charged again). It accepts only `omni-flash` and `omni-flash-10s` (the latter maps to canonical `omni_flash-10s`). It offers no Veo, first-last, unverified-reference or raw argument passthrough. Do not call the general-purpose generator's default command directly for montage work. The wrapper does not implement a competing video provider.

## Source admission and reusable records

Product-page images and generated reference sheets stay outside the footage library. `accepted_shots()` requires the canonical sibling `clip.provenance.json`, current clip hash, allowed model, 10s request, Omni reference mode, successful task identity, no QC override, and current local reference hashes. Set each shot's absolute `generation_root` to the canonical product directory. FFprobe checks actual frames and source duration (~10s, tolerance 0.12s for container/frame rounding). Re-encoded derivatives are not substitutes for the canonical generated source; keep the original and point shot ranges to it.

Each accepted shot records source/task provenance, observed `in/out`, `claim_ids`, evidence, angle/action, proof moment, market, unique creative slot, visual fingerprint/cluster and `hook_eligible`. Set `hook_eligible:true` only after verifying an independent, understandable 3s opening. Current range-bound `qc` must include `generated_motion:true`, `reviewer`, and nonempty visual `evidence`. A pan over a web photo, static grid or relabeled still is rejected even if it has video encoding. No script can authenticate fabricated review records; inspect the actual media and never manufacture passing evidence. Missing legacy provenance must be reconciled from existing real receipts, or excluded, never forged.

## After generation

Run visual QC and fingerprint clustering, then `plan_variant_batch.py`. Default target/review cap is 20; pass both `--selected-n 30 --review-cap 30` for an explicitly requested 30. Reports retain the requested target and found candidate shortfall, returning exit 2 on insufficiency. Distinct hook visual clusters and non-overlapping opening ranges are mandatory, not just score preferences. Selling-point order varies when multiple points exist; do not claim that 20 permutations alone create 20 different videos. Rendered opening comparison is still required because hashing cannot reliably understand scene semantics.

Write N complete scripts matched to the N picture plans. Generate N separate full GEM/Doubao TTS jobs. One consistent voice within each video; the same approved voice preset across videos is fine. Unique files/IDs are not enough: batch validation rejects identical script contents, audio hashes or task IDs. Changing a narration requires regenerating the complete track for that variant. Each final runtime follows its own returned audio. BGM may be selectively shared from the passing Suno/native-reference/licensed-file pool; the same music does not excuse the same hook or narration.

Batch manifest (paths relative to the batch file):

```json
{"target_videos":20,"variants":[
  {"variant_id":"v01","edl":"v01/edl.json","narration":"v01/narration.json",
   "script":"v01/narration.txt","audio":"v01/narration.wav","journal":"v01/tts-task.json"}
]}
```

The array above is abbreviated; a real target-20 batch requires 20 entries. Narration metadata additionally binds `task_id` and `tts_prompt_sha256` (SHA256 of exact UTF-8 submitted prompt, including delivery instructions). Keep original provider journals with successful terminal status. Final ASR must still verify spoken script, since prompt hash alone is not evidence of correct speech.

```bash
python3 scripts/validate_batch.py edit/batch.json --library asset_library/library_manifest.json \
  -o edit/batch-validation.json
```

Run this batch gate alongside per-video `validate_edl.py` and full release QA. Compare every rendered first 3s by contact sheet AND playback: new captions, crops, music or slight trim shifts do not make repeated footage unique. Save review evidence bound to current render hashes. No batch is deliverable solely because its plan passed. Report actual passing count and concrete rejected/missing assets; do not quietly deliver fewer than requested or claim a guaranteed ad-platform approval.
