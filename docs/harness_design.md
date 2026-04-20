# Harness Engineering 设计说明

本文档对应课程作业要求，说明 ProjectPilot V2 如何体现 Harness Engineering 思想。

## 1. 上下文管理 / Agent Skill

ProjectPilot 不依赖一次性聊天上下文，而是把规则沉淀到固定文件中。

### skills

```text
skills/
  project_schema.md
  writing_rules.md
  source_priority.md
```

职责：

- `project_schema.md`：定义通用项目画像字段。
- `writing_rules.md`：约束生成内容长度、风格和事实边界。
- `source_priority.md`：定义 anchor 优先、supporting 补充的来源规则。

### prompts

```text
prompts/
  system_role.md
  field_summarizer.md
  intro_generator.md
  innovation_generator.md
  defense_generator.md
  readme_generator.md
  retry_repair.md
  judge.md
```

职责：

- 明确不同任务的输出格式。
- 要求只能基于证据生成，不得捏造。
- 将 skills 内容注入任务 prompt。
- retry prompt 接收 warning、原稿和 evidence 后进行修复。

## 2. 外部工具调用 / Tool / API

ProjectPilot 明确调用外部能力，而不是只做网页聊天。

### 本地解析工具

`app/parser.py` 支持读取多种文件：

- txt
- md
- pdf
- docx
- pptx
- doc
- ppt

### 本地工具注册层

`app/tool_registry.py` 提供本地工具入口：

- 本地文件检索。
- Office 转换能力检测。
- Office 旧格式转换调用。
- MCP-ready 的工具状态描述。

当前版本还没有启动独立 MCP server，但接口设计已经把工具能力从业务逻辑中分离出来。

### CLI 工具

`main.py` 提供可复现命令：

```powershell
python main.py status
python main.py doctor
python main.py extract
python main.py verify
python main.py generate --type defense
python main.py runall
```

### LLM API

`app/llm_client.py` 支持 OpenAI-compatible API：

- `PROJECTPILOT_LLM_ENABLED`
- `PROJECTPILOT_API_KEY`
- `PROJECTPILOT_API_BASE`
- `PROJECTPILOT_MODEL`
- `PROJECTPILOT_TIMEOUT`

LLM 调用失败时返回结构化错误，pipeline 会 fallback 到规则生成。

## 3. 验证与反馈闭环 / Feedback Loop

ProjectPilot 的生成不是一次性输出，而是：

```text
Generate -> Verify -> Retry Repair -> Verify
```

### verifier 检查内容

`app/verifier.py` 负责：

- 必填字段检查。
- anchor 存在性检查。
- parse error / empty docs 检查。
- noisy output 检查。
- suspicious long fields 检查。
- repeated phrases 检查。
- source coverage 检查。
- unsupported claims 轻量检查。
- claim-evidence alignment。
- field duplication 检查。
- summary quality warnings。

### retry repair

当校验发现关键 warning，pipeline 会把以下信息送入修复 prompt：

- 原始生成稿。
- verify report。
- profile。
- evidence。
- task 类型。

系统只做一次有限 retry，避免无限循环。

### 可追踪产物

每次生成都会输出：

```text
outputs/{task}.md
outputs/{task}_meta.json
outputs/{task}_evidence.json
data/processed/verify_report.json
```

其中 meta 会记录：

- generation mode
- used sources
- used roles
- anchor document
- warnings before retry
- retry used
- final verify report

这让项目可以解释“为什么这样生成”，而不是只给一个黑盒答案。

