# Audio provider contract

Read this reference when the run will generate new narration or BGM. It records the preferred provider route supplied by the user; provider payloads remain separate from the product-generation pipeline.

## GEM-3.1-TTS (default narration)

- Provider: updrama, `BASE_URL=https://api.lk888.ai`.
- Create: `POST /v1/media/generate` with `{ "model":"gem-3.1-tts", "prompt": <target-language script>, "params": { "voice_id": <provider-supported voice> } }`.
- Poll: `GET /v1/media/status?task_id=<id>` every 3–5 seconds until `is_final === true`; accept only `state === "success"`, then fetch `result_url`.
- Use a single Japanese-market voice for the whole run. Query the provider's current voice/model catalog; do not assume the `gem-2.5-tts` voice-list endpoint or a hard-coded voice is valid for GEM-3.1-TTS.
- Prefer presets whose catalog description suggests relaxed, smooth, or conversational delivery for lifestyle UGC; avoid an overly excited/company-announcer preset when the brief is meant to sound human. Treat this as a candidate choice, not a guarantee: listen to a short sample or generated track and re-run runtime/QA after any voice change.
- Save task ID, voice ID, model, prompt hash, result URL, duration, and provider cost in the run manifest. Keep the script and audio as separate artifacts.
- Run word-level ASR on the returned audio, check the final word and clean tail, and never trim a sentence to force a runtime.

## Suno v4.5 (default BGM candidate)

- Provider: updrama, `BASE_URL=https://api.lk888.ai`.
- Create: `POST /v1/media/generate` with `model:"suno-v4.5"`, a style prompt, and `params.make_instrumental:"instrumental"`; leave lyrics empty for a no-vocal bed.
- Prefer a short instrumental brief such as: `soft Japanese outdoor camping ambience, warm acoustic guitar and gentle pads, no vocals, no dramatic drops, evolving arrangement, natural ending, seamless-feeling bed`; do not request a fixed 30-second duration when the runtime is narration-derived.
- Poll with the same `is_final`/`state` rules. Record task ID, model, prompt, result URL, duration, license/provenance, and any loop/trim operation.
- Before delivery, fit/loop the BGM to the narration-derived runtime, duck it **8–12 dB below narration** on the final timeline, add head/tail fades, and verify that no vocal or lyric content remains. Do not use a continuous sine tone, single-frequency drone, or unfiltered hum as a creative fallback; those are test signals only.
- For batches, generate or select a candidate pool and assign tracks by mood/variant. Suno remains the default candidate, not a mandatory provider: switch when repeated outputs fail hum, no-vocal, seam, dynamic-range, or musicality checks. Record failed candidates and the replacement provider/track in the manifest.

## Authorization boundary

These are paid or potentially paid calls. Before submitting either task, show the user the exact model, voice/style, estimated jobs, expected duration, and audio policy and obtain explicit confirmation. Never substitute a local TTS or procedural tone as the default without recording it as a fallback.
