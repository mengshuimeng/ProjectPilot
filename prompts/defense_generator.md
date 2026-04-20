# Defense Generator Prompt

任务：生成 3 分钟左右可直接演讲的答辩稿。

输出要求：
- 适合任意项目，不预设项目领域。
- 使用项目汇报口吻，结构建议：问候与项目名称、背景痛点、解决方案、系统/方法架构、创新点、结果与不足、总结。
- 主体必须汇报用户上传材料中的项目，不要把 ProjectPilot、Harness 工具或 V2 升级过程写成被答辩项目。
- 可在结尾用一句话说明本稿由主材料优先、补充材料增强、证据检索和自动校验流程生成，不能展开成大段工具介绍。
- 控制在约 700 到 950 个中文字符，便于 3 分钟内讲完。
- 只能基于 evidence、profile 和 skills，不得捏造。
- anchor document 是主依据；supporting documents 只能补充。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}

{{demo_rubric}}

{{quality_guardrails}}
