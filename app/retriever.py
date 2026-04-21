from __future__ import annotations

import math
import re
from collections import Counter
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

TASK_QUERY_HINTS = {
    "intro": "项目简介 背景 痛点 目标用户 核心技术 使用场景 项目价值",
    "innovation": "创新点 技术亮点 架构优势 交付成果 校验闭环 证据治理 Harness",
    "defense": "答辩 背景 痛点 方案 架构 模块 实验结果 局限性 反馈闭环 Harness",
    "readme": "README 项目类型 项目名称 核心技术 系统架构 使用方法 交付成果",
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


def _tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    base_tokens = re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{1,}|[\u4e00-\u9fff]{2,}", normalized)
    compact = re.sub(r"\s+", "", normalized.lower())
    chargrams = [compact[index : index + 2] for index in range(max(0, len(compact) - 1))]
    tokens = [token.lower() for token in base_tokens if token.strip()]
    tokens.extend(chargram for chargram in chargrams if chargram.strip())
    return tokens


def _tf(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def _idf(texts: list[str]) -> dict[str, float]:
    document_count = max(1, len(texts))
    df: Counter[str] = Counter()
    for text in texts:
        df.update(set(_tokenize(text)))
    return {token: math.log((1 + document_count) / (1 + count)) + 1.0 for token, count in df.items()}


def _tfidf_vector(text: str, idf: dict[str, float]) -> dict[str, float]:
    counter = _tf(_tokenize(text))
    if not counter:
        return {}
    max_freq = max(counter.values())
    return {token: (freq / max_freq) * idf.get(token, 1.0) for token, freq in counter.items()}


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    if not numerator:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _build_query_text(task: str, profile: dict[str, Any]) -> str:
    parts = [
        TASK_QUERY_HINTS.get(task, ""),
        " ".join(TASK_KEYWORDS.get(task, [])),
        " ".join(TASK_FIELD_PREFERENCES.get(task, [])),
        str(profile.get("project_name", "")),
        str(profile.get("project_type", "")),
    ]
    for field in TASK_FIELD_PREFERENCES.get(task, []):
        value = profile.get(field)
        if isinstance(value, list):
            value = " ".join(str(item) for item in value[:8])
        parts.append(str(value or ""))
    return normalize_text(" ".join(part for part in parts if part))


def _make_candidate(
    source: str,
    role: str,
    text: str,
    task: str,
    origin: str,
    field: str = "",
) -> dict[str, Any]:
    normalized = normalize_text(text)
    keyword_score = _keyword_score(normalized, TASK_KEYWORDS.get(task, []))
    heuristic = keyword_score * _length_penalty(normalized)
    if field and field in TASK_FIELD_PREFERENCES.get(task, []):
        heuristic += 1.5
    if role == "supporting":
        heuristic += _supporting_bonus(task, normalized)
    if "Harness" in normalized and task in {"innovation", "defense", "readme"}:
        heuristic += 1.0
    return {
        "source": source,
        "role": role,
        "text": normalized,
        "score": 0.0,
        "origin": origin,
        "field": field,
        "keyword_score": round(keyword_score, 3),
        "semantic_score": 0.0,
        "jaccard_score": 0.0,
        "heuristic_score": round(heuristic, 3),
    }


def _score_candidates(candidates: list[dict[str, Any]], task: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    query_text = _build_query_text(task, profile)
    corpus = [query_text] + [str(candidate.get("text", "")) for candidate in candidates]
    idf = _idf(corpus)
    query_vector = _tfidf_vector(query_text, idf)

    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        text = str(candidate.get("text", ""))
        semantic_score = _cosine_similarity(_tfidf_vector(text, idf), query_vector)
        jaccard_score = _jaccard_similarity(text, query_text)
        role_weight = _role_weight(str(candidate.get("role", "supporting")))
        field_bonus = 0.8 if candidate.get("field") in TASK_FIELD_PREFERENCES.get(task, []) else 0.0
        final_score = (
            float(candidate.get("heuristic_score", 0.0)) * role_weight
            + semantic_score * 4.0
            + jaccard_score * 1.8
            + field_bonus
        )
        enriched = dict(candidate)
        enriched["semantic_score"] = round(semantic_score, 4)
        enriched["jaccard_score"] = round(jaccard_score, 4)
        enriched["score"] = round(final_score, 4)
        enriched["retrieval_mode"] = "hybrid_lexical_semantic"
        scored.append(enriched)
    return scored


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
            if candidate["keyword_score"] > 0 or len(chunk) >= 80:
                candidates.append(candidate)

    candidates = _score_candidates(candidates, task, profile)
    candidates.sort(key=lambda item: (item["score"], item.get("role") == "anchor"), reverse=True)

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    anchor_candidate = next((item for item in candidates if item.get("role") == "anchor" and item["source"] != "profile"), None)
    if anchor_candidate:
        selected.append(anchor_candidate)
        seen.add((anchor_candidate["source"], anchor_candidate["text"][:140]))

    for candidate in candidates:
        key = (candidate["source"], candidate["text"][:140])
        if key in seen:
            continue
        if any(_jaccard_similarity(candidate["text"], item["text"]) > 0.72 for item in selected):
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
        "query_text": _build_query_text(task, profile),
        "retrieval_mode": "hybrid_lexical_semantic",
        "chunks": selected,
        "role_summary": role_summary,
        "source_summary": source_summary,
        "semantic_index_summary": {
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "anchor_priority": True,
            "supports_cross_document_semantic_index": True,
        },
    }


def retrieve_relevant_paragraphs(
    docs: list[dict[str, Any]],
    query_keywords: list[str],
    limit: int = 5,
) -> list[dict[str, str]]:
    query_text = " ".join(query_keywords)
    corpus = [query_text]
    paragraphs: list[dict[str, str]] = []
    for doc in docs:
        source = str(doc.get("name", ""))
        for paragraph in split_paragraphs(clean_document_text(str(doc.get("text", "")))):
            if is_noise_paragraph(paragraph):
                continue
            text = normalize_text(paragraph)
            paragraphs.append({"source": source, "text": text})
            corpus.append(text)

    idf = _idf(corpus)
    query_vector = _tfidf_vector(query_text, idf)
    candidates: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        text = paragraph["text"]
        score = _keyword_score(text, query_keywords) + _cosine_similarity(_tfidf_vector(text, idf), query_vector) * 3.0
        if score > 0:
            candidates.append({"source": paragraph["source"], "text": text, "score": round(score, 4)})

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return [
        {"source": str(item.get("source", "")), "text": str(item.get("text", ""))}
        for item in candidates[:limit]
    ]
