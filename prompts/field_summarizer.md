# Field Summarizer Prompt

任务：把检索到的项目材料证据整理成短摘要候选，用于 LLM 生成前的结构化上下文。

要求：
- 只基于提供的 evidence，总结为短句或短段。
- 不保留目录、致谢、页眉页脚、章节号、孤立页码、公式残片。
- 遇到多个项目名称时，统一归一为“基于改进Yolo和PCBNet的景区行人重识别系统”。
- 每条摘要保留来源文件名。
- 若证据不足，写“证据不足”，不要补编。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
