# ProjectPilot V2：通用 Harness + LLM 项目材料理解与答辩生成助手

ProjectPilot V2 是一个面向任意项目材料的 AI 原生工具。它不再只服务某一个大创、算法、Web 或论文项目，而是让用户上传一个主材料文件，再可选上传补充材料，系统自动完成项目理解、证据检索、内容生成、校验和修复。

它不是普通聊天机器人，而是一个 Retrieval-Grounded + Harness-Controlled 的项目交付工作流。

## 核心使用方式

### 1. Anchor Document（必填，单文件）

用户必须上传一个主材料文件，作为项目理解和生成的主依据。它可以是：

- 项目申报书
- 项目总体方案
- 项目主论文
- 设计开发文档
- 项目说明书
- 课程大作业主文档

对于当前仓库内的示例项目，`dachuang_application.pdf` 会被推荐为 anchor document，但系统不依赖这个固定文件名。

### 2. Supporting Documents（可选，多文件）

用户可以上传任意补充材料，例如：

- README 草稿
- 用户手册
- PPT 提纲
- 测试说明
- 界面说明
- 项目备注文件

系统会优先围绕 anchor 建立项目画像，supporting documents 只作为补充证据。如果 supporting 与 anchor 冲突，默认以 anchor 为准。

## 支持文件类型

稳定支持：

- `txt`
- `md`
- `pdf`
- `docx`
- `pptx`

兼容支持：

- `doc`
- `ppt`

旧版 `doc` / `ppt` 会尝试通过本地 LibreOffice 转换后解析。如果当前环境不支持转换，系统不会崩溃，而是在文档记录中写入 `parse_warning`。

## 功能列表

- 双上传入口：anchor document + supporting documents。
- 会话隔离：网页端每次上传创建独立 `data/sessions/{session_id}` 工作区。
- Demo 重置：网页端可一键创建干净示例会话，便于录屏展示。
- 多格式解析：解析 txt、md、pdf、docx、pptx，并兼容 doc/ppt。
- 文本清洗：过滤目录、致谢、页眉页脚、章节号、孤立页码、公式残片。
- 通用项目画像：抽取项目名称、项目类型、背景、痛点、用户、技术、架构、模块、创新点、实验结果、交付物、不足和未来工作。
- Anchor 优先证据检索：生成任务会优先检索 anchor 证据，再使用 supporting 补充。
- LLM 生成：支持 OpenAI-compatible API，包括 DeepSeek 等兼容服务。
- 规则 fallback：没有 API key、LLM 关闭或调用失败时仍可本地生成。
- 自动校验：检查 anchor 存在性、来源角色一致性、脏文本、重复表达、来源覆盖、unsupported claims 和 claim-evidence 对齐。
- Retry Repair：关键 warning 出现时，自动进行一次有限修复。
- 生成产物：intro、innovation、defense、readme。

## Harness Engineering 设计

### 上下文管理 / Agent Skill

ProjectPilot V2 使用 `skills/` 和 `prompts/` 明确约束上下文，而不是依赖一次性聊天记忆。

- `skills/project_schema.md`：通用项目画像字段。
- `skills/writing_rules.md`：写作长度、风格、事实约束。
- `skills/source_priority.md`：anchor/supporting 来源优先级。
- `prompts/*.md`：intro、innovation、defense、readme、retry repair、judge 等任务提示词。

### 外部工具调用 / Tool / API

系统显式调用本地工具和外部 API：

- `app/parser.py`：读取 txt、md、pdf、docx、pptx、doc、ppt。
- `app/tool_registry.py`：提供本地工具注册层，当前包含文件检索和 Office 转换工具，接口设计为 MCP-ready。
- `main.py`：提供 CLI 工作流。
- `app/ui.py`：提供 Streamlit 双上传产品页面。
- `app/llm_client.py`：调用 OpenAI-compatible LLM API。

### 验证与反馈闭环 / Feedback Loop

生成结果不会直接交付，而是经过 verifier 检查：

- `app/verifier.py`：检查字段、解析状态、anchor 存在性、来源角色、脏文本、重复句子、来源覆盖和轻量 unsupported claims。
- `claim_evidence_alignment`：对生成输出中的关键声明做句子级轻量证据重叠检查。
- `data/processed/verify_report.json`：保存校验报告。
- `prompts/retry_repair.md`：根据 warning、原稿和 evidence 进行一次有限修复。
- `outputs/{task}_meta.json`：保存生成模式、来源、角色、retry 状态和校验结果。

## 系统架构

```text
Upload / Raw Docs
  -> Parse
  -> Assign Roles (anchor/supporting)
  -> Clean
  -> Extract Generic Profile
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
    parser.py          # 多格式解析与 anchor/supporting role
    chunker.py         # 文本清洗与分块基础工具
    extractor.py       # 通用项目画像抽取
    retriever.py       # anchor 优先 evidence 检索
    llm_client.py      # OpenAI-compatible LLM 客户端
    generator.py       # 规则 + LLM 双模式生成
    verifier.py        # 自动校验与反馈闭环
    pipeline.py        # Harness orchestrator
    ui.py              # 双上传 Streamlit 页面
  prompts/
  skills/
  data/
    raw/
    processed/
    sessions/          # UI 每次上传生成的独立会话工作区
  outputs/
  tests/
  docs/
  .github/workflows/ci.yml
  .env.example
  .editorconfig
  main.py
  requirements.txt
```

仓库已按 GitHub 项目习惯整理：运行时数据、用户上传材料、生成结果、Python 缓存和 Streamlit 临时日志均写入 `.gitignore`。目录下保留 `.gitkeep`，用于展示必要的空目录结构。

## 环境变量

LLM 默认关闭。未配置 API key 时，系统自动使用规则版 fallback。

OpenAI-compatible 示例：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="true"
$env:PROJECTPILOT_API_KEY="你的 API Key"
$env:PROJECTPILOT_API_BASE="https://api.openai.com/v1"
$env:PROJECTPILOT_MODEL="gpt-4o-mini"
$env:PROJECTPILOT_TIMEOUT="30"
```

DeepSeek 示例：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="true"
$env:PROJECTPILOT_API_KEY="你的 DeepSeek API Key"
$env:PROJECTPILOT_API_BASE="https://api.deepseek.com"
$env:PROJECTPILOT_MODEL="deepseek-reasoner"
$env:PROJECTPILOT_TIMEOUT="30"
```

不要把真实 API key 写入 README 或提交到仓库；只在当前终端环境变量中配置。

关闭 LLM：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

CLI 中也可以通过环境变量指定 anchor：

```powershell
$env:PROJECTPILOT_ANCHOR_DOCUMENT="your-main-doc.pdf"
```

## 使用方法

安装依赖：

```powershell
pip install -r requirements.txt
```

检查状态：

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
python main.py generate --type readme
```

执行全流程：

```powershell
python main.py runall
```

启动网页端：

```powershell
streamlit run app/ui.py
```

## UI 双上传窗口

网页端包含两个上传区：

- 左侧：Anchor Document 上传区，单文件，必填。
- 右侧：Supporting Documents 上传区，多文件，可选。

点击“保存上传并抽取”后，系统会：

1. 创建新的 `data/sessions/{session_id}`。
2. 将文件写入该会话的 `raw/`。
3. 写入该会话的 `processed/input_manifest.json`，记录 anchor 和 supporting。
4. 解析文件并生成该会话的 `processed/documents.json`。
5. 抽取通用项目画像并生成该会话的 `processed/profile.json`。
6. 在页面展示项目画像、来源角色、校验结果和生成产物。

网页端顶部会显示当前会话 ID。每次上传都会形成独立工作区，避免不同项目互相污染。

“重置 Demo 示例”按钮会创建一个新的示例会话，不删除 CLI 使用的 `data/raw/`。

## 输出产物

- `data/processed/documents.json`：解析和清洗后的文档，包含 role、parse_status、parse_warning。
- `data/processed/profile.json`：通用项目画像。
- `data/processed/verify_report.json`：最新校验报告。
- `data/sessions/{session_id}/raw/`：UI 当前会话上传材料。
- `data/sessions/{session_id}/processed/`：UI 当前会话结构化中间结果。
- `data/sessions/{session_id}/outputs/`：UI 当前会话生成结果。
- `outputs/intro.md`
- `outputs/innovation.md`
- `outputs/defense.md`
- `outputs/readme.md`
- `outputs/{task}_evidence.json`
- `outputs/{task}_meta.json`

## Demo 建议

3 分钟录屏可以按以下顺序：

1. 打开网页端，展示两个上传窗口。
2. 上传一个 anchor document，再上传若干 supporting documents。
3. 点击“保存上传并抽取”，展示项目画像。
4. 点击生成 intro、innovation、defense、readme。
5. 展示 evidence、meta 和 verify report，说明 anchor 优先、supporting 补充、verifier 与 retry repair。

## 已知不足

- 旧版 `doc` / `ppt` 兼容性依赖本地 LibreOffice 等转换环境。
- 扫描版 PDF 如果没有文本层，解析效果会受限。
- `unsupported_claims` 和 `claim_evidence_alignment` 仍是轻量规则检查，不等同于完整事实证明。
- 当前 evidence 检索仍是轻量关键词和来源权重方案，没有引入重型向量数据库。
- 当前已接入本地工具注册层，但尚未连接外部 MCP server 或知识图谱。
