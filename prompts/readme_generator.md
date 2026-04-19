# README Generator Prompt

任务：生成仓库 README 草稿片段。

输出要求：
- 偏项目说明文档风格，清楚解释项目目标、功能、Harness Engineering 设计、运行方式。
- 不写成聊天机器人介绍。
- 强调 Retrieval-Grounded + Harness-Controlled：证据检索、skills/prompts、LLM 调用、自动校验、有限重试。
- 只能基于 evidence、profile 和 skills，不得捏造。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
