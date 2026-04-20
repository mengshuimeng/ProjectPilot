from __future__ import annotations

from typing import Any

from app.chunker import chunk_text, split_paragraphs
from app.extractor import clean_document_text, is_noise_paragraph, normalize_text


TASK_KEYWORDS = {
    "intro": [
        "背景",
        "痛点",
        "问题",
        "用户",
        "对象",
        "技术",
        "项目",
        "目标",
        "场景",
        "background",
        "pain",
        "user",
    ],
    "innovation": [
        "创新",
        "亮点",
        "优势",
        "架构",
        "成果",
        "交付",
        "Harness",
        "证据",
        "校验",
        "重试",
        "innovation",
        "deliverable",
    ],
    "defense": [
        "背景",
        "痛点",
        "方案",
        "架构",
        "模块",
        "实验",
        "结果",
        "不足",
        "Harness",
        "答辩",
        "workflow",
        "architecture",
    ],
    "readme": [
        "项目名称",
        "项目类型",
        "技术",
        "架构",
        "使用",
        "运行",
        "功能",
        "安装",
        "Harness",
        "README",
        "usage",
    ],
}

TASK_FIELD_PREFERENCES = {
    "intro": ["background", "pain_points", "target_users", "core_technologies"],
    "innovation": ["innovation_points", "system_architecture", "deliverables", "future_work"],
    "defense": [
        "background",
        "pain_points",
        "system_architecture",
        "system_modules",
        "experiment_results",
        "limitations",
        "innovation_points",
    ],
    "readme": [
        "project_type",
        "project_name",
        "core_technologies",
        "system_architecture",
        "deliverables",
        "future_work",
    ],
}


def _role_weight(role: str) -> float:
    return 2.4 if role == "anchor" else 1.0


def _supporting_bonus(task: str, text: str) -> float:
    lower = text.lower()
    bonus = 0.0
    if task == "intro" and any(token in lower for token in ["简介", "概述", "readme"]):
        bonus += 0.8
    if task == "innovation" and any(token in lower for token in ["harness", "校验", "证据", "重试", "亮点"]):
        bonus += 1.2
    if task == "defense" and any(token in lower for token in ["ppt", "答辩", "总结", "成果"]):
        bonus += 1.0
    if task == "readme" and any(token in lower for token in ["安装", "运行", "使用", "readme", "cli"]):
        bonus += 1.0
    return bonus


def _keyword_score(text: str, keywords: list[str]) -> float:
    lower = text.lower()
    return float(sum(lower.count(keyword.lower()) for keyword in keywords))


def _length_penalty(text: str) -> float:
    length = len(text)
    if length < 35:
        return 0.5
    if length > 1000:
        return 0.62
    if length > 700:
        return 0.82
    return 1.0


def _make_candidate(
    source: str,
    role: str,
    text: str,
    task: str,
    origin: str,
    field: str = "",
) -> dict[str, Any]:
    normalized = normalize_text(text)
    score = _keyword_score(normalized, TASK_KEYWORDS.get(task, [])) * _role_weight(role) * _length_penalty(normalized)
    if field and field in TASK_FIELD_PREFERENCES.get(task, []):
        score += 1.5 * _role_weight(role)
    if role == "supporting":
        score += _supporting_bonus(task, normalized)
    if "Harness" in normalized and task in {"innovation", "defense", "readme"}:
        score += 1.0
    return {
        "source": source,
        "role": role,
        "text": normalized,
        "score": round(score, 3),
        "origin": origin,
        "field": field,
    }


def retrieve_evidence(
    task: str,
    profile: dict[str, Any],
    docs: list[dict[str, Any]],
    limit: int = 10,
) -> dict[str, Any]:
    task = task.lower()
    if task not in TASK_KEYWORDS:
        raise ValueError(f"Unsupported evidence task: {task}")

    source_roles = profile.get("source_roles", {})
    candidates: list[dict[str, Any]] = []

    for field in TASK_FIELD_PREFERENCES.get(task, []):
        field_value = profile.get(field)
        if isinstance(field_value, list):
            field_value = "、".join(str(item) for item in field_value)
        if isinstance(field_value, str) and field_value.strip():
            candidates.append(
                _make_candidate(
                    source="profile",
                    role="anchor",
                    text=field_value,
                    task=task,
                    origin="profile",
                    field=field,
                )
            )
        for item in profile.get("field_sources", {}).get(field, []):
            text = str(item.get("text", ""))
            source = str(item.get("source", "profile"))
            role = str(item.get("role") or source_roles.get(source, "supporting"))
            if text and not is_noise_paragraph(text):
                candidates.append(_make_candidate(source, role, text, task, "profile", field))

    for doc in docs:
        source = str(doc.get("name", ""))
        role = str(doc.get("role", source_roles.get(source, "supporting")))
        if doc.get("parse_status") in {"unsupported", "parse_warning"} and not doc.get("text"):
            continue
        cleaned_text = clean_document_text(str(doc.get("text", "")))
        paragraphs = split_paragraphs(cleaned_text)
        if not paragraphs and cleaned_text:
            paragraphs = chunk_text(cleaned_text, max_chars=750, overlap=90)
        for paragraph in paragraphs:
            if is_noise_paragraph(paragraph):
                continue
            chunk = paragraph if len(paragraph) <= 900 else paragraph[:900]
            candidate = _make_candidate(source, role, chunk, task, "document")
            if candidate["score"] > 0:
                candidates.append(candidate)

    candidates.sort(key=lambda item: (item["score"], item.get("role") == "anchor"), reverse=True)

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    # Ensure the anchor is represented whenever possible.
    anchor_candidate = next((item for item in candidates if item.get("role") == "anchor" and item["source"] != "profile"), None)
    if anchor_candidate:
        selected.append(anchor_candidate)
        seen.add((anchor_candidate["source"], anchor_candidate["text"][:140]))

    for candidate in candidates:
        key = (candidate["source"], candidate["text"][:140])
        if key in seen:
            continue
        selected.append(candidate)
        seen.add(key)
        if len(selected) >= limit:
            break

    role_summary = {
        role: sum(1 for chunk in selected if chunk.get("role") == role)
        for role in ("anchor", "supporting")
    }
    source_summary = {
        source: sum(1 for chunk in selected if chunk.get("source") == source)
        for source in sorted({chunk.get("source", "") for chunk in selected})
    }

    return {
        "task": task,
        "session_id": profile.get("session_id", ""),
        "anchor_document": profile.get("anchor_document", ""),
        "query_keywords": TASK_KEYWORDS[task],
        "chunks": selected,
        "role_summary": role_summary,
        "source_summary": source_summary,
    }


def retrieve_relevant_paragraphs(
    docs: list[dict[str, Any]],
    query_keywords: list[str],
    limit: int = 5,
) -> list[dict[str, str]]:
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
