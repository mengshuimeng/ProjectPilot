# 质量控制与测试

ProjectPilot V2 的质量控制分为四层：

1. 解析和清洗。
2. 项目画像抽取。
3. 生成结果校验。
4. 自动化测试。

## 1. 文本清洗

`app/extractor.py` 会过滤常见脏文本：

- 目录。
- 致谢。
- 页眉页脚。
- 章节号，如 `第 1 章`、`1.1`。
- 图表编号，如 `图 1`、`表 1`。
- 孤立页码。
- 公式残片。
- 联系电话、学号、电子信箱、指导教师等表单残片。
- 经费预算和比赛封面信息。
- 数字符号比例异常高的段落。

## 2. 展示摘要和字段去重

早期版本会把同一段原文放入多个字段，导致项目画像里背景、痛点、创新点、交付物和局限性高度重复。

当前版本做了三层修复：

### 字段专属候选池

每个展示字段都有独立正关键词和负关键词：

- `background_summary`
- `pain_points_summary`
- `innovation_summary`
- `deliverables_summary`
- `limitations_summary`

### 句子级候选

系统先按段落切分，再按句号、分号、问号、叹号切成句子。展示摘要只从句子级候选中选择，不再直接展示整段正文。

### 跨字段互斥

字段按以下顺序选择：

1. 背景摘要
2. 痛点摘要
3. 创新点摘要
4. 交付物
5. 局限性

一句话被前面字段选中后，后续字段默认不能复用。若候选句与已选句的 token Jaccard 相似度过高，也会被跳过。

### 缺失时占位

如果材料没有高质量候选：

- 交付物显示：`当前材料中未明确给出交付物描述，待补充`
- 局限性显示：`当前材料中未明确给出局限性描述，待补充`

系统不会为了填满字段而复制痛点。

## 3. Verifier 检查

`app/verifier.py` 会检查：

- required fields。
- parse errors。
- empty docs。
- anchor 存在性。
- noisy output。
- suspicious long fields。
- repeated phrases。
- source coverage。
- unsupported claims。
- claim-evidence alignment。
- field duplication。
- summary quality warnings。

### 字段重复检查

检查字段对：

- 背景摘要 vs 痛点摘要
- 痛点摘要 vs 局限性
- 创新点摘要 vs 交付物
- 交付物 vs 局限性

如果相似度过高，写入：

- `field_duplication`
- `duplicated_field_pairs`

### 摘要质量检查

如果交付物里出现大量算法训练术语，如：

- Backbone
- TriHard
- Batch Size
- 数据增强
- 训练过程

则写入 `summary_quality_warnings`。

## 4. 测试

运行：

```powershell
python -m pytest -q
```

当前测试环境已固定到项目内可控临时目录，不再依赖系统 Temp 路径，避免 Windows 权限差异导致 `tmp_path` 相关用例不稳定。

当前覆盖内容包括：

- parser 读取 md/pdf。
- parser 读取 docx/pptx。
- extractor 输出通用项目名。
- retriever 返回非空 evidence。
- generator fallback 输出字符串。
- llm_client 未配置 key 时不崩溃。
- verifier 返回 dict 且包含 `passed`。
- runall 输出 intro/innovation/defense/readme。
- generate 在材料变化后会重新抽取。
- session 工作区隔离。
- project name 不混入作者和摘要。
- claim-evidence alignment 报告。
- 本地工具注册和文件检索。
- display_summaries 存在。
- 背景和痛点不能完全一样。
- 局限性不能直接等于痛点。
- 交付物不能明显包含大量训练细节术语。
- 缺失局限性时显示“待补充”。
- verifier 能报告字段重复和摘要质量问题。

最近验证结果：

```text
23 passed
```
