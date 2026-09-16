# AI 配乐与配音：业界方案研究（2026-09）

这份参考把“视频生成器自带声音”和“广告成片的可控音频”分开。结论不是选一个万能模型，而是采用**画面先行、音频分轨、最后统一混音**的两阶段架构。

## 结论先行

对于产品 UGC 投放，默认不要把最终配乐烘进视频生成阶段。让 `video-use` 只做画面理解、卖点匹配和 EDL；随后单独生成一条完整日语旁白和一条无 vocals 的音乐轨，再由 Kinocut/FFmpeg 做 sidechain ducking、响度归一化和 QA。这样才能在不重剪画面的情况下替换音色、配乐、音量和版本风格。Omni-Flash 可以额外跑一轮“原生配乐参考”：若它输出的是贯穿全片、无对白/人声、无嗡声且通过版权和响度检查的音乐，可作为候选 BGM 与 Suno/Lyria 盲听比较；不要因为它随视频生成就自动放行。

视频模型的原生音频适合预览、对白或音效驱动的创意探索；正式广告仍应把它视为临时音轨：保留画面参考，最终导出前静音并重配。以 Veo 3.1 为例，官方 API 将原生音频列为 always-on，并支持对白、SFX、环境声提示，但输出不是一个可独立替换的音乐 stem。这是“生成带配乐”适合 demo、不适合作为最终投放母带的原因。[Veo 3.1 API](https://ai.google.dev/gemini-api/docs/veo)

## 推荐的生产架构

```text
素材/生成片段（无对白、无音乐，最多保留临时环境声）
        ↓
video-use：画面理解 → 卖点/镜头排名 → 多版本 EDL
        ↓
完整日语脚本 → GEM-3.1-TTS（单一音色、完整音轨）
        ↓
粗剪时长/节拍分析 → 生成 2–4 条无 vocals BGM 候选
        ↓
音乐候选池评分（音乐性、变化、场景贴合、无嗡声、版权）
        ↓
Kinocut：视频 + 旁白 + 选定 BGM → sidechain ducking → loudness/黑帧/同步 QA
```

关键点：BGM 候选应在粗剪画面和旁白已经确定后生成或筛选；不要先固定 30 秒，也不要为每个镜头切一段独立配乐。运行时由旁白真实时长加 headroom/tail 推导，音乐只负责适配该时长。

## 模型与工具选型

| 目标 | 首选 | 适用理由 | 主要限制 |
|---|---|---|---|
| 高质量、无 vocals 的广告底乐 | **Lyria 3.5** 或 Suno v4.5 instrumental | Lyria 支持文本/图片条件、乐器/速度/结构提示及“Instrumental only, no vocals”；Suno 适合快速做多候选 | 需要正式 provider adapter、版权/商用条款必须单独记录；候选仍要听感 QA。 [Lyria](https://ai.google.dev/gemini-api/docs/music-generation) |
| 随画面/节奏自适应 | **Lyria RealTime**；或 Timbre/sonique 一类 video-to-music 编排 | 可用 WebSocket 实时 steer；开源参考展示了按场景情绪、节奏、转场生成并用短段 crossfade | 工程复杂，实时结果需冻结为可复现的 stems/segments；不应直接把实时流当最终母带。 [Lyria RealTime](https://ai.google.dev/gemini-api/docs/realtime-music-generation) |
| 本机/私有化短动机、转场、环境声 | **Stable Audio Open**、MusicGen、ACE-Step | 可自托管，适合 riff、鼓点、短 cue、SFX 和风格变体；可降低 API 成本 | Stable Audio Open 主要生成最长约 47 秒的 samples/SFX，不以长篇连贯歌曲为目标；MusicGen 官方建议中型/旋律模型需约 16GB VRAM。 [Stable Audio Open](https://stability.ai/news-updates/introducing-stable-audio-open) · [MusicGen](https://github.com/facebookresearch/audiocraft/blob/main/docs/MUSICGEN.md) |
| 版权稳定的兜底 | 经过授权的 stock/library + AI 检索/beat 对齐 | 商用风险和音乐性通常比弱生成模型更可控；可按 mood、BPM、时长筛选 | 需核对地域、广告投放和平台许可；不是“零成本 AI 生成”。 |
| 日语旁白 | **GEM-3.1-TTS**（当前默认） | 已接入 updrama，支持单一完整音轨和多语言 | 先做 2–3 个音色 audition；用自然语言指定年龄、语气、停顿、速度和日语发音，避免播音腔。 |
| 旁白备选 | Gemini-TTS、ElevenLabs、Cartesia Sonic | 都支持风格/速度/情绪控制；适合在 GEM 音色仍有明显 AI 感时做 A/B | 需新增 adapter、价格和商用许可核验；过度情绪控制可能产生伪影。 [Gemini-TTS](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts) · [ElevenLabs Voice Design](https://elevenlabs.io/docs/eleven-creative/voices/voice-design) · [Cartesia controls](https://docs.cartesia.ai/ja-jp/build-with-cartesia/capability-guides/control-speed-and-emotion) |

## 为什么不把最终配乐直接放进视频生成

1. **不可拆分**：原生音频往往与画面绑定，旁白、环境声、音乐不能分别重混。
2. **不可分支**：同一视觉 EDL 难以快速测试不同 BGM、音色和语言市场。
3. **时长不稳定**：生成器的音频结尾不一定与旁白句尾、CTA 或动态结尾对齐。
4. **质量难统一**：跨片段会出现响度跳变、loop seam、突发人声或持续单频嗡声。

如果必须用视频模型原生音频，提示词使用 `no dialogue, no vocals, no music; subtle diegetic ambience only`，并把该音频当临时参考；交付前仍执行 `-an`/静音和统一重配。原生音频只在音效本身是卖点（例如开合、喷雾、点击声）时保留经过 QA 的 stem。

## 配乐提示词与候选池

每条候选至少包含：`用途/市场 + 情绪 + 速度/BPM + 主乐器 + 结构变化 + 无人声约束 + 结尾方式`。示例：

> `Japanese lifestyle UGC product bed, warm acoustic guitar, soft marimba and brushed percussion, 92 BPM, gentle lift at the product reveal, sparse under voiceover, evolving arrangement, natural resolved ending, instrumental only, no vocals, no chanting, no lyrics, no dramatic drop, no drone, no hum.`

同一粗剪建议生成 2–4 条风格相近但编曲不同的候选（例如 acoustic、lo-fi electronic、light city-pop instrumental），再按镜头情绪和旁白密度分配。评分维度：

- 音乐性/和声变化，而非持续单音或循环噪声；
- 与镜头节奏、转场和产品类别的贴合；
- 旁白频段遮挡、sidechain 后的清晰度；
- 前后 1 秒的可用 head/tail、无明显 loop seam；
- 无人声、无歌词、无版权/模型水印风险；
- 在多个版本中的多样性，避免同一首机械复用。

任一候选出现持续嗡声、单频 drone、突发人声、明显拼接或 speech masking，就标记为 failed，不要靠再降音量掩盖。

## 混音与 QA 建议

- 旁白是主轨；BGM 使用 sidechain/compressor 随旁白自动下压，而非只写死一个 gain。
- 目标仍为 BGM 比旁白低约 **8–12 dB**，并在最终时间线上测 integrated/short-term loudness；同时检查 speech masking、峰值和尾部噪声。
- 统一目标响度（例如项目约束的 LUFS/true peak）后再导出，不把平台二次响度归一化当作修复手段。
- 自动检查：句尾完整性、重复句、产品标注覆盖、旁白/BGM 相对响度、源音频残留、黑帧、A/V 时长与同步、波形爆音、静止结尾。
- BGM 轨道保持独立 provenance：模型、任务 ID、prompt、候选评分、裁切/loop/crossfade、许可证和最终增益都写入 manifest。

## 对本 skill 的落地决策

当前默认保持 **GEM-3.1-TTS + Suno instrumental candidate pool**，但 Suno 不再是“唯一正确答案”。下一步应补一个 `score_audio_candidate` 阶段：先读取视频 EDL、旁白 timing 和 mood tags，再并发请求/检索有限数量的候选，自动打分后交给用户选择风格或接受默认最优项。后续可增加 Lyria 3.5 adapter；Lyria RealTime 作为实验性“自适应配乐”后端；Stable Audio Open/MusicGen/ACE-Step 作为本地短 cue/fallback，而不是强行承担整条长 BGM。

相关开源参考：

- [timbre](https://github.com/saat-sy/timbre)：多模态视频情绪/节奏分析、场景分段、Lyria soundtrack、短段 crossfade；
- [sonique](https://github.com/zxxwxyyy/sonique)：Video-LLaMA → 音乐标签 → Stable Audio Tools 的 video-to-music 研究实现；
- [motif](https://github.com/wuxinkerrqq/motif)：节拍分析 → 场景理解 → shot planning → transition rendering；
- [YouAndOrchestra](https://github.com/shibuiwilliam/YouAndOrchestra)：多 agent 作曲与 stems/质量评估参考。

这些项目适合作为编排和评分的设计参考，不应绕过本 skill 的市场、版权、付费确认和发布 QA。
