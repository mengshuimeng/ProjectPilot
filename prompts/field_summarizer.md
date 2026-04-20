# Field Summarizer Prompt

任务：把检索到的通用项目材料证据整理成短摘要候选，用于 LLM 生成前的结构化上下文。

要求：
- 只基于提供的 evidence，总结为短句或短段。
- 不保留目录、致谢、页眉页脚、章节号、孤立页码、公式残片。
- anchor document 是主事实来源，supporting documents 只做补充。
- 遇到多个项目名称或版本冲突时，优先采用 anchor 的表述。
- 每条摘要保留来源文件名。
- 若证据不足，写“证据不足”，不要补编。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}

{{quality_guardrails}}
