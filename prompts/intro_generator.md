# Intro Generator Prompt

任务：生成 README 中的通用项目简介。

输出要求：
- 100 到 180 字左右。
- 一段中文，不要标题。
- 说明项目是什么、解决什么问题、面向什么对象、采用什么关键技术或方法。
- 主体必须介绍用户上传材料中的项目，不要介绍 ProjectPilot 本身。
- 只能基于 evidence、profile 和 skills，不得捏造。
- anchor document 是主依据，supporting documents 只能补充。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
