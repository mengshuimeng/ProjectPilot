# 使用指南

## 安装依赖

```powershell
pip install -r requirements.txt
```

## 配置 LLM

ProjectPilot 可以不配置 LLM。没有 API key 或关闭 LLM 时，会自动使用规则 fallback。

启用 OpenAI-compatible API：

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

关闭 LLM：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

不要把真实 API key 写入代码、README 或提交历史。

## CLI 使用

### 1. 准备材料

把材料放入：

```text
data/raw/
```

如果需要指定 anchor：

```powershell
$env:PROJECTPILOT_ANCHOR_DOCUMENT="your-main-doc.pdf"
```

如果不指定，系统会按当前 parser/pipeline 规则选择主材料。

### 2. 查看状态

```powershell
python main.py status
python main.py doctor
```

`status` 用于查看原始文件、anchor、supporting、解析状态和 LLM 模式。  
`doctor` 用于检查 API、skills、prompts、raw 文件和本地工具状态。

### 3. 抽取和校验

```powershell
python main.py extract
python main.py verify
```

抽取后会生成：

```text
data/processed/documents.json
data/processed/profile.json
```

校验后会生成：

```text
data/processed/verify_report.json
```

### 4. 生成内容

```powershell
python main.py generate --type intro
python main.py generate --type innovation
python main.py generate --type defense
python main.py generate --type readme
```

每个任务会输出：

```text
outputs/{task}.md
outputs/{task}_meta.json
outputs/{task}_evidence.json
```

### 5. 全流程

```powershell
python main.py runall
```

执行顺序：

```text
extract -> verify -> intro -> innovation -> defense -> readme
```

## UI 使用

启动网页端：

```powershell
streamlit run app/ui.py
```

## MCP server 使用

检查 MCP server：

```powershell
python -m app.mcp_server --check
```

给 MCP 客户端配置 stdio server 时使用：

```json
{
  "command": "python",
  "args": ["-m", "app.mcp_server", "--stdio"]
}
```

该 server 面向支持 MCP 的客户端暴露 ProjectPilot 本地工具：

- `projectpilot_status`
- `search_project_files`
- `search_raw_materials`
- `convert_office_material`
- `extract_project_profile`
- `retrieve_task_evidence_mcp`
- `verify_project_materials`
- `project_knowledge_map`
- `orchestrate_project_task`

页面流程：

1. 上传主材料。
2. 可选上传补充材料。
3. 点击“保存上传并抽取”。
4. 点击“运行校验”。
5. 点击“生成全部”，或在各 Tab 内单独生成。
6. 查看项目画像、校验状态、生成结果和证据来源。

UI 有两个辅助按钮：

- `清空当前会话`：清空页面展示，不删除历史磁盘文件。
- `重置 Demo 示例`：创建一个新的干净示例 session，方便录屏。

## 支持格式

稳定支持：

- `txt`
- `md`
- `pdf`
- `docx`
- `pptx`

兼容支持：

- `doc`
- `ppt`

旧版 Office 格式依赖本地转换工具。无法转换时，系统会写入 `parse_warning`，不会崩溃。
