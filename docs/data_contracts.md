# 数据契约

本文档说明 ProjectPilot V2 主要 JSON 产物的字段含义，便于调试、Demo 和后续开发。

## documents.json

路径：

```text
data/processed/documents.json
data/sessions/{session_id}/processed/documents.json
```

结构：

```json
{
  "documents": [
    {
      "name": "main.pdf",
      "suffix": ".pdf",
      "path": "...",
      "text": "清洗后的正文",
      "char_count": 1234,
      "raw_char_count": 1500,
      "paragraph_count": 20,
      "parse_status": "parsed",
      "parse_warning": "",
      "role": "anchor"
    }
  ]
}
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `name` | 文件名 |
| `suffix` | 文件后缀 |
| `path` | 文件路径 |
| `text` | 解析并清洗后的文本 |
| `char_count` | 清洗后字符数 |
| `raw_char_count` | 原始解析字符数 |
| `paragraph_count` | 段落数量 |
| `parse_status` | `parsed`、`empty`、`unsupported`、`parse_error`、`parse_warning` |
| `parse_warning` | 解析提示或兼容格式失败原因 |
| `role` | `anchor` 或 `supporting` |

## profile.json

路径：

```text
data/processed/profile.json
data/sessions/{session_id}/processed/profile.json
```

主要字段：

```json
{
  "anchor_document": "main.pdf",
  "supporting_documents": ["slides.pptx"],
  "source_roles": {
    "main.pdf": "anchor",
    "slides.pptx": "supporting"
  },
  "project_name": "示例项目",
  "project_type": "通用项目",
  "background": "...",
  "pain_points": "...",
  "target_users": "...",
  "core_technologies": ["Python", "Streamlit"],
  "system_architecture": "...",
  "system_modules": ["文档解析", "证据检索"],
  "innovation_points": "...",
  "experiment_results": "...",
  "deliverables": "...",
  "limitations": "...",
  "future_work": "...",
  "field_sources": {},
  "field_candidates": {},
  "display_summaries": {},
  "display_summary_sources": {},
  "raw_field_values": {},
  "doc_stats": []
}
```

### display_summaries

UI 默认展示 `display_summaries`，不直接展示 raw 字段。

```json
{
  "display_summaries": {
    "background_summary": "...",
    "pain_points_summary": "...",
    "innovation_summary": "...",
    "deliverables_summary": "...",
    "limitations_summary": "..."
  }
}
```

这样可以避免背景、痛点、创新点、交付物和局限性互相复制。

### field_candidates

`field_candidates` 保留句子级候选，供 verifier、UI 来源折叠区和调试使用。

```json
{
  "field_candidates": {
    "background_candidates": [],
    "pain_point_candidates": [],
    "innovation_candidates": [],
    "deliverable_candidates": [],
    "limitation_candidates": []
  }
}
```

每个候选包含：

```json
{
  "source": "main.pdf",
  "role": "anchor",
  "text": "候选句",
  "score": 7.8
}
```

## evidence.json

路径：

```text
outputs/{task}_evidence.json
data/sessions/{session_id}/outputs/{task}_evidence.json
```

结构：

```json
{
  "task": "defense",
  "session_id": "",
  "anchor_document": "main.pdf",
  "query_keywords": ["背景", "痛点"],
  "chunks": [
    {
      "source": "main.pdf",
      "role": "anchor",
      "text": "证据块文本",
      "score": 2.4,
      "origin": "document",
      "field": ""
    }
  ],
  "role_summary": {
    "anchor": 6,
    "supporting": 2
  },
  "source_summary": {
    "main.pdf": 6,
    "slides.pptx": 2
  }
}
```

## meta.json

路径：

```text
outputs/{task}_meta.json
data/sessions/{session_id}/outputs/{task}_meta.json
```

主要字段：

```json
{
  "task": "defense",
  "session_id": "",
  "generation_mode": "llm",
  "fallback_reason": "",
  "used_sources": ["main.pdf"],
  "used_roles": ["anchor"],
  "anchor_document": "main.pdf",
  "warnings_before_retry": [],
  "retry_used": false,
  "notes": [],
  "paths": {},
  "initial_verify_report": {},
  "final_verify_report": {}
}
```

## verify_report.json

路径：

```text
data/processed/verify_report.json
data/sessions/{session_id}/processed/verify_report.json
```

主要字段：

```json
{
  "passed": true,
  "warnings": [],
  "infos": [],
  "missing_fields": [],
  "parse_errors": [],
  "empty_docs": [],
  "noisy_output": [],
  "suspicious_long_fields": [],
  "field_duplication": {},
  "duplicated_field_pairs": [],
  "summary_quality_warnings": [],
  "repeated_phrases": [],
  "unsupported_claims": [],
  "claim_evidence_alignment": {},
  "source_coverage_summary": {},
  "anchor_document": "main.pdf",
  "supporting_document_count": 1,
  "parse_warnings_summary": [],
  "project_name_candidates": []
}
```

