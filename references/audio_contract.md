# Unified audio contract for product ads

This workflow is visual-only at the source-clip level. Smart editing analyzes picture and selects shots; it never carries source speech, room tone, or music into the final master.

## Required order

1. Write one complete Japanese narration for the whole ad.
2. Generate one complete GEM-3.1-TTS audio file from that exact script and retain word/phrase timing.
3. Choose one soft, instrumental BGM bed for the full runtime (default candidate: Suno v4.5 instrumental).
4. Mute or strip every source audio stream before segment extraction/concat.
5. Mix narration and BGM only after the video-only base is assembled.

## Mix target

Measure narration and BGM on the final timeline using integrated or short-term loudness. Keep BGM approximately **8–12 dB below narration**, with gentle head/tail fades. A raw volume multiplier alone is not sufficient evidence of compliance. Store the measured values and method in the QA report.

## Required automated checks

- Compare final video duration with the narration file and verify the narration has a clean tail; reject clipped final phonemes or incomplete sentence endings.
- Run final-audio ASR and compare the transcript to the authored Japanese script; flag missing, duplicated, or reordered sentences.
- Verify every product annotation (and optional subtitle, if explicitly requested) has coverage on the output timeline, does not overlap an excluded UI safe zone, and is readable in sampled frames.
- Verify no source audio stream survives the video-only concat and that the final master contains exactly the intended narration plus one BGM bed.
- Measure narration/BGM relative loudness and reject values outside the 8–12 dB target or speech masking at proof moments.
- Run black-frame detection, duration checks, and audio/video sync checks on the final MP4.
- Sample all cut boundaries plus the first/last two seconds for flashes, pops, frozen tails, hidden overlays, and dynamic-ending quality.

Source ASR is diagnostic only. It may help describe a shot, but it must never be used as a reason to preserve native source audio. If a check fails, revise the script, EDL, mix, or annotation plan and re-render; do not silently trim away a failed narration tail.
