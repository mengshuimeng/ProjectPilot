# ProjectPilot：基于 Harness Engineering 的项目材料理解与答辩生成助手

ProjectPilot 是一个面向课程项目交付的 AI 原生工具。它不是开放式网页聊天框，而是一个 Retrieval-Grounded + Harness-Controlled 的本地工作流：读取真实项目材料，抽取结构化项目画像，按任务检索证据，调用可配置 LLM 生成内容，再通过 verifier 做自动校验和一次有限修复。

## 项目痛点

课程项目资料通常分散在大创申请书、毕业论文、Markdown 说明、PPT 提纲和 README 草稿中。不同材料的版本、口径和侧重点经常不一致，人工整理简介、创新点和答辩稿时容易出现三个问题：

- 信息查找繁琐，需要反复打开 PDF、Markdown、PPT 提纲。
- 多版本项目名称和技术描述混在一起，最终 README 和答辩稿容易前后不一致。
- 论文页眉页脚、目录、章节号、致谢、大段正文等脏文本可能被误复制进最终材料。

ProjectPilot 的目标是把这类繁琐、重复、容易出错的项目材料整理过程变成一个可运行、可校验、可录屏展示的 AI 原生工具。

## 解决方案

系统从 `data/raw/` 读取 PDF、Markdown 和文本材料，经过解析、清洗、分块和结构化抽取，形成 `profile.json`。当用户生成 `intro`、`innovation` 或 `defense` 时，系统不会把全部材料直接塞给模型，而是先用轻量检索器选出与任务相关的 evidence，再结合 `skills/` 与 `prompts/` 约束 LLM 输出。

如果没有配置 LLM API Key，系统会自动退回规则版生成，保证本地仍可运行、可演示、可提交。

## 功能列表zuowe

- 多文档解析：读取 PDF、Markdown、文本等项目材料。
- 结构化抽取：生成项目名称、核心技术、系统模块、背景、痛点、创新点等 profile。
- 项目名称归一化：将已知别名统一为“基于改进Yolo和PCBNet的景区行人重识别系统”。
- 证据检索：针对 intro、innovation、defense 检索不同 evidence。
- LLM 生成：支持 OpenAI-compatible API，通过环境变量配置。
- 自动校验：检查必填字段、核心术语、解析错误、脏文本、来源覆盖和轻量 unsupported claims。
- 重试修复：若生成结果存在关键 warning，自动把 warning、原稿和 evidence 送入 retry prompt 修复一次。
- 输出产物：生成 `intro.md`、`innovation.md`、`defense.md`、对应 meta 和 evidence 文件。

## Harness Engineering 设计

### 上下文管理 / Agent Skill

ProjectPilot 将上下文拆成稳定的 skill 和任务 prompt，而不是依赖一次性聊天记忆。

- `skills/project_schema.md`：定义项目画像字段。
- `skills/writing_rules.md`：定义输出风格、长度和事实约束。
- `skills/source_priority.md`：定义大创申请书、论文、项目说明、PPT 提纲之间的来源优先级。
- `prompts/*.md`：分别约束简介、创新点、答辩稿、README、retry repair 和 judge 任务。

### 外部工具调用 / Tool / API

系统显式调用外部工具和本地能力完成任务：

- 本地文件解析：`app/parser.py` 读取 PDF、Markdown 和文本。
- CLI 工具：`main.py` 提供 `status`、`extract`、`verify`、`generate`、`runall`、`doctor`。
- 文档处理：`app/extractor.py` 与 `app/retriever.py` 完成清洗、分块、抽取和证据检索。
- LLM API 调用：`app/llm_client.py` 支持 OpenAI-compatible API，使用环境变量配置，不写死 key。

### 验证与反馈闭环 / Feedback Loop

ProjectPilot 的生成结果不是直接交付，而是经过自动检查：

- `app/verifier.py` 检查字段缺失、核心术语、PDF 解析错误、空文档、名称别名、脏文本、重复句子、来源覆盖和轻量 unsupported claims。
- `data/processed/verify_report.json` 保存校验结果。
- 若生成稿存在关键 warning，`app/pipeline.py` 会调用 `prompts/retry_repair.md` 进行一次有限修复。
- 每次生成都会保存 `outputs/{task}_evidence.json` 和 `outputs/{task}_meta.json`，便于追踪来源与调试。

## 系统架构

```text
Raw Docs
  -> Parse
  -> Clean
  -> Extract Profile
  -> Retrieve Evidence
  -> LLM Generate or Rule Fallback
  -> Verify
  -> Retry Repair
  -> Outputs
```

## 目录结构

```text
ProjectPilot/
  app/
    parser.py          # 读取 PDF / Markdown / 文本
    chunker.py         # 文本清洗与分块基础工具
    extractor.py       # 结构化抽取、项目名称归一化、噪声过滤
    retriever.py       # 任务相关 evidence 检索
    llm_client.py      # OpenAI-compatible LLM 客户端
    generator.py       # 规则 + LLM 双模式生成
    verifier.py        # 自动校验与质量检查
    pipeline.py        # Harness orchestrator
    ui.py              # Streamlit Demo 页面
  skills/
    project_schema.md
    writing_rules.md
    source_priority.md
  prompts/
    system_role.md
    intro_generator.md
    innovation_generator.md
    defense_generator.md
    readme_generator.md
    retry_repair.md
    judge.md
  data/
    raw/               # 原始项目材料
    processed/         # documents.json / profile.json / verify_report.json
  outputs/             # 生成内容、meta、evidence
  tests/
  main.py
  requirements.txt
```

## 环境变量说明

LLM 默认关闭。未配置 API Key 时，系统自动使用规则版 fallback。

```powershell
$env:PROJECTPILOT_LLM_ENABLED="true"
$env:PROJECTPILOT_API_KEY="你的 API Key"
$env:PROJECTPILOT_API_BASE="https://api.openai.com/v1"
$env:PROJECTPILOT_MODEL="gpt-4o-mini"
$env:PROJECTPILOT_TIMEOUT="30"
```

```powershell
$env:PROJECTPILOT_LLM_ENABLED="true"
$env:PROJECTPILOT_API_KEY="你的 DeepSeek 或 OpenAI-compatible API Key"
$env:PROJECTPILOT_API_BASE="https://api.deepseek.com"
$env:PROJECTPILOT_MODEL="deepseek-reasoner"
$env:PROJECTPILOT_TIMEOUT="30"
```

不要把真实 API Key 写入 README 或提交到仓库；只在当前终端环境变量中配置。

关闭 LLM：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

## 使用方法

安装依赖：

```powershell
pip install -r requirements.txt
```

查看状态：

```powershell
python main.py status
python main.py doctor
```

抽取与校验：

```powershell
python main.py extract
python main.py verify
```

生成内容：

```powershell
python main.py generate --type intro
python main.py generate --type innovation
python main.py generate --type defense
```

执行全流程：

```powershell
python main.py runall
```

启动 Demo 页面：

```powershell
streamlit run app/ui.py
```

## 输出产物

- `data/processed/documents.json`：清洗后的文档内容。
- `data/processed/profile.json`：结构化项目画像。
- `data/processed/verify_report.json`：最新校验报告。
- `outputs/intro.md`：README 简介。
- `outputs/innovation.md`：创新点总结。
- `outputs/defense.md`：3 分钟答辩稿。
- `outputs/{task}_evidence.json`：每个任务使用的证据。
- `outputs/{task}_meta.json`：生成模式、来源映射、retry 状态和校验报告。

## Demo 建议

3 分钟录屏可以按以下顺序展示：

1. 打开 `data/raw/`，展示 PDF、Markdown、PPT 提纲等真实材料。
2. 运行或点击“抽取”，展示项目画像、核心技术、系统模块和项目名称候选。
3. 点击“校验”，展示 `verify_report.json` 和 warning/info。
4. 点击“生成答辩稿”，展示 `outputs/defense.md`。
5. 打开 `outputs/defense_evidence.json` 和 `outputs/defense_meta.json`，说明来源映射、LLM/fallback 模式和 retry repair。

## 已知不足

- 当前 evidence 检索仍以关键词、来源权重和字段偏好为主，没有接入向量数据库。
- 扫描版 PDF 的 OCR 支持一般，依赖 PDF 是否能提取文本。
- `unsupported_claims` 是轻量检查，只能发现部分明显缺少证据的声明。
- 尚未接入真正的 MCP server，目前外部工具调用以本地 CLI、文件解析和 LLM API 为主。
- LLM 输出质量仍受提示词、证据质量和 API 模型能力影响。
