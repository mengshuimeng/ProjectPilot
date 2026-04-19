# Retry Repair Prompt

任务：根据 verifier 返回的 warnings / noisy_output / source_coverage / unsupported_claims，对原始生成稿做一次有限修复。

输入会包含：
- 原始输出 draft
- verify report 中的 warning 和风险项
- 本任务 evidence
- profile 和 Harness skills

修复要求：
- 只修复被指出的问题，不大幅改写已经正确的内容。
- 删除目录、致谢、页眉页脚、章节号、孤立页码、公式残片等脏文本。
- 对 evidence 中没有支撑的性能结果、算法能力、系统能力改成稳妥表述或删除。
- 如果来源覆盖不足，补充能够被 evidence 支撑的来源相关表达，但不要插入虚构引用。
- 仍然只返回合法 JSON：{"content": "...", "used_sources": [...], "notes": [...]}。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
