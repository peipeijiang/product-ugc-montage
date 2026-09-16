# Unified audio contract for product ads

This workflow is visual-only at the source-clip level. Smart editing analyzes picture and selects shots; it never carries source speech, room tone, or music into the final master.

## Required order

1. Write one complete Japanese narration for the whole ad.
2. Generate one complete GEM-3.1-TTS audio file from that exact script and retain word/phrase timing.
3. Derive the runtime from the real narration duration: `narration_duration + headroom_before + clean_tail_after` (never a fixed 15/25/30-second target).
4. Build a pool of soft, instrumental BGM candidates, validate each, and assign a passing candidate to each variant; fit/loop each to that derived runtime (default candidate: Suno v4.5 instrumental).
5. Mute or strip every source audio stream before segment extraction/concat.
6. Mix narration and BGM only after the video-only base is assembled.

## Mix target

Measure narration and each assigned BGM on the final timeline using integrated or short-term loudness. Keep BGM approximately **8–12 dB below narration**, with gentle head/tail fades. A raw volume multiplier alone is not sufficient evidence of compliance. Avoid continuous sine tones, single-frequency drones, audible loop seams, vocals, dramatic drops, or unfiltered hums; use a musical/chordal, filtered texture or an approved/licensed instrumental bed. If the selected model repeatedly fails these checks, switch provider or use a licensed/original track and record the failed candidate. Store the measured values, candidate ID, provider, and method in the QA report.

## Required automated checks

- Compare final video duration with the narration file and verify the narration has a clean tail; reject clipped final phonemes or incomplete sentence endings.
- Run final-audio ASR and compare the transcript to the authored Japanese script; flag missing, duplicated, or reordered sentences.
- Verify every product annotation (and optional subtitle, if explicitly requested) has coverage on the output timeline, does not overlap an excluded UI safe zone, and is readable in sampled frames.
- Verify no source audio stream survives the video-only concat and that every final master contains exactly the intended narration plus one assigned BGM bed.
- Measure narration/BGM relative loudness and reject values outside the 8–12 dB target or speech masking at proof moments.
- Run black-frame detection, duration checks, and audio/video sync checks on the final MP4.
- Sample all cut boundaries plus the first/last two seconds for flashes, pops, frozen tails, hidden overlays, and dynamic-ending quality.

Source ASR is diagnostic only. It may help describe a shot, but it must never be used as a reason to preserve native source audio. If a check fails, revise the script, EDL, mix, or annotation plan and re-render; do not silently trim away a failed narration tail.
