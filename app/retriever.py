from __future__ import annotations

from typing import Any

from app.chunker import chunk_text, split_paragraphs
from app.extractor import clean_document_text, is_noise_paragraph, normalize_text


TASK_KEYWORDS = {
    "intro": [
        "ProjectPilot",
        "项目材料",
        "答辩",
        "README",
        "背景",
        "场景",
        "核心技术",
        "模块",
        "景区",
        "重识别",
    ],
    "innovation": [
        "创新",
        "Harness",
        "证据",
        "检索",
        "校验",
        "反馈闭环",
        "来源",
        "LLM",
        "prompt",
        "skills",
    ],
    "defense": [
        "痛点",
        "背景",
        "项目材料",
        "系统",
        "方案",
        "Harness",
        "外部工具",
        "校验",
        "答辩",
        "结果",
    ],
    "readme": [
        "ProjectPilot",
        "功能",
        "架构",
        "Harness",
        "运行",
        "环境变量",
        "CLI",
        "LLM",
    ],
}

TASK_FIELD_PREFERENCES = {
    "intro": ["background_summary", "application_scenarios", "pain_point_summary"],
    "innovation": ["innovation_summary", "pain_point_summary", "future_work"],
    "defense": [
        "background_summary",
        "pain_point_summary",
        "innovation_summary",
        "experiment_summary",
        "application_scenarios",
    ],
    "readme": ["background_summary", "pain_point_summary", "innovation_summary", "limitations"],
}

SOURCE_WEIGHTS = {
    "project_notes.md": 2.2,
    "README_source.md": 2.0,
    "ppt_outline.md": 1.6,
    "dachuang_application.pdf": 1.2,
    "reid_thesis.pdf": 0.75,
}


def _source_weight(source: str) -> float:
    return SOURCE_WEIGHTS.get(source, 1.0)


def _keyword_score(text: str, keywords: list[str]) -> float:
    lower = text.lower()
    return float(sum(lower.count(keyword.lower()) for keyword in keywords))


def _length_penalty(text: str) -> float:
    length = len(text)
    if length < 40:
        return 0.55
    if length > 900:
        return 0.65
    if length > 650:
        return 0.85
    return 1.0


def _make_candidate(source: str, text: str, task: str, origin: str, field: str = "") -> dict[str, Any]:
    keywords = TASK_KEYWORDS.get(task, [])
    normalized = normalize_text(text)
    score = _keyword_score(normalized, keywords) * _source_weight(source) * _length_penalty(normalized)
    if field and field in TASK_FIELD_PREFERENCES.get(task, []):
        score += 1.2
    if "ProjectPilot" in normalized and task in {"intro", "innovation", "defense", "readme"}:
        score += 1.0
    if "Harness" in normalized and task in {"innovation", "defense", "readme"}:
        score += 1.0
    return {
        "source": source,
        "text": normalized,
        "score": round(score, 3),
        "origin": origin,
        "field": field,
    }


def retrieve_evidence(
    task: str,
    profile: dict[str, Any],
    docs: list[dict[str, Any]],
    limit: int = 8,
) -> dict[str, Any]:
    task = task.lower()
    if task not in TASK_KEYWORDS:
        raise ValueError(f"Unsupported evidence task: {task}")

    candidates: list[dict[str, Any]] = []

    for field in TASK_FIELD_PREFERENCES.get(task, []):
        for item in profile.get("field_sources", {}).get(field, []):
            text = str(item.get("text", ""))
            source = str(item.get("source", "profile"))
            if text and not is_noise_paragraph(text):
                candidates.append(_make_candidate(source, text, task, "profile", field))

    for doc in docs:
        source = str(doc.get("name", ""))
        text = str(doc.get("text", ""))
        if "[PDF_PARSE_ERROR]" in text:
            continue
        cleaned_text = clean_document_text(text)
        paragraphs = split_paragraphs(cleaned_text)
        if not paragraphs and cleaned_text:
            paragraphs = chunk_text(cleaned_text, max_chars=650, overlap=80)
        for paragraph in paragraphs:
            if is_noise_paragraph(paragraph):
                continue
            chunk = paragraph if len(paragraph) <= 850 else paragraph[:850]
            candidate = _make_candidate(source, chunk, task, "document")
            if candidate["score"] > 0:
                candidates.append(candidate)

    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate["source"], candidate["text"][:120])
        if key in seen:
            continue
        selected.append(candidate)
        seen.add(key)
        if len(selected) >= limit:
            break

    return {
        "task": task,
        "query_keywords": TASK_KEYWORDS[task],
        "chunks": selected,
        "source_summary": {
            source: sum(1 for chunk in selected if chunk.get("source") == source)
            for source in sorted({chunk.get("source", "") for chunk in selected})
        },
    }


def retrieve_relevant_paragraphs(
    docs: list[dict[str, Any]],
    query_keywords: list[str],
    limit: int = 5,
) -> list[dict[str, str]]:
    """Compatibility wrapper for the original rule-based retriever API."""
    candidates: list[dict[str, Any]] = []
    for doc in docs:
        source = str(doc.get("name", ""))
        for paragraph in split_paragraphs(clean_document_text(str(doc.get("text", "")))):
            if is_noise_paragraph(paragraph):
                continue
            score = _keyword_score(paragraph, query_keywords)
            if score > 0:
                candidates.append({"source": source, "text": normalize_text(paragraph), "score": score})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return [
        {"source": str(item.get("source", "")), "text": str(item.get("text", ""))}
        for item in candidates[:limit]
    ]
