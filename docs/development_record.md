# ProjectPilot 开发记录

记录日期：2026-04-20

本文档用于记录本轮对 ProjectPilot 的主要开发、修复和验证过程，方便后续提交作业、写报告、录 Demo 或继续迭代时回看。

## 1. 项目定位调整

最初版本的 ProjectPilot 更偏向服务固定材料集，尤其是“基于改进 Yolo 和 PCBNet 的景区行人重识别系统”这一项目。后续将项目重新定义为：

**ProjectPilot：通用 Harness + LLM 项目材料理解与答辩生成助手。**

新的定位不是聊天机器人，而是一个围绕项目材料自动完成理解、证据检索、生成、校验和修复的 AI 原生工具。

核心使用方式调整为：

- 用户上传一个主材料文件，称为 anchor document。
- 用户可选上传多个补充材料，称为 supporting documents。
- 系统优先围绕 anchor 建立项目画像。
- supporting documents 只作为补充证据来源。
- 如果 anchor 和 supporting 冲突，默认以 anchor 为准。

## 2. Harness + LLM 能力建设

本轮将 ProjectPilot 从“规则抽取 + 模板生成”升级为“Retrieval-Grounded + Harness-Controlled LLM”工具。

主要完成内容：

- 新增 LLM 客户端抽象层，支持 OpenAI-compatible API。
- 支持通过环境变量配置模型、API base、API key、timeout。
- 保留规则版 fallback：没有 API key、LLM 关闭或调用失败时，系统仍可本地生成。
- 引入 prompts 目录下的任务级 prompt。
- 保留并强化 skills 目录作为上下文管理层。
- 生成流程中显式使用 profile、evidence、skills 和 prompts。
- 输出时保留 meta 和 evidence，方便追踪来源。

涉及文件：

- `app/llm_client.py`
- `app/generator.py`
- `prompts/system_role.md`
- `prompts/intro_generator.md`
- `prompts/innovation_generator.md`
- `prompts/defense_generator.md`
- `prompts/readme_generator.md`
- `prompts/retry_repair.md`
- `skills/project_schema.md`
- `skills/writing_rules.md`
- `skills/source_priority.md`
- `skills/demo_rubric.md`
- `skills/quality_guardrails.md`
- `skills/repository_rules.md`

## 3. Anchor / Supporting 输入模型

V2 中引入了明确的文档角色：

- `anchor`
- `supporting`

系统现在会在以下产物中记录文档角色：

- `data/processed/documents.json`
- `data/processed/profile.json`
- `outputs/{task}_evidence.json`
- `outputs/{task}_meta.json`

主流程变为：

```text
Upload / Raw Docs
-> Parse
-> Assign Roles
-> Extract Generic Profile
-> Retrieve Evidence
-> LLM or Rule Generate
-> Verify
-> Retry Repair
-> Outputs
```

## 4. Parser 文件解析增强

对 `app/parser.py` 做了增强，使其更适合真实用户上传材料。

稳定支持：

- `txt`
- `md`
- `pdf`
- `docx`
- `pptx`

兼容支持：

- `doc`
- `ppt`

旧版 `doc / ppt` 依赖本地 LibreOffice 等转换环境。如果无法转换，系统不会崩溃，而是写入 `parse_warning`。

每个解析后的文档包含：

- `name`
- `suffix`
- `path`
- `text`
- `char_count`
- `parse_status`
- `parse_warning`
- `role`

## 5. Extractor 通用化

`app/extractor.py` 从固定景区 ReID 项目抽取，调整为通用项目画像抽取。

新的 profile 字段包括：

- `anchor_document`
- `supporting_documents`
- `source_roles`
- `project_name`
- `project_type`
- `background`
- `pain_points`
- `target_users`
- `core_technologies`
- `system_architecture`
- `system_modules`
- `innovation_points`
- `experiment_results`
- `deliverables`
- `limitations`
- `future_work`
- `field_sources`
- `doc_stats`

保留的兼容能力：

- 仍然保留原景区行人重识别项目的 canonical project name。
- 仍然识别并归一化已知别名。
- 仍然过滤目录、致谢、页眉页脚、章节号、孤立页码、公式残片等脏文本。

后续修复中还增强了：

- 清理 `第 1 章`、`1.1`、`作品简介`、`需求分析` 等章节前缀。
- 修复项目名称中混入“项目名称：”的问题。
- 防止将任何项目都误抽成 ProjectPilot 自身的模块，例如“文档解析、内容生成、自动校验”。
- 增加对硬件 / IoT 项目、传感器、STM32、物联网、巡检小车等场景的泛化识别。

## 6. Retriever 证据检索增强

`app/retriever.py` 被改造成轻量证据检索层。

特点：

- 不引入向量数据库。
- 使用关键词、字段偏好、来源权重、长度惩罚进行打分。
- anchor 证据优先。
- supporting 证据作为补充。
- 不同任务使用不同检索偏好。

任务类型：

- `intro`
- `innovation`
- `defense`
- `readme`

每次生成会写出：

- `outputs/{task}_evidence.json`

证据块包含：

- `source`
- `role`
- `score`
- `text`

## 7. Generator 双模式生成

`app/generator.py` 已支持双模式：

- Harness + LLM 模式
- Rule-based fallback 模式

支持生成：

- `intro`
- `innovation`
- `defense`
- `readme`

LLM 模式下：

- 读取 profile。
- 读取 evidence。
- 注入 skills。
- 注入任务 prompt。
- 要求模型返回结构化 JSON。

fallback 模式下：

- 不依赖 API key。
- 根据 profile 生成可用文本。
- 输出不会崩溃。

后续修复中解决了一个重要问题：

之前生成内容会反复出现固定的 ProjectPilot V2 介绍，例如“这次 V2 升级的目标，是把 ProjectPilot 从服务单一材料集的工具……”。这会导致不管上传什么项目，答辩稿都像在介绍 ProjectPilot 本身。

修复后：

- `intro` 主体介绍用户上传的项目。
- `innovation` 前几条围绕项目本身，只保留最多一条生成流程可追踪说明。
- `defense` 改成项目答辩稿，不再大段讲 ProjectPilot V2。
- `readme` 生成当前项目的 README 底稿，而不是 ProjectPilot 自己的 README。

## 8. Verifier 校验与反馈闭环

`app/verifier.py` 从简单字段检查增强为生成质量守门人。

检查内容包括：

- 必填字段检查。
- parse error / empty docs 检查。
- anchor 存在性检查。
- source role consistency 检查。
- noisy output 检查。
- suspicious long fields 检查。
- repeated phrases 检查。
- source coverage 检查。
- unsupported claims 轻量检查。
- parse warnings summary。

输出报告：

- `data/processed/verify_report.json`

若校验发现关键 warning，pipeline 会触发一次有限 retry repair。

## 9. Pipeline 编排增强

`app/pipeline.py` 现在承担 Harness orchestrator 角色。

主要流程：

- `run_extract()`
  - 读取 raw 文件。
  - 读取 manifest。
  - 解析文档。
  - 写出 `documents.json`。
  - 写出 `profile.json`。

- `run_verify()`
  - 读取 profile。
  - 读取 documents。
  - 读取最新输出。
  - 写出 `verify_report.json`。

- `run_generate(task)`
  - 读取或创建 profile。
  - 检索 evidence。
  - 生成初稿。
  - 校验初稿。
  - 必要时 retry repair。
  - 写出最终产物。

- `run_all()`
  - extract
  - verify
  - generate intro
  - generate innovation
  - generate defense
  - generate readme

后续修复中增加了 processed 新鲜度检查：

- 如果 raw 文件、manifest、documents 或 profile 不一致，会自动重新抽取。
- 如果上传了新项目，但旧 profile 还存在，生成前不会继续复用旧 profile。

这是为了解决“不管上传什么项目，抽取都变成同一个内容”的问题。

## 10. CLI 增强

`main.py` 保留原有命令，并新增或增强了展示信息。

可用命令：

```powershell
python main.py status
python main.py doctor
python main.py extract
python main.py verify
python main.py generate --type intro
python main.py generate --type innovation
python main.py generate --type defense
python main.py generate --type readme
python main.py runall
```

CLI 会显示：

- raw 文件数量。
- anchor document。
- supporting documents 数量。
- 解析状态。
- LLM 模式状态。
- 输出路径。
- meta 路径。
- evidence 路径。

## 11. UI 产品化改造

`app/ui.py` 被改造成更适合录屏演示的 Streamlit 产品页面。

主要页面结构：

- 顶部：ProjectPilot 标题、副标题、当前模式、大模型、主材料。
- 上传区：主材料上传、补充材料上传。
- 操作区：保存上传并抽取、抽取、校验、生成全部、清空页面。
- 中间：项目画像、文档列表、技术标签、模块标签。
- 右侧：校验报告、生成结果 tabs、来源、生成模式、重试状态。

后续修复：

- UI 全部改成中文展示。
- 去掉 `use_container_width` 弃用写法，改成 `width="stretch"`。
- 打开 UI 时不自动展示历史残留。
- 新增“清空页面”按钮，只清空网页展示，不删除磁盘文件。
- 修复上传新文件后直接点“抽取 / 校验 / 生成全部 / 单独生成”仍复用旧文件的问题。

现在 UI 行为是：

- 初次打开页面为空白会话。
- 不自动展示上一次 profile、verify report 或 outputs。
- 只在本次点击操作后展示本次结果。
- 如果当前页面有新上传文件，任何操作都会先保存上传，再重新抽取。

## 12. README 重写

`README.md` 已改为 V2 可提交版本。

主要内容包括：

- 项目名称。
- 项目痛点。
- 解决方案。
- 功能列表。
- Harness Engineering 设计。
- 系统架构。
- 目录结构。
- 环境变量说明。
- 使用方法。
- Demo 建议。
- 已知不足。

README 明确说明：

- ProjectPilot 不是只服务单一大创项目。
- ProjectPilot 是通用项目材料理解与答辩生成助手。
- 使用方式是上传一个 anchor document，再可选上传 supporting documents。
- 这不是普通聊天机器人，而是 Harness + LLM 工具。

## 13. 测试补充

测试集中在 `tests/test_smoke.py`。

已覆盖：

- parser 读取 `md / pdf`。
- parser 读取 `docx / pptx`。
- extractor 输出通用项目名。
- retriever 返回非空 evidence。
- generator fallback 输出字符串。
- llm_client 未配置 key 时不崩溃。
- verifier 返回 dict 且包含 `passed`。
- runall 输出 `intro / innovation / defense / readme`。
- 防止 fallback defense 再出现固定 ProjectPilot V2 套话。
- 防止 raw/manifest 更换后 generate 继续复用旧 profile。

最近一次验证结果：

```text
9 passed
```

## 14. 环境变量

LLM 默认可关闭，关闭后使用规则 fallback。

可配置：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="true"
$env:PROJECTPILOT_API_KEY="你的 API Key"
$env:PROJECTPILOT_API_BASE="https://api.deepseek.com"
$env:PROJECTPILOT_MODEL="deepseek-reasoner"
$env:PROJECTPILOT_TIMEOUT="30"
```

关闭 LLM：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

注意：API key 不应写入代码或提交到仓库。

## 15. 当前产物路径

结构化中间结果：

- `data/processed/documents.json`
- `data/processed/profile.json`
- `data/processed/verify_report.json`
- `data/processed/input_manifest.json`

生成结果：

- `outputs/intro.md`
- `outputs/innovation.md`
- `outputs/defense.md`
- `outputs/readme.md`

追踪信息：

- `outputs/intro_meta.json`
- `outputs/innovation_meta.json`
- `outputs/defense_meta.json`
- `outputs/readme_meta.json`
- `outputs/intro_evidence.json`
- `outputs/innovation_evidence.json`
- `outputs/defense_evidence.json`
- `outputs/readme_evidence.json`

## 16. 已知不足

当前版本仍有一些诚实限制：

- 扫描版 PDF 如果没有文本层，解析效果会受限。
- 旧版 `doc / ppt` 的兼容支持依赖本地转换环境。
- unsupported claims 仍是轻量规则检查，不是真正的事实验证模型。
- 证据检索仍是轻量关键词打分，没有引入向量数据库。
- 尚未接入真正的 MCP server 或外部知识图谱。
- 对排版非常复杂的 PDF，章节前缀和页眉页脚仍可能残留，需要继续增强清洗规则。

## 17. 后续优化建议

本轮后续又完成了以下增强：

- UI 已增加当前会话 ID。
- 每次上传都会保存到 `data/sessions/{session_id}`，形成独立工作区。
- 每个会话拥有自己的 `raw / processed / outputs / session.json`。
- UI 已增加“重置 Demo 示例”按钮，可一键创建干净示例会话。
- pipeline 已支持 session 工作区，同时保持 CLI 原有 `data/raw` 兼容。
- project name 抽取已增强，会过滤作者名、摘要、关键词、指导教师等噪声。
- verifier 已增加 `claim_evidence_alignment`，对输出中的关键声明做轻量句子级证据重叠检查。
- 已新增本地工具注册层 `app/tool_registry.py`，当前包含本地文件检索和 Office 转换工具。
- 已新增 `app/mcp_server.py`，提供 stdio MCP server，可暴露 ProjectPilot 状态、工作区文件检索、raw 材料检索和 Office 转换工具。
- parser 的旧版 Office 转换已改为通过工具层调用。
- doctor 会显示本地工具数量、Office 转换可用性和 MCP 连接说明。
- 项目结构已按 GitHub 仓库习惯整理，新增 `.gitignore`、`.env.example`、`.editorconfig`、`.streamlit/config.toml` 和 GitHub Actions CI。
- 新增 `docs/project_structure.md`，说明源码目录、运行时目录、输出目录和哪些文件不应提交。
- 已将历史误跟踪的 `__pycache__`、运行时数据和输出产物从 Git 索引中移除，保留 `.gitkeep` 维持目录结构。

新增测试覆盖：

- session 工作区隔离。
- 项目名不混入作者和摘要。
- claim-evidence 对齐报告。
- 本地工具注册与文件检索。

当前测试结果已更新为：

```text
13 passed
```

## 18. 项目画像字段重复污染修复

后续又修复了“项目画像字段重复污染”问题。

问题表现：

- 背景摘要、痛点摘要、创新点摘要、交付物、局限性经常复用同一段原文。
- 交付物有时会被误抽成算法训练细节。
- 局限性有时直接复用痛点。
- UI 默认展示 raw 字段，导致页面像信息墙。

本次修复覆盖三层：

- `app/extractor.py`
  - 为背景、痛点、创新点、交付物、局限性建立字段专属候选池。
  - 从段落级候选改为句子级候选。
  - 增加跨字段互斥，避免同一句或高度相似句子被多个字段复用。
  - 在 `profile.json` 中新增 `field_candidates`、`display_summaries` 和 `display_summary_sources`。

- `app/generator.py`
  - 新增 `build_display_summaries(profile)` 和 `compress_summary(...)`。
  - fallback 生成优先使用 `display_summaries`，不再直接使用长段 raw 字段。
  - 对交付物、局限性缺失场景使用“待补充”占位，而不是复制其他字段。

- `app/verifier.py`
  - 新增 `field_duplication`。
  - 新增 `duplicated_field_pairs`。
  - 新增 `summary_quality_warnings`。
  - 检查背景/痛点、痛点/局限性、创新点/交付物、交付物/局限性之间的高度重复。
  - 检查交付物是否混入 Backbone、TriHard、Batch Size、数据增强等训练细节。

- `app/ui.py`
  - 项目画像区域只展示 `profile["display_summaries"]`。
  - 原始候选放入“来源”折叠区，不作为默认展示内容。

新增回归测试：

- `display_summaries` 必须存在。
- 背景摘要和痛点摘要不能完全一样。
- 局限性不能直接等于痛点。
- 交付物不能明显包含大量训练细节术语。
- 缺失高质量局限性时允许显示“待补充”。
- verifier 能报告字段重复和摘要质量问题。

当前测试结果已更新为：

```text
17 passed
```

## 19. docs 文档目录完善

为方便提交作业、答辩讲解和后续维护，新增了完整的 `docs/` 文档目录：

- `docs/README.md`
- `docs/overview.md`
- `docs/usage_guide.md`
- `docs/architecture.md`
- `docs/harness_design.md`
- `docs/data_contracts.md`
- `docs/quality_and_testing.md`
- `docs/demo_guide.md`
- `docs/roadmap.md`

这些文档分别说明项目总览、使用方式、系统架构、Harness 设计、数据契约、质量控制、Demo 录屏路线和后续路线图。

## 20. Agent Skills 扩展

为进一步体现 Harness 的上下文管理能力，新增 3 个技能文件：

- `skills/demo_rubric.md`：约束 Demo 和答辩内容覆盖课程评分点，包括痛点、架构、Harness 设计和实际运行。
- `skills/quality_guardrails.md`：约束输出清洁度、字段去重、事实支撑、交付物和局限性抽取质量。
- `skills/repository_rules.md`：约束 README、仓库说明、环境变量、MCP、输出路径和提交边界。

同时更新：

- `app/generator.py`：`_load_skill_bundle()` 注入 6 个 skills。
- `prompts/*.md`：按任务注入 demo、quality、repository 相关技能。
- `main.py`：doctor 检查 6 个 skills 和完整 prompts。
- `tests/test_smoke.py`：新增 skill 存在性与 prompt 注入回归测试。

当前测试结果已更新为：

```text
20 passed
```

仍可以继续做的方向：

- 加入 OCR 支持，提高扫描版 PDF 可用性。
- 扩展更多 MCP 工具，例如 OCR、文档元数据读取和 session 导出。
- 接入本地 OCR 服务或文档转换服务。
- 将 claim-evidence 从轻量关键词重叠升级为更严格的语义对齐。
- 为每个 session 增加导出压缩包功能。
