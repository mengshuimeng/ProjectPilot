# README Generator Prompt

任务：生成可复用 README 底稿内容。

输出要求：
- 偏项目仓库说明文档风格，不写成答辩稿。
- 至少包含：项目简介、项目类型、核心功能或模块、技术/方法、运行或使用说明、交付成果、后续优化。
- 支持任意项目类型，不要写成只服务某个固定项目。
- README 主体必须服务用户上传材料中的项目，不要写成 ProjectPilot 自身的 README。
- 如需说明材料来源，只能简短写明内容基于主材料优先、补充材料增强的证据流程整理。
- 只能基于 evidence、profile 和 skills，不得捏造。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}

{{quality_guardrails}}

{{repository_rules}}
