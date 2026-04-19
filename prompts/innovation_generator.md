# Innovation Generator Prompt

任务：生成 ProjectPilot 的创新点。

输出要求：
- 3 到 5 条，使用编号列表。
- 重点突出工具创新：多源材料治理、项目名称归一化、证据检索、LLM 生成、自动校验、失败重试修复、来源映射。
- 可以提到原项目涉及 YOLOv8、PCBNet、ResNet50 等技术，但不要把创新点全部写成算法本体。
- 每条应简洁、正式、适合课程作业 README 或答辩。
- 只能基于 evidence、profile 和 skills，不得捏造。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
