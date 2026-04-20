# Repository Rules

ProjectPilot 生成 README 或仓库说明时，需要符合可提交 GitHub 项目的习惯。

README 应包含：

- 项目名称和一句话定位。
- 真实痛点。
- 解决方案和核心流程。
- 功能列表。
- Harness Engineering 设计说明。
- 系统架构或流程图。
- 目录结构。
- 环境变量说明。
- CLI 和 UI 使用方法。
- MCP server 自检和客户端配置方法。
- 输出产物路径。
- Demo 建议。
- 已知不足。

仓库提交规则：

- 不提交真实 API key。
- 不提交 `.env`。
- 不提交 `__pycache__`、`.pytest_cache`、Streamlit 临时日志。
- 不提交用户上传材料、运行时 processed 数据和 outputs 产物，除非课程明确要求。
- 使用 `.gitkeep` 保留必要空目录。
- `.vscode/` 属于本地 IDE 配置，不应作为项目必要文件提交。

文档表达：

- 面向课程作业和 GitHub 读者，语言清楚、可复现。
- 不要写成营销页。
- 不要把 ProjectPilot 说成万能系统；需要保留已知不足。
