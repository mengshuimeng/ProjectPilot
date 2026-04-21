# 3 分钟 Demo 录屏指南

本文档给出一个适合课程答辩的 3 分钟演示路线。

## 演示目标

让观众看到 ProjectPilot 不是普通聊天框，而是一个 Harness + LLM 项目材料处理工具：

- 有主材料和补充材料。
- 有解析和结构化项目画像。
- 有 evidence 来源链。
- 有校验报告。
- 有 LLM 或 fallback 生成。
- 有 retry repair 机制。

## 演示前准备

1. 安装依赖。

```powershell
pip install -r requirements.txt
```

2. 可选配置 LLM。

```powershell
$env:PROJECTPILOT_LLM_ENABLED="true"
$env:PROJECTPILOT_API_KEY="你的 API Key"
$env:PROJECTPILOT_API_BASE="https://api.deepseek.com"
$env:PROJECTPILOT_MODEL="deepseek-reasoner"
$env:PROJECTPILOT_TIMEOUT="30"
```

无 API key 时可以关闭 LLM：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

3. 启动 UI。

```powershell
streamlit run app/ui.py
```

## 推荐录屏流程

### 0:00 - 0:25 项目定位

讲解：

> ProjectPilot 是一个通用项目材料理解与答辩生成助手。它不是聊天机器人，而是把项目材料解析、证据检索、生成、校验和修复组织成 Harness 工作流。

展示页面顶部：

- 当前模式。
- 当前模型。
- 当前会话。
- 当前主材料。
- 当前建议动作。

### 0:25 - 0:55 上传材料

展示两个上传区：

- 主材料上传：上传项目申报书、说明书或主论文。
- 补充材料上传：上传 PPT、README、测试说明等。

讲解：

> anchor document 是主事实来源，supporting documents 只补充证据。材料冲突时默认以 anchor 为准。

### 0:55 - 1:20 保存上传并抽取

点击：

```text
保存上传并抽取
```

展示项目画像：

- 项目名称。
- 项目类型。
- 背景摘要。
- 痛点摘要。
- 创新点摘要。
- 交付物。
- 局限性。
- 技术标签。
- 模块标签。

讲解：

> UI 展示的是 display summaries，不是原始长段文本。系统会用字段专属候选池和跨字段去重，避免背景、痛点、交付物和局限性互相复制。

### 1:20 - 1:45 运行校验

点击：

```text
运行校验
```

展示校验状态：

- passed。
- warnings。
- infos。

讲解：

> verifier 会检查 anchor 是否存在、解析是否失败、输出是否混入脏文本、来源是否覆盖、字段是否重复、声明是否有证据支撑。页面右侧还会显示 claim-support 摘要，便于现场解释为什么这段内容可信。

### 1:45 - 2:30 生成全部

点击：

```text
生成全部
```

展示四个 Tab：

- 项目简介。
- 创新点。
- 答辩稿。
- README 草稿。

重点打开“答辩稿”。

讲解：

> 生成阶段会先检索 evidence，再把 evidence、profile、skills 和 prompt 交给 LLM。如果没有 LLM 或调用失败，会使用规则 fallback，保证本地可运行。

### 2:30 - 2:55 展示 evidence 和 meta

展示底部“证据与来源”区域：

- 主材料来源。
- 证据块数量。
- 生成模式。
- retry 是否发生。
- anchor/supporting 来源。
- claim-support 支撑率。
- 实际使用来源。

讲解：

> 每个输出都有 evidence 和 meta，可以追踪用了哪些来源、是否发生 retry，以及校验报告结果。现在 UI 里还能直接看到 claim-support 摘要和关键 evidence 片段，更方便讲清楚闭环。

### 2:55 - 3:00 总结

讲解：

> ProjectPilot 的核心价值是把分散项目材料转成可校验、可追踪、可生成的项目交付内容，体现了上下文管理、外部工具调用和验证反馈闭环。

## 演示失败兜底

如果 LLM API 网络不稳定：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

然后重新运行 UI。系统会使用 fallback 模式，Demo 仍可完成。

如果上传材料解析失败：

- 换成带文本层的 PDF。
- 使用 md/txt/docx/pptx。
- 查看 `parse_warning`。
