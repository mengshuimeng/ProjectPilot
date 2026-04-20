# 常用命令与调试指令

本文档集中记录 ProjectPilot V2 的常用运行命令、调试命令、MCP 命令、测试命令和 Git 提交命令。推荐在项目根目录执行这些命令。

```powershell
cd D:\Documents\code\python\ProjectPilot
```

## 1. 环境准备

安装依赖：

```powershell
pip install -r requirements.txt
```

查看 Python 版本：

```powershell
python --version
```

如果本机 `python` 指向错误解释器，可以直接使用当前项目环境：

```powershell
D:\anaconda3\envs\ProjectPilot\python.exe --version
```

## 2. LLM 环境变量

关闭 LLM，使用本地规则 fallback：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

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

指定 CLI 模式下的主材料：

```powershell
$env:PROJECTPILOT_ANCHOR_DOCUMENT="your-main-doc.pdf"
```

查看当前环境变量：

```powershell
Get-ChildItem Env:PROJECTPILOT*
```

清除 API key：

```powershell
Remove-Item Env:PROJECTPILOT_API_KEY
```

## 3. CLI 常用命令

查看当前项目状态：

```powershell
python main.py status
```

检查依赖、材料、skills、prompts、LLM 和工具状态：

```powershell
python main.py doctor
```

抽取项目画像：

```powershell
python main.py extract
```

运行校验：

```powershell
python main.py verify
```

生成项目简介：

```powershell
python main.py generate --type intro
```

生成创新点：

```powershell
python main.py generate --type innovation
```

生成答辩稿：

```powershell
python main.py generate --type defense
```

生成 README 草稿：

```powershell
python main.py generate --type readme
```

执行全流程：

```powershell
python main.py runall
```

## 4. Streamlit UI 命令

启动网页端：

```powershell
streamlit run app/ui.py
```

如果 `streamlit` 不在 PATH，可以使用：

```powershell
python -m streamlit run app/ui.py
```

指定端口启动：

```powershell
python -m streamlit run app/ui.py --server.port 8502
```

无浏览器模式启动：

```powershell
python -m streamlit run app/ui.py --server.headless true
```

## 5. MCP 命令

本地自检 MCP server：

```powershell
python -m app.mcp_server --check
```

给 MCP 客户端配置 stdio server：

```json
{
  "command": "python",
  "args": ["-m", "app.mcp_server", "--stdio"]
}
```

注意：不要在普通终端里直接运行 `python -m app.mcp_server --stdio` 后手动输入空行。stdio MCP server 需要由 MCP 客户端通过 JSON-RPC 协议连接。

## 6. 测试与静态检查

运行全部测试：

```powershell
python -m pytest -q
```

运行单个测试文件：

```powershell
python -m pytest tests/test_smoke.py -q
```

编译核心文件，检查语法：

```powershell
python -m py_compile app/parser.py app/extractor.py app/generator.py app/verifier.py app/pipeline.py app/ui.py app/mcp_server.py main.py
```

检查 UI 是否仍有弃用参数：

```powershell
rg "use_container_width" app/ui.py
```

检查是否误提交 API key：

```powershell
rg "sk-[A-Za-z0-9]|PROJECTPILOT_API_KEY=.*sk-" . --glob "!pytest-cache-files-*" --glob "!.git/**"
```

检查 MCP 命令说明是否一致：

```powershell
rg "python -m app\.mcp_server" README.md docs app tests
```

## 7. 产物查看命令

查看解析后的文档：

```powershell
Get-Content data/processed/documents.json
```

查看项目画像：

```powershell
Get-Content data/processed/profile.json
```

查看校验报告：

```powershell
Get-Content data/processed/verify_report.json
```

查看生成结果：

```powershell
Get-Content outputs/intro.md
Get-Content outputs/innovation.md
Get-Content outputs/defense.md
Get-Content outputs/readme.md
```

查看 evidence：

```powershell
Get-Content outputs/defense_evidence.json
```

查看 meta：

```powershell
Get-Content outputs/defense_meta.json
```

## 8. Git 常用命令

查看远程仓库：

```powershell
git remote -v
```

查看当前状态：

```powershell
git status --short
```

查看改动概览：

```powershell
git diff --stat
```

查看具体改动：

```powershell
git diff
```

添加全部改动：

```powershell
git add .
```

提交：

```powershell
git commit -m "Update ProjectPilot V2"
```

推送：

```powershell
git push origin main
```

如果 `.vscode/settings.json` 已被跟踪，但不想提交：

```powershell
git rm --cached .vscode/settings.json
```

## 9. 清理运行缓存

清理 Python 缓存：

```powershell
Remove-Item -LiteralPath app\__pycache__,tests\__pycache__ -Recurse -Force -ErrorAction SilentlyContinue
```

查找 Python 缓存：

```powershell
Get-ChildItem -Path app,tests -Directory -Filter __pycache__ -ErrorAction SilentlyContinue
```

清理 Streamlit smoke-test 日志：

```powershell
Remove-Item -LiteralPath .streamlit-*.out,.streamlit-*.err -Force -ErrorAction SilentlyContinue
```

注意：不要随意删除 `data/sessions/`、`data/raw/` 或 `outputs/` 中仍要用于 Demo 的文件。如果要清理运行时产物，建议先确认这些文件不需要提交。

## 10. 常见问题排查

### MCP server 直接运行报 JSON 错误

使用：

```powershell
python -m app.mcp_server --check
```

不要直接在终端里运行 stdio 模式后手动输入内容。MCP 客户端配置应使用：

```json
{
  "command": "python",
  "args": ["-m", "app.mcp_server", "--stdio"]
}
```

### Streamlit 提示 use_container_width 弃用

搜索：

```powershell
rg "use_container_width" app/ui.py
```

应该改成：

```python
width="stretch"
```

### LLM 调用失败

先运行：

```powershell
python main.py doctor
```

确认：

- `PROJECTPILOT_LLM_ENABLED=true`
- `PROJECTPILOT_API_KEY` 已设置
- `PROJECTPILOT_API_BASE` 正确
- `PROJECTPILOT_MODEL` 正确

如果赶时间，可以关闭 LLM：

```powershell
$env:PROJECTPILOT_LLM_ENABLED="false"
```

系统会使用本地 fallback。

### 上传新项目后仍显示旧内容

网页端点击：

```text
清空页面
```

再重新上传主材料，点击：

```text
保存上传并抽取
```

CLI 模式下可重新运行：

```powershell
python main.py extract
python main.py verify
```

