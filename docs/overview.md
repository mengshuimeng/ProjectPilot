# ProjectPilot V2 项目总览

## 项目定位

ProjectPilot V2 是一个通用项目材料理解与答辩生成助手。它面向任意课程项目、科研项目、大创项目、软件项目、硬件项目或论文型项目，不要求用户提前整理成固定模板。

用户只需要提供：

- 一个主材料文件：`anchor document`
- 若干可选补充材料：`supporting documents`

系统会优先围绕 anchor 建立项目画像，再使用 supporting 补充细节。生成内容时不会把所有材料混在一起直接拼接，而是通过证据检索、提示词约束、自动校验和一次有限修复来控制输出质量。

## 真实痛点

项目材料经常分散在 PDF、Markdown、PPT、README、测试说明、设计文档和临时备注中。人工整理这些材料时常见问题包括：

- 主材料和补充材料口径不一致。
- 旧版本信息混入最终 README 或答辩稿。
- 论文页眉页脚、目录、致谢、公式残片混入输出。
- 背景、痛点、创新点、交付物、局限性互相重复。
- 答辩稿需要从多份材料中整理证据，耗时且容易漏掉来源。

ProjectPilot V2 的目标是把这些繁琐工作变成一个可重复、可追踪、可校验的 Harness 工作流。

## 当前已完成功能

- 多格式文档解析。
- anchor/supporting 文档角色建模。
- 文档清洗和噪声过滤。
- 通用项目画像抽取。
- 项目名称识别和已知别名归一化。
- 字段专属候选池和展示摘要。
- 轻量证据检索。
- LLM 生成和规则 fallback 双模式。
- 自动校验和一次 retry repair。
- Streamlit 双上传产品页面。
- CLI 全流程命令。
- session 工作区隔离。
- meta/evidence/report 可追踪输出。
- 回归测试覆盖核心链路。

## 当前可生成内容

- `intro`：项目简介，适合 README 或项目首页。
- `innovation`：创新点总结，兼顾项目本身和 Harness 工程亮点。
- `defense`：3 分钟左右答辩稿。
- `readme`：仓库 README 草稿。

## 当前版本边界

- 扫描版 PDF 如果没有文本层，解析效果仍受限。
- `doc / ppt` 老格式依赖本地转换工具。
- evidence 检索仍是轻量关键词和规则打分，不是向量数据库。
- unsupported claims 和 claim-evidence alignment 是轻量规则检查。
- 尚未接入真正独立运行的 MCP server。
- 复杂 PDF 的章节、表格、指标行仍可能需要继续加强清洗规则。

