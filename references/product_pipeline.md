# Product-link entry workflow

Use this reference when the request begins with an ecommerce URL rather than an existing clip library.

## Route

1. Ask for the target country/market if it is not already stated.
2. Echo and confirm the read-only collection route: ChronoForge → product-ugc-pipeline → ego-browser. If that route was explicitly requested, do not ask again.
3. Classify the request using ChronoForge: product URL = `product_video`; URL plus uploaded/local footage = `hybrid`.
4. For TikTok Shop, regional pages, or any page that may require cookies, use `ego-browser` first. If the page shows a login, CAPTCHA, device prompt, or region challenge, stop and ask the user to take over.
5. Treat product-ugc-pipeline as the only production generation path: use its complete extraction, built-in vision, product brief, taxonomy, identity lock, usage ledger, prompt generation, keyframes, paid video adapters, parallel-batch state tracking, and L1/L2 QC. Do not substitute an ad-hoc model/API workflow.

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
- unified audio policy: all source clips muted, one complete Japanese GEM-3.1-TTS narration, one BGM bed;
- whether the user authorizes paid generation now.

The user may pre-authorize a model and batch size in the same request; otherwise pause at this gate. Keep the reference-pack lock and paid-create confirmation separate.

## Asset-library gate

After video QC, write an append-only library manifest. Group clips by one selling point and retain 3 or more visual variants when budget allows. Keep accepted, reserve, rejected, and superseded clips distinguishable. Record hashes/provenance and never replace source evidence with generated images.

## Handoff into montage

Only accepted generated containers enter the edit timeline. The montage planner receives the library manifest plus the final narration cue ranges; it does not use source-generated dialogue as the editorial script. The final package must include the product evidence, claim ledger, asset library, EDL/timeline, unified audio assets, product annotations (and subtitles only when explicitly requested), render receipt, and QA report.

## Generation ownership

ChronoForge owns route selection, immutable run/version contracts, reference-lock and paid-delivery gates. `product-ugc-pipeline` owns every product-generation decision and execution: model capability review, prompt/risk routing, Image2 references, Omni/VEO submission, task polling, parallel workers, resume state, retry policy, and L1/L2 video QC. This Skill may orchestrate those stages but must not create a second generation implementation.

The market profile is a required input to that ownership boundary: product-ugc-pipeline generates the visuals and any native dialogue for the locked country/region, while the final montage uses only the same locale's narration, overlays and subtitles.
