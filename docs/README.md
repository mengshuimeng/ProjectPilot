# ProjectPilot 文档目录

这里集中放置 ProjectPilot V2 的设计、使用、演示和维护文档。README 面向项目首页快速介绍，`docs/` 面向答辩、开发复盘和后续维护。

## 推荐阅读顺序

1. [项目总览](overview.md)  
   了解 ProjectPilot V2 解决什么问题、当前已实现什么、已知不足和后续规划。

2. [使用指南](usage_guide.md)  
   了解 CLI、Streamlit UI、环境变量、文件上传和输出位置。

3. [常用命令与调试指令](command_reference.md)  
   集中查看运行、调试、MCP、测试、Git 和清理命令。

4. [系统架构](architecture.md)  
   了解 anchor/supporting 输入模型、pipeline 主流程和各模块职责。

5. [Harness Engineering 设计](harness_design.md)  
   对应课程要求，说明上下文管理、外部工具调用、验证反馈闭环。

6. [数据契约](data_contracts.md)  
   说明 `documents.json`、`profile.json`、`verify_report.json`、`meta/evidence` 的主要字段。

7. [质量控制与测试](quality_and_testing.md)  
   说明文本清洗、展示摘要、字段去重、校验器和测试覆盖。

8. [Demo 录屏指南](demo_guide.md)  
   提供 3 分钟答辩 Demo 的推荐操作路线和讲解词。

9. [项目结构说明](project_structure.md)  
   说明哪些文件应该提交，哪些运行时文件不应该提交。

10. [开发记录](development_record.md)  
   记录从早期版本到当前 V2 的主要迭代过程。

11. [后续路线图](roadmap.md)  
    记录当前仍可继续增强的方向。

## 当前版本一句话

ProjectPilot V2 是一个通用的 Harness + LLM 项目材料理解与答辩生成助手。用户上传一个主材料文件和若干补充材料后，系统会完成解析、清洗、项目画像抽取、证据检索、内容生成、自动校验和必要的重试修复。

## 当前主要能力

- 支持 `txt / md / pdf / docx / pptx` 稳定解析。
- 对 `doc / ppt` 做兼容解析，依赖本地转换环境。
- 预留 OCR fallback 接口。
- 支持 anchor document 和 supporting documents。
- 支持 CLI 和 Streamlit 双入口。
- 支持 OpenAI-compatible LLM API。
- 保留无 API key 时的规则 fallback。
- 输出 `intro / innovation / defense / readme`。
- 保存 evidence、meta、verify report，便于追踪。
- UI 每次上传创建独立 session，避免不同项目互相污染。
- 项目画像展示使用 `display_summaries`，避免 raw 字段重复污染。
- 使用 6 个 Agent Skills 管理 schema、写作、来源、Demo、质量和仓库规则。
- 使用轻量 lexical + semantic 混合索引做 evidence 检索。
- 提供句子级 claim-support 对齐结果。
- 提供 stdio MCP server 和工作流工具。
