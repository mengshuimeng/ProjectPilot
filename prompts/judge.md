# Judge Prompt

任务：辅助判断生成内容是否可信、干净、可提交。

检查重点：
- 是否只基于 evidence，没有捏造。
- 是否优先使用 anchor document，并把 supporting documents 作为补充。
- 是否混入目录、致谢、页眉页脚、章节编号、孤立页码、公式残片。
- 是否出现大段照抄。
- 是否覆盖关键来源。
- 是否把 ProjectPilot 写成普通聊天机器人。
- 是否讲清 Harness Engineering：上下文管理、外部工具调用、验证反馈闭环。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
