# Product-link entry workflow

Use this reference when the request begins with an ecommerce URL rather than an existing clip library.

## Route

1. Ask for the target country/market if it is not already stated.
2. Echo and confirm the read-only collection route: ChronoForge → product-ugc-pipeline → ego-browser. If that route was explicitly requested, do not ask again.
3. Classify the request using ChronoForge: product URL = `product_video`; URL plus uploaded/local footage = `hybrid`.
4. For TikTok Shop, regional pages, or any page that may require cookies, use `ego-browser` first. If the page shows a login, CAPTCHA, device prompt, or region challenge, stop and ask the user to take over.
5. Treat product-ugc-pipeline as the only production generation path: use its complete extraction, built-in vision, product brief, taxonomy, identity lock, usage ledger, prompt generation, keyframes, paid video adapters, parallel-batch state tracking, and L1/L2 QC. Do not substitute an ad-hoc model/API workflow.
6. For new `omni-flash`/`omni_flash-10s` montage assets, select `omni-reference` before image generation: generate a genuine chronological storyboard from the current risk-routed script, pass storyboard QC, and submit it with the verified product identity grid. Protected routes omit the operation grid. Follow the reference and risk-record contracts in `../SKILL.md` section 2; single-frame renaming and adapter scene-anchor fallbacks do not satisfy them.

## Evidence gate

Do not write final claims or prompts until all relevant image surfaces are collected and analyzed. The manifest and image-analysis local-path sets must match exactly. Every claim used in a script, overlay, or scene must point to evidence in the brief/claim ledger.

## Market lock

After the user names the country/region, write `analysis/market-profile.json` and freeze it for the run. It must define at least `country`, `region`, `locale`, `language`, `script`, `currency`, `casting_profile`, `scene_context`, `voice_profile`, and `subtitle_style`. Pass this profile to every product-ugc-pipeline prompt and variant manifest. Generated people, wardrobe, locations, gestures, dialogue, overlays, CTA and subtitles must match it. If a video model cannot reliably render the target language, set the clip to visual-only and use target-language TTS in post; do not accept mixed-language or culturally mismatched output.

## Generation gate

Before a paid job, present:

- target market and language;
- frozen market-profile path and casting/language rules;
- selected SKU/colorway;
- confirmed selling points and rejected/uncertain claims;
- number of visual variants and expected runtime;
- selected video model and reference mode;
- unified audio policy: all source clips muted, one complete target-language GEM-3.1-TTS narration, one BGM bed;
- whether the user authorizes paid generation now.

The user may pre-authorize a model and batch size in the same request; otherwise pause at this gate. Keep the reference-pack lock and paid-create confirmation separate.

## Asset-library gate

Before generation, assign distinct creative slots so requested variants do not merely reuse the same storyboard, opening frame, composition or camera treatment. A ten-second Omni container may cover two or three compatible claims to reduce generation cost, but every claim needs a separate chronological proof beat and later a separately observed/QC'd shot range. The first beat is the chosen hook claim and must land inside three seconds. Validate the full plan with `validate_generation_matrix.py` before requesting paid storyboards/videos; its creative axes must then be passed through to the actual product-pipeline prompt batch.

After video QC, write an append-only **shot-range** library manifest. Group/query shots by `claim_ids`; retain at least three materially different visual clusters per selling point when budget allows. Run `fingerprint_shots.py` and visual review; duplicate or near-duplicate clusters cannot both remain active. Keep accepted, reserve, rejected and superseded shots distinguishable. Record source/range hashes, creative slot, visual fingerprint/cluster, provenance and range-level QC; never replace source evidence with generated images.

Only after this library is complete, run batch planning and present the TikTok recommendation. Default guidance is at least 3 distinct variants for a meaningful test, 6 as the recommended first batch when the library passes the overlap limit, and no more than 12 in one review/export round. Do not claim six are available when the low-repeat capacity is lower; report the shortfall and propose the exact additional visual clusters required.

## Handoff into montage

Only accepted generated containers enter the edit timeline. The montage planner receives the library manifest plus the final narration cue ranges; it does not use source-generated dialogue as the editorial script. The final package must include the product evidence, claim ledger, asset library, EDL/timeline, unified audio assets, product annotations (and subtitles only when explicitly requested), render receipt, and QA report.

## Generation ownership

ChronoForge owns route selection, immutable run/version contracts, reference-lock and paid-delivery gates. `product-ugc-pipeline` owns every product-generation decision and execution: model capability review, prompt/risk routing, Image2 references, Omni/VEO submission, task polling, parallel workers, resume state, retry policy, and L1/L2 video QC. This Skill may orchestrate those stages but must not create a second generation implementation.

The market profile is a required input to that ownership boundary: product-ugc-pipeline generates the visuals and any native dialogue for the locked country/region, while the final montage uses only the same locale's narration, overlays and subtitles.
