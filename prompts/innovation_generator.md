# Innovation Generator Prompt

任务：生成当前项目的创新点总结。

输出要求：
- 3 到 5 条，使用编号列表。
- 前 3 到 4 条必须围绕用户上传材料中的项目本身：场景、技术路线、系统架构、模块实现、交付成果。
- 最多 1 条可以说明本次材料生成采用了主材料优先、证据检索、自动校验和重试修复，不能把 ProjectPilot 写成项目主体。
- 不要只重复 anchor 文档原文。
- 只能基于 evidence、profile 和 skills，不得捏造。
- anchor 与 supporting 冲突时，以 anchor 为准。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}

{{demo_rubric}}

{{quality_guardrails}}
