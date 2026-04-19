# Intro Generator Prompt

任务：生成 README 中的项目简介。

输出要求：
- 100 到 180 字左右。
- 一段中文，不要标题。
- 说明 ProjectPilot 如何读取 PDF / Markdown / PPT 提纲等项目材料，抽取项目画像，并生成可校验的简介、创新点和答辩稿。
- 突出“项目材料理解与答辩生成助手”，不要只复述景区 ReID 算法本体。
- 只能基于 evidence、profile 和 skills，不得捏造。
- 不输出目录、致谢、页眉页脚、章节号、孤立页码。

注入的 Harness skills：
{{project_schema}}

{{writing_rules}}

{{source_priority}}
