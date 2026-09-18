# Demand-led production and calibrated budgeting

Default target: 20 distinct-opening ads. Explicit user count overrides it. This is not spending authorization or a guarantee of ad-platform approval.

## Decision loop

Evidence/claims → N creative briefs and script drafts → proof/role/seconds demand → compatible 10s source designs → authorized pilot → observed QC/yield → constrained allocation → targeted supplements → independent full TTS → measured-runtime allocation → render/release → forecast/outcome audit.

AI owns creative interpretation and actual media review; deterministic helpers check structure and resource constraints. No helper invents claims, proves perceptual quality, or creates paid media on import.

### 1. Write demand before deciding source count

Use one brief per requested video. Vary the buyer problem, main claim, scenario, proof treatment and supporting claim subset; do not merely permute all claims. Freeze the market and evidence. Choose a deliberate reuse cap and overlap limit for this campaign rather than treating three uses as a measured universal rule.

Write `creative-demand.json`, schema at [creative_demand.schema.json](creative_demand.schema.json):

- Top level: `schema_version:1`, `target_videos` (default 20), market ID/hash, `selling_points:[{id,status:"confirmed",evidence:[...]}]`, `constraints:{max_shot_uses,max_pairwise_overlap}`, `variants`.
- Each variant: unique `variant_id`, `audience`, `scenario`, `creative_angle`, `main_claim_id`, unique complete `script_draft`, `runtime_basis:"estimated"|"measured"`, `runtime_seconds`, ordered `slots`.
- Each slot: unique-in-variant `slot_id`, confirmed `claim_id`, `proof_key`, `role:"hook"|"proof"|"transition"|"ending"`, `seconds`, `calibration_group`.
- The first slot is the sole hook (at least 3s); the last is a separate dynamic ending. All slot seconds sum to runtime, including headroom and speech tail. One continuous slot cannot exceed the 10s source length; split a longer proof into meaningful separately matched slots, not fabricated claims.
- `proof_key` names an actual visual need, e.g. `water-beads-macro`, not just “waterproof.” `calibration_group` identifies comparable production difficulty and beat layout, e.g. `ready-state-macro-v2`.
- A variant may use only some confirmed claims. Neutral lifestyle/transition material needs an explicitly evidence-supported semantic tag; do not falsely label it as technical proof.
- Estimated seconds are provisional per-script estimates, not fixed ad lengths. After each independent full TTS track, replace estimates with measured cue/slot durations and rerun allocation.

Changing labels is not a new creative. The validator rejects exact duplicate briefs/scripts; actual concept quality and near-duplicate copy still need review.

### 2. Design source candidates, not an automatic N × coefficient budget

```bash
python3 scripts/plan_source_budget.py edit/creative-demand.json -o edit/demand-report.json
```

Without source candidates the report lists demand and says `needs_source_design`, with no fabricated source count.

Author `source-container-plan.json` with market ID/hash, target, allowed model, `reference_mode:"omni-reference"`, confirmed `selling_points`, and `containers`. Each 10s container has canonical positive `variant_id`, unique `container_id`/`creative_slot_id`, `claim_ids`, `calibration_group`, five creative axes (`scene_geometry,camera_distance,camera_motion,creator_staging,proof_composition`) and contiguous beats covering 0–10s.

Every beat has:
`start,end,claim_id,proof_moment,creative_slot_id,proof_key,roles`.
A hook role also needs `payoff_after` in (0,3] relative to THAT beat and at least 3s of footage. An ending role needs a concrete `dynamic_action`. The container's legacy first-beat `hook_claim_id/hook_payoff_by` may be omitted for supporting-only sources.

One complex claim may occupy a whole container even when other claims exist. Several compatible simple proofs may share one source. Interior beats can supply independent hooks. Twenty openings do not imply twenty source files. Generation must still be 10s Omni all-purpose references, never Veo, first/last frames or page-image animation.

```bash
python3 scripts/plan_source_budget.py edit/creative-demand.json \
  --matrix edit/source-container-plan.json -o edit/source-budget.json
```

The planner tries assignments that reuse already selected source containers first. It reports the selected candidate IDs and a feasible source count, **not a globally minimum count**. Unselected candidates need not be generated. Refine the candidate designs and compare feasible solutions when budget reduction matters; there is no hidden optimality claim or newly installed solver/model.

The submit matrix is the chosen pilot/production/supplement subset. Keep a hash-bound full candidate matrix and budget report for audit. Bind submit-matrix `demand_sha256` to current demand; bind canonical prompt batch `montage_matrix_sha256` to the submit matrix, and each routed variant's `montage_plan` to its exact container. Preserve risk routing, chronological storyboards, identity/reference QC and clean-footage prompts.

```bash
python3 scripts/generate_montage_sources.py /absolute/run/01-product \
  --demand edit/creative-demand.json --matrix edit/submission-matrix.json \
  --prompts /absolute/run/01-product/ugc_prompts.json
# Dry-run by default. Only with real authorization add --execute --authorized.
```

A pilot/supplement need not cover all campaign claims or include N containers. Source selection is authorized explicitly; the wrapper does not treat the budget report as authority to charge.

### 3. Measure a representative pilot and retain all outcomes

With no comparable history, report `pilot_required`, unknown total count, and relevant calibration groups. `pilot_candidates` gives one possible source design per unmeasured/zero-success group, NOT a statistically adequate sample size. Select an authorized representative pilot across proof difficulty, action and layout; its size depends on coverage, observed uncertainty and budget. Do not extrapolate complex-action yield from easy B-roll.

Retain every submitted task, including failed generations and visually rejected outputs. One completed generation task is one statistical trial; three beats from one clip are not three independent trials.

History file:
```json
{"trials":[
  {"task_id":"actual-task-id",
   "context":{"model":"omni-flash","reference_mode":"omni-reference","category":"actual-category","prompt_version":"v2","market_profile_sha256":"actual-profile-hash"},
   "review_file":"qc/task-outcome.json","review_sha256":"actual-review-hash"}
]}
```

The hash-bound task outcome contains:
`task_id, reviewer, evidence, calibration_group, usable (boolean), usable_seconds (0..10), independent_hooks (0..3)`.
Define `usable` before the pilot: the template supplied ALL intended required proof/role/duration slots at QC quality. Partial successes remain false here but contribute measured usable seconds/hooks and accepted library ranges. Evidence includes actual receipt/source hashes, observed ranges, failure reasons and review observations. Never fabricate a passing review.

The source matrix's `calibration_context` has the same five fields as history. Exact context matches only; use groups specific enough to avoid mixing unrelated beat layouts and difficulty. Duplicate task IDs and stale review hashes fail. Do not combine changed model/prompt/market conditions silently.

```bash
python3 scripts/plan_source_budget.py edit/creative-demand.json \
  --matrix edit/source-candidates.json --library asset_library/library_manifest.json \
  --history edit/generation-history.json -o edit/revised-budget.json
```

For each group the report shows task sample size, usable-template rate, 95% Wilson interval, mean usable seconds and independent hooks. A point scenario divides required NEW containers by observed rate; a conservative sensitivity scenario uses its lower Wilson endpoint. It does NOT mean a 95% probability of delivering the batch. Independence/comparability are assumptions; shared references, correlated failures and untested layouts can invalidate extrapolation. Small samples remain visibly uncertain. Zero-success or missing groups produce no numeric total and require diagnosis/pilot redesign, not an infinite automatic retry budget.

Observed accepted footage is allocated first. A feasible existing library returns zero NEW source requests. Otherwise observed and planned sources are solved together; only selected NEW containers enter generation scenarios.

### 4. Admit real footage and verify the whole campaign

Accepted library sources still require canonical Omni/10s/reference provenance, provider task identity, current hashes/reference chain and real decoded video duration. Page photos, storyboard grids and animated still substitutes cannot enter the timeline.

Each accepted range adds `proof_keys`, `roles`, `calibration_group`, `hook_eligible` and `dynamic_ending` to the existing source/claim/observed-range metadata. These labels require actual review. Preserve range-bound `qc.generated_motion/reviewer/evidence` and visual clustering. Planned slot IDs are not observed clusters.

```bash
python3 scripts/plan_variant_batch.py asset_library/library_manifest.json \
  --demand edit/creative-demand.json --include-reserve -o edit/variant_batch_plan.json
```

The dependency-free finite-domain search checks:
- each requested slot's claim, proof key, role and continuous seconds;
- distinct opening clusters and non-overlapping hook ranges;
- no repeated/overlapping footage within a video;
- explicit global cluster reuse cap;
- pairwise shared picture seconds divided by the shorter runtime, bounded by the configured overlap limit;
- a reviewed dynamic ending.

Repeated appearances of the same visual cluster are conservatively counted as shared picture even when trims differ. Source overlap is also counted. Source choices are bound to fixed observed range starts; author additional legitimately reviewed boundaries if needed, never call them new visuals merely to evade clustering.

Statuses:
- **FEASIBLE**: full assignment witness, not maximum capacity, optimal cost or release approval.
- **INFEASIBLE**: empty domains or exhaustive search disproved feasibility for this supplied demand/shot set.
- **UNKNOWN**: node/time limit before resolution; inspect/expand search or refine domains before proposing more generation.

Defaults: 20,000 nodes / 5 seconds per solve, adjustable through CLI. The legacy `--explore` permutation/greedy search is retained for non-production ideation only and cannot justify spending. No arbitrary “found count” is a proven capacity ceiling.

### 5. Supplement only diagnosed gaps and bind final audio

Empty-domain deficits identify variant/slot, claim, proof key, role and continuous seconds. If individual matches exist but joint assignment fails, report the reuse/opening/overlap conflict; do not fabricate an exact minimum shortage. Ask the AI to propose specific new proof treatments, rerun allocation and compare the resulting feasible set. UNKNOWN is not a generation trigger.

Each variant receives its own complete script and independent GEM/Doubao TTS job. Freeze measured slot timing after TTS and rerun allocation. BGM may be selectively shared. If speech outgrows available proof, supplement appropriate ranges or rewrite and regenerate that variant's complete narration; no stretch/loop/freeze padding.

Batch manifest:
`{target_videos,variants:[{variant_id,edl,narration,script,audio,journal}]}`.
Narration additionally binds `task_id`, exact submitted `tts_prompt_sha256`, script/audio hashes, market hash and timed cues. Preserve successful journals.

```bash
python3 scripts/validate_batch.py edit/batch.json --demand edit/creative-demand-measured.json \
  --library asset_library/library_manifest.json -o edit/batch-validation.json
```

The release gate verifies actual EDL slot order/duration/proof/roles/reuse/overlap against MEASURED demand, distinct scripts/audio/tasks and opening footage. Run full per-video QA plus contact-sheet AND playback comparison of all rendered first 3s. A budget/assignment pass alone never authorizes delivery.

### 6. Backtest forecasts, not just code

Freeze each pre-generation budget report and hash. After a completed run/round, record all actual NEW generation attempts since that forecast, delivered videos, and supporting receipts/QA evidence. Do not revise the forecast retrospectively.

```json
{"runs":[{"run_id":"actual-run-round","complete":true,
 "budget_file":"frozen-budget.json","budget_sha256":"actual-hash",
 "actual_generated_sources":0,"actual_delivered_videos":0,
 "evidence":["actual task manifest","actual delivery QA"]}]}
```

Numbers above are schema examples, not claimed measurements.

```bash
python3 scripts/audit_budget_outcomes.py edit/budget-outcomes.json -o edit/forecast-audit.json
```

The audit reports signed/absolute source-count error, delivery shortfall and mean absolute error over numeric forecasts. Unknown forecasts are not scored as zero. Include failed and over-budget runs; do not cherry-pick. These descriptive results and regression tests are not proof of predictive accuracy until evaluated prospectively across real projects.

Statistical method reference: [NIST proportion intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). The local search implements its own bounded assignment; OR-Tools is not installed or required.
