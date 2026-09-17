# AI 配乐与配音：业界方案研究（2026-09）

这份参考把“视频生成器自带声音”和“广告成片的可控音频”分开。结论不是选一个万能模型，而是采用**画面先行、音频分轨、最后统一混音**的两阶段架构。

## 当前环境能力快照（以本机检查为准）

这不是模型推荐清单，而是本仓库当前真正可执行的边界：

- 已配置的音频 provider 只有 `gem`（GEM-3.1-TTS）、`doubao`（豆包 TTS 2.0）和 `suno`（Suno v4.5），调用方式均来自 updrama；
- 已安装的 `Kinocut` 负责本地渲染、混音和 QA，不负责生成音乐；
- `audiocraft` 目前只是一个 skill 文档，不代表 MusicGen 权重或运行时已安装；当前 Python 环境没有 `audiocraft`、`torchaudio` 或 `transformers`；
- Ollama 当前只有 `bge-m3`，它是文本/向量模型，不是音乐模型；
- 工作区内 MoneyPrinterTurbo 的 MP3 是示例/素材文件，不等于已授权的广告音乐库，也不等于本地音乐生成模型；
- 因此当前**没有已下载并可直接调用的本地 AI 音乐模型**。

### 当前唯一可执行的回退判断

Suno 生成失败时，当前回退只能是**用户提供或已确认授权的本地音乐文件/素材库**，再由 Kinocut 做裁切、淡入淡出、ducking 和 QA。不能把未安装的 MusicGen、Stable Audio Open 或 ACE-Step 写成自动 fallback，也不能用测试正弦波或持续嗡声伪造音乐。

如果未来明确批准安装本地模型，再单独评估 ACE-Step；安装、checkpoint 下载、显存、速度和商用许可都要先验证，不能在本次运行中隐式完成。

## 结论先行

对于产品 UGC 投放，默认不要把最终配乐烘进视频生成阶段。让 `video-use` 只做画面理解、卖点匹配和 EDL；随后单独生成一条完整目标市场语言旁白和一条无 vocals 的音乐轨，再由 Kinocut/FFmpeg 做 sidechain ducking、响度归一化和 QA。这样才能在不重剪画面的情况下替换音色、配乐、音量和版本风格。Omni-Flash 可以额外跑一轮“原生配乐参考”：若它输出的是贯穿全片、无对白/人声、无嗡声且通过版权和响度检查的音乐，可作为候选 BGM 与 Suno/Lyria 盲听比较；不要因为它随视频生成就自动放行。

视频模型的原生音频适合预览、对白或音效驱动的创意探索；正式广告仍应把它视为临时音轨：保留画面参考，最终导出前静音并重配。以 Veo 3.1 为例，官方 API 将原生音频列为 always-on，并支持对白、SFX、环境声提示，但输出不是一个可独立替换的音乐 stem。这是“生成带配乐”适合 demo、不适合作为最终投放母带的原因。[Veo 3.1 API](https://ai.google.dev/gemini-api/docs/veo)

## 推荐的生产架构

```text
素材/生成片段（无对白、无音乐，最多保留临时环境声）
        ↓
video-use：画面理解 → 卖点/镜头排名 → 多版本 EDL
        ↓
完整目标市场语言脚本 → GEM-3.1-TTS（单一音色、完整音轨）
        ↓
粗剪时长/节拍分析 → 生成 2–4 条无 vocals BGM 候选
        ↓
音乐候选池评分（音乐性、变化、场景贴合、无嗡声、版权）
        ↓
Kinocut：视频 + 旁白 + 选定 BGM → sidechain ducking → loudness/黑帧/同步 QA
```

关键点：BGM 候选应在粗剪画面和旁白已经确定后生成或筛选；不要先固定 30 秒，也不要为每个镜头切一段独立配乐。运行时由旁白真实时长加 headroom/tail 推导，音乐只负责适配该时长。

## 模型与工具选型（仅列当前可执行链路）

| 目标 | 首选 | 适用理由 | 主要限制 |
|---|---|---|---|
| 高质量、无 vocals 的广告底乐 | **Suno v4.5 instrumental** | 当前唯一已接入的 AI 配乐 provider；可按市场、速度、乐器和结尾写候选 prompt | 仍需逐条听感、无 vocals/无嗡声、版权和响度 QA；失败时不能自动换未配置模型 |
| 旁白 | **GEM-3.1-TTS** 或 **豆包 TTS 2.0** | 两者均有正式 updrama adapter；按市场选择并 audition 女声与自然口语风格 | 需实时查询 voice catalog；当前仓库没有任何线上音色效果保证 |
| 本地/授权回退 | 用户提供或已确认授权的音乐文件 | 不需下载 AI checkpoint，可直接由 Kinocut/FFmpeg 适配时长和响度 | 必须记录许可、来源和投放地域；没有授权文件时音频链路停止 |

| 版权稳定的兜底 | 经过授权的 stock/library + AI 检索/beat 对齐 | 商用风险和音乐性通常比弱生成模型更可控；可按 mood、BPM、时长筛选 | 需核对地域、广告投放和平台许可；不是“零成本 AI 生成”。 |

其他模型或开源项目（例如 Lyria、MusicGen、ACE-Step）在这里仅作为未来独立评估方向，不是本机已安装能力，也不是自动 fallback。安装权重、依赖、显存和商业许可都必须另行批准。

## 为什么不把最终配乐直接放进视频生成

1. **不可拆分**：原生音频往往与画面绑定，旁白、环境声、音乐不能分别重混。
2. **不可分支**：同一视觉 EDL 难以快速测试不同 BGM、音色和语言市场。
3. **时长不稳定**：生成器的音频结尾不一定与旁白句尾、CTA 或动态结尾对齐。
4. **质量难统一**：跨片段会出现响度跳变、loop seam、突发人声或持续单频嗡声。

如果必须用视频模型原生音频，提示词使用 `no dialogue, no vocals, no music; subtle diegetic ambience only`，并把该音频当临时参考；交付前仍执行 `-an`/静音和统一重配。原生音频只在音效本身是卖点（例如开合、喷雾、点击声）时保留经过 QA 的 stem。

## 配乐提示词与候选池

每条候选至少包含：`用途/市场 + 情绪 + 速度/BPM + 主乐器 + 结构变化 + 无人声约束 + 结尾方式`。示例：

> 日本市场示例：`Japanese lifestyle UGC product bed, warm acoustic guitar, soft marimba and brushed percussion, 92 BPM, gentle lift at the product reveal, sparse under voiceover, evolving arrangement, natural resolved ending, instrumental only, no vocals, no chanting, no lyrics, no dramatic drop, no drone, no hum.` 其他市场必须从冻结市场配置改写文化语境，不能照搬 Japanese。

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

当前默认保持 **GEM-3.1-TTS 或豆包女声 audition + Suno instrumental candidate pool**。候选评分由听感、无 vocals/无嗡声、时长适配、响度和授权证据组成；仓库当前没有独立的 `score_audio_candidate` 可执行脚本，因此不得把该阶段描述成已自动完成。Suno 失败时，当前自动链路应停在“授权本地音乐回退”，而不是调用未安装模型。其他模型仅保留为未来经过用户批准后的独立安装/接入项目，不属于当前运行时能力。

相关开源参考：

- [timbre](https://github.com/saat-sy/timbre)：多模态视频情绪/节奏分析、场景分段、Lyria soundtrack、短段 crossfade；
- [sonique](https://github.com/zxxwxyyy/sonique)：Video-LLaMA → 音乐标签 → Stable Audio Tools 的 video-to-music 研究实现；
- [motif](https://github.com/wuxinkerrqq/motif)：节拍分析 → 场景理解 → shot planning → transition rendering；
- [YouAndOrchestra](https://github.com/shibuiwilliam/YouAndOrchestra)：多 agent 作曲与 stems/质量评估参考。

这些项目适合作为编排和评分的设计参考，不应绕过本 skill 的市场、版权、付费确认和发布 QA。
