# Product UGC Forge

中文 · [English](README.en.md)

面向 TikTok、Reels 和 Shorts 的证据驱动电商 UGC 广告 skill。它把产品证据、素材库、日语旁白、产品标注、智能剪辑和发布前质检组织成一条可复用的本地流程。

## 核心流程

```text
市场/证据锁定
  → 素材画面分析与买点选镜头
  → 写一条完整日语旁白
  → GEM-3.1-TTS 生成完整音轨
  → 所有源片音频静音
  → 一条统一轻柔 BGM（旁白下压 8–12 dB）
  → 产品标注（不是字幕）
  → 自动混剪、渲染与质检
```

默认由 AI 接管时间线。用户只需要在市场、产品声明和付费 provider 提交等高风险节点确认；AI 可以自动生成 EDL、预览、返工和最终交付。

## 工具分工

- `video-use`：只分析画面、按买点排名镜头、生成 EDL 和做视觉检查。
- [Kinocut](https://github.com/KyaniteLabs/kinocut)：优先用于本地类型化渲染、统一音频混音、preflight、receipt、黑帧和响度检查。
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)：仅参考其“脚本 → TTS → BGM → 导出”的批处理编排，不覆盖产品证据和声明规则。

## 音频规则

1. 先写完整的日语旁白，再选镜头时长。
2. 使用一个 GEM-3.1-TTS voice 生成一条完整旁白音轨。
3. 所有源片音频统一静音；源片 ASR 只用于理解画面，不进入最终混音。
4. 使用一条完整、无 vocals 的轻柔 BGM，默认候选为 Suno v4.5 instrumental。
5. 在最终时间线上测量响度，BGM 比旁白低 8–12 dB。
6. 任何 provider 都不会在没有明确付费授权时提交任务。

## 可复用资源

- [`SKILL.md`](SKILL.md)：完整工作流与决策边界。
- [`references/product_annotation.schema.json`](references/product_annotation.schema.json)：产品标注 JSON Schema。
- [`references/product_annotation_template.json`](references/product_annotation_template.json)：TikTok 风格产品标注模板。
- [`references/audio_contract.md`](references/audio_contract.md)：统一音频和质检契约。
- [`references/audio_providers.md`](references/audio_providers.md)：GEM/Suno provider 适配说明。
- [`references/tool_research.md`](references/tool_research.md)：Kinocut 与 MoneyPrinterTurbo 的研究结论。
- [`scripts/providers/updrama_client.py`](scripts/providers/updrama_client.py)：GEM-3.1-TTS / Suno adapter。
- [`scripts/qa_unified_audio.py`](scripts/qa_unified_audio.py)：句尾、重复句、音量、静音、黑帧、同步等自动检查。
- [`scripts/score_asset_library.py`](scripts/score_asset_library.py)：素材多样性评分。
- [`scripts/score_dynamic_ending.py`](scripts/score_dynamic_ending.py)：动态结尾评分。

## 快速使用

将本目录放到 agent skill 搜索路径，例如：

```bash
git clone https://github.com/peipeijiang/product-ugc-forge.git ~/.agents/skills/product-ugc-forge
```

先验证环境和 skill：

```bash
python3 ~/.agents/skills/product-ugc-forge/scripts/check_env.py --edit-dir ./edit
python3 ~/.agents/skills/product-ugc-forge/scripts/validate_annotations.py ./edit/product_annotation_plan.json
python3 ~/.agents/skills/product-ugc-forge/scripts/score_asset_library.py ./asset_library/library_manifest.json
python3 ~/.agents/skills/product-ugc-forge/scripts/score_dynamic_ending.py ./edit/final.mp4 --edl ./edit/video_use_edl.json
```

provider adapter 支持 dry-run；真正调用前需要设置 `UPDRAMA_API_KEY`，并单独确认付费音频授权：

```bash
python3 ~/.agents/skills/product-ugc-forge/scripts/providers/updrama_client.py gem \
  'このテントは広くて、日差しや雨の日にも使いやすいです。' \
  --voice-id Zephyr --dry-run
```

## 自动质检放行条件

最终视频必须通过：完整日语句尾、无意外重复句、产品标注覆盖、源片音频清除、BGM/旁白 8–12 dB 分离、无黑帧、音画同步、动态结尾和市场/声明一致性检查。失败时最多自动返工三轮；证据、市场或付费授权不明确时停止并请求确认。

## 设计边界

本 skill 可以让 AI 全自动执行混剪，但不会把产品事实、声明证据、市场锁定、provider 计费或最终商业发布授权交给单一剪辑器。所有生成媒体仍需保留 provenance，并在发布前完成视觉和音频复核。

