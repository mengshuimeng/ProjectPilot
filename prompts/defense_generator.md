# Defense Generator Prompt

任务：生成 3 分钟左右可直接演讲的答辩稿。

输出要求：
- 使用第一人称或项目汇报口吻，适合课程作业现场讲述。
- 结构建议：问候与项目名称、真实痛点、解决方案、Harness Engineering 设计、功能演示点、总结。
- 必须显式讲清三类 Harness 设计：
  1. 上下文管理 / Agent Skill：skills 与 prompts 如何约束生成。
  2. 外部工具调用 / Tool / API：本地文件解析、CLI、PDF/MD 读取、LLM API。
  3. 验证与反馈闭环 / Feedback Loop：verifier、verify_report、retry repair、evidence coverage。
- 控制在约 700 到 950 个中文字符，便于 3 分钟内讲完。
- 只能基于 evidence、profile 和 skills，不得捏造。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
