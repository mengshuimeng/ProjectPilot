# 后续路线图

ProjectPilot V2 当前已经可以完成课程作业所需的主要功能。以下是后续可继续优化的方向。

## 高优先级

### 1. OCR 支持

当前 PDF 解析依赖文本层。扫描版 PDF 或图片型材料可能无法抽取有效文本。

可选方案：

- 接入本地 OCR。
- 接入 PaddleOCR。
- 接入云 OCR API。
- 在 parser 中增加 OCR fallback。

### 2. 更强的 claim-evidence 对齐

当前 `claim_evidence_alignment` 是轻量关键词重叠检查。

后续可以升级为：

- 句向量相似度。
- NLI 判断。
- LLM judge。
- 引文级 evidence 标注。

### 3. 真正独立 MCP server

当前 `app/tool_registry.py` 是 MCP-ready 的本地工具层，但还不是独立 MCP server。

后续可以把以下能力封装为 MCP：

- 文件系统检索。
- Office 转换。
- OCR。
- 文档元数据读取。
- 本地缓存管理。

## 中优先级

### 4. UI session 导出

为每个 session 增加一键导出：

```text
session.zip
  raw/
  processed/
  outputs/
  session.json
```

这样方便提交作业或分享 Demo 结果。

### 5. 更细的项目类型识别

当前项目类型是规则判断，例如：

- 硬件 / IoT 项目
- AI / 算法项目
- Web / 软件系统
- 数据分析项目
- 课程/科研项目
- 通用项目

后续可以结合 LLM 或更细的规则，识别：

- 机器人项目。
- 智能制造项目。
- 计算机视觉项目。
- 管理信息系统。
- 移动端应用。
- 数据平台。

### 6. 更完善的 PPT 输出

当前生成内容包含 intro、innovation、defense、readme。

后续可以增加：

- PPT 大纲。
- 每页标题和讲稿。
- 答辩 Q&A。
- 项目亮点页。

## 低优先级

### 7. 向量检索

当前 evidence 检索是轻量关键词打分。对于大规模材料，可以考虑：

- 本地 embedding。
- FAISS。
- Chroma。
- 混合检索。

课程作业阶段暂不建议引入重量级依赖。

### 8. 多语言支持

当前 UI 和提示词主要使用中文。后续可以支持：

- 英文材料。
- 中英双语输出。
- 英文 README。

### 9. 更严格的隐私处理

后续可以增加：

- API key 检查和脱敏。
- 上传材料敏感字段提示。
- 输出前隐私信息扫描。

## 当前已知限制

- 扫描版 PDF 支持一般。
- 旧版 doc/ppt 取决于本地转换环境。
- unsupported claims 是轻量检查。
- evidence 检索不是语义向量检索。
- LLM 输出质量仍受提示词、材料质量和模型能力影响。

