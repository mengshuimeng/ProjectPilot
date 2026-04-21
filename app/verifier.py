from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Any

from app.extractor import CANONICAL_PROJECT_NAME, is_known_project_alias, is_noise_paragraph, normalize_text

REQUIRED_FIELDS = [
    "project_name",
    "project_type",
    "background",
    "pain_points",
    "core_technologies",
]

CLAIM_TERMS = [
    "YOLOv8",
    "PCBNet",
    "ResNet50",
    "Flask",
    "Vue",
    "ECharts",
    "mAP",
    "Rank-1",
    "准确率",
    "精度",
    "召回率",
    "实时",
    "部署",
    "一键",
    "自动",
    "支持",
    "达到",
    "提升",
]

SUMMARY_FIELD_PAIRS = [
    ("background_summary", "pain_points_summary"),
    ("pain_points_summary", "limitations_summary"),
    ("innovation_summary", "deliverables_summary"),
    ("deliverables_summary", "limitations_summary"),
]

SUMMARY_LABELS = {
    "background_summary": "背景摘要",
    "pain_points_summary": "痛点摘要",
    "innovation_summary": "创新点摘要",
    "deliverables_summary": "交付物",
    "limitations_summary": "局限性",
}

TRAINING_DETAIL_TERMS = [
    "Backbone",
    "TriHard",
    "Batch Size",
    "batch size",
    "数据增强",
    "训练过程",
    "学习率",
    "epoch",
    "损失函数",
    "Neck",
    "Head",
]


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _summary_text(profile: dict[str, Any], summary_key: str) -> str:
    display = profile.get("display_summaries") or {}
    if isinstance(display, dict) and display.get(summary_key):
        return str(display.get(summary_key, ""))
    fallback = {
        "background_summary": profile.get("background") or profile.get("background_summary"),
        "pain_points_summary": profile.get("pain_points") or profile.get("pain_point_summary"),
        "innovation_summary": profile.get("innovation_points") or profile.get("innovation_summary"),
        "deliverables_summary": profile.get("deliverables") or profile.get("deliverables_summary"),
        "limitations_summary": profile.get("limitations") or profile.get("limitations_summary"),
    }
    return str(fallback.get(summary_key) or "")


def _summary_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{1,}|[\u4e00-\u9fff]{2,}", text))
    compact = re.sub(r"\s+", "", text)
    if len(tokens) < 3:
        tokens.update(compact[index : index + 2] for index in range(max(0, len(compact) - 1)))
    return {token.lower() for token in tokens if token.strip()}


def _summary_similarity(left: str, right: str) -> float:
    left_tokens = _summary_tokens(left)
    right_tokens = _summary_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _check_field_duplication(profile: dict[str, Any]) -> dict[str, Any]:
    duplicated_pairs: list[dict[str, Any]] = []
    quality_warnings: list[str] = []
    summaries = {field: _summary_text(profile, field).strip() for field, _ in SUMMARY_FIELD_PAIRS}
    summaries.update({right: _summary_text(profile, right).strip() for _, right in SUMMARY_FIELD_PAIRS})

    for left, right in SUMMARY_FIELD_PAIRS:
        left_text = summaries.get(left, "")
        right_text = summaries.get(right, "")
        if not left_text or not right_text or "待补充" in left_text or "待补充" in right_text:
            continue
        similarity = _summary_similarity(left_text, right_text)
        if similarity > 0.6 or left_text == right_text:
            duplicated_pairs.append(
                {
                    "left": left,
                    "right": right,
                    "left_label": SUMMARY_LABELS[left],
                    "right_label": SUMMARY_LABELS[right],
                    "similarity": round(similarity, 3),
                }
            )

    deliverables_text = summaries.get("deliverables_summary", "")
    training_hits = [term for term in TRAINING_DETAIL_TERMS if term.lower() in deliverables_text.lower()]
    if len(training_hits) >= 2:
        quality_warnings.append(
            "交付物摘要疑似抽到了算法训练细节，而不是成果/产出/系统/论文/专利等交付内容。"
        )

    pain_text = summaries.get("pain_points_summary", "")
    limitation_text = summaries.get("limitations_summary", "")
    if pain_text and limitation_text and "待补充" not in limitation_text and _summary_similarity(pain_text, limitation_text) > 0.55:
        quality_warnings.append("局限性摘要与痛点摘要高度相似，可能存在字段复用。")

    return {
        "duplicated_field_pairs": duplicated_pairs,
        "summary_quality_warnings": quality_warnings,
        "ok": not duplicated_pairs and not quality_warnings,
    }


def _find_noisy_output(output_text: str) -> list[str]:
    noisy: list[str] = []
    for line in output_text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = line.strip()
        if stripped and is_noise_paragraph(stripped):
            noisy.append(stripped[:120])
    return list(dict.fromkeys(noisy))


def _find_repeated_phrases(output_text: str) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[。！？!\?\n]+", output_text)
        if len(sentence.strip()) >= 14
    ]
    counter = Counter(sentences)
    return [sentence for sentence, count in counter.items() if count > 1]


def _find_suspicious_long_fields(profile: dict[str, Any]) -> list[dict[str, Any]]:
    suspicious: list[dict[str, Any]] = []
    for field in [
        "background",
        "pain_points",
        "system_architecture",
        "innovation_points",
        "experiment_results",
        "deliverables",
        "limitations",
        "future_work",
    ]:
        value = str(profile.get(field, ""))
        if len(value) > 900:
            suspicious.append({"field": field, "length": len(value)})
        if value and _find_noisy_output(value):
            suspicious.append({"field": field, "issue": "contains_noisy_text"})
    return suspicious


def _parse_warnings_summary(docs: list[dict[str, Any]]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for doc in docs:
        if doc.get("parse_warning"):
            warnings.append(
                {
                    "file": str(doc.get("name", "")),
                    "role": str(doc.get("role", "supporting")),
                    "status": str(doc.get("parse_status", "")),
                    "warning": str(doc.get("parse_warning", "")),
                }
            )
    return warnings


def _source_coverage(
    output_text: str,
    evidence: dict[str, Any] | None,
    used_sources: list[str] | None,
    used_roles: list[str] | None,
    task: str | None,
) -> dict[str, Any]:
    evidence_sources = []
    evidence_roles = []
    if evidence:
        evidence_sources = [
            str(chunk.get("source", ""))
            for chunk in evidence.get("chunks", [])
            if chunk.get("source")
        ]
        evidence_roles = [
            str(chunk.get("role", ""))
            for chunk in evidence.get("chunks", [])
            if chunk.get("role")
        ]
    evidence_sources = list(dict.fromkeys(evidence_sources))
    evidence_roles = list(dict.fromkeys(evidence_roles))
    used = list(dict.fromkeys(used_sources or []))
    roles = list(dict.fromkeys(used_roles or []))
    covered = [source for source in used if source in evidence_sources]
    minimum = 2 if task in {"defense", "innovation", "readme"} and len(evidence_sources) >= 2 else 1
    if len(output_text) < 80:
        minimum = 0
    anchor_used = "anchor" in roles or (not roles and "anchor" in evidence_roles)
    supporting_count = sum(1 for role in evidence_roles if role == "supporting")
    anchor_count = sum(1 for role in evidence_roles if role == "anchor")
    return {
        "task": task or "",
        "evidence_sources": evidence_sources,
        "evidence_roles": evidence_roles,
        "used_sources": used,
        "used_roles": roles,
        "covered_sources": covered,
        "covered_count": len(covered),
        "minimum_expected": minimum,
        "anchor_used": anchor_used,
        "anchor_chunk_count": anchor_count,
        "supporting_chunk_count": supporting_count,
        "over_rely_on_supporting": supporting_count > 0 and anchor_count == 0,
        "ok": len(covered) >= minimum and anchor_used,
    }


def _find_unsupported_claims(
    output_text: str,
    profile: dict[str, Any],
    evidence: dict[str, Any] | None,
) -> list[str]:
    support_text = _as_text(profile)
    evidence_chunks = list(evidence.get("chunks", [])) if evidence else []
    if evidence_chunks:
        support_text += "\n" + "\n".join(str(chunk.get("text", "")) for chunk in evidence_chunks)

    unsupported: list[str] = []
    for term in CLAIM_TERMS:
        if term.lower() in output_text.lower() and term.lower() not in support_text.lower():
            unsupported.append(term)

    for detail in _claim_evidence_alignment(output_text, profile, evidence).get("weak_claims", []):
        claim = str(detail.get("claim", "")).strip()
        if claim:
            unsupported.append(claim[:80])
    return list(dict.fromkeys(unsupported))


def _claim_keywords(sentence: str) -> set[str]:
    keywords = set()
    for token in CLAIM_TERMS:
        if token.lower() in sentence.lower():
            keywords.add(token.lower())
    for token in re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{2,}|[\u4e00-\u9fff]{2,}", sentence):
        if len(token) >= 2:
            keywords.add(token.lower())
    return keywords


def _claim_token_counter(text: str) -> Counter[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{1,}|[\u4e00-\u9fff]{2,}", normalized)
    compact = re.sub(r"\s+", "", normalized.lower())
    chargrams = [compact[index : index + 2] for index in range(max(0, len(compact) - 1))]
    return Counter(token.lower() for token in [*tokens, *chargrams] if token.strip())


def _cosine_counter_similarity(left: Counter[str], right: Counter[str]) -> float:
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


def _text_excerpt(text: str, max_chars: int = 140) -> str:
    compact = normalize_text(text)
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def _claim_sentences(output_text: str) -> list[str]:
    sentences = []
    claim_markers = ["实现", "支持", "采用", "达到", "提升", "降低", "优化", "准确", "实时", "自动", "识别", "检测", "部署", "%", "ms", "秒"]
    for sentence in re.split(r"[。！？!\?\n]+", output_text):
        text = sentence.strip()
        if len(text) < 12:
            continue
        if any(marker in text for marker in claim_markers) or re.search(r"\d+(?:\.\d+)?\s*(?:%|ms|s|秒|h|小时)", text):
            sentences.append(text)
    return sentences[:24]


def _claim_evidence_alignment(output_text: str, profile: dict[str, Any], evidence: dict[str, Any] | None) -> dict[str, Any]:
    evidence_chunks = list(evidence.get("chunks", [])) if evidence else []
    checked: list[dict[str, Any]] = []
    weak: list[dict[str, Any]] = []
    strong: list[dict[str, Any]] = []
    for sentence in _claim_sentences(output_text):
        sentence_terms = _claim_keywords(sentence)
        sentence_counter = _claim_token_counter(sentence)
        best_overlap = 0
        best_semantic = 0.0
        best_score = 0.0
        best_source = ""
        best_excerpt = ""
        best_role = ""
        for chunk in evidence_chunks:
            chunk_text = str(chunk.get("text", ""))
            overlap = sentence_terms & _claim_keywords(chunk_text)
            semantic = _cosine_counter_similarity(sentence_counter, _claim_token_counter(chunk_text))
            score = len(overlap) * 0.7 + semantic * 3.2
            if score > best_score:
                best_score = score
                best_overlap = len(overlap)
                best_semantic = semantic
                best_source = str(chunk.get("source", ""))
                best_role = str(chunk.get("role", ""))
                best_excerpt = _text_excerpt(chunk_text)
        detail = {
            "claim": sentence[:160],
            "best_overlap": best_overlap,
            "best_semantic_similarity": round(best_semantic, 4),
            "support_score": round(best_score, 4),
            "best_source": best_source,
            "best_role": best_role,
            "best_evidence_excerpt": best_excerpt,
        }
        is_supported = best_overlap >= 2 or best_semantic >= 0.34 or best_score >= 1.15
        if not is_supported:
            weak.append(detail)
        else:
            strong.append(detail)
        checked.append(detail)

    total = len(checked)
    supported = len(strong)
    return {
        "checked_count": total,
        "supported_count": supported,
        "weak_claims": weak,
        "supported_claims": strong[:12],
        "support_ratio": round((supported / total), 4) if total else 1.0,
        "ok": total == 0 or supported / total >= 0.72,
        "details": checked[:12],
    }


def _check_alias_conflict(profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    infos: list[str] = []
    warnings: list[str] = []
    candidates = profile.get("project_name_candidates") or profile.get("_project_name_candidates") or []
    unknown = []

    for candidate in candidates:
        candidate_text = str(candidate)
        if not candidate_text:
            continue
        if candidate_text == CANONICAL_PROJECT_NAME or is_known_project_alias(candidate_text):
            if candidate_text != CANONICAL_PROJECT_NAME:
                infos.append(f"已识别项目名称别名并归一化：{candidate_text}")
        else:
            unknown.append(candidate_text)

    if len(list(dict.fromkeys(unknown))) > 3:
        warnings.append(f"发现多个未登记项目名称候选，请确认：{', '.join(list(dict.fromkeys(unknown))[:5])}")
    elif unknown:
        infos.append(f"发现项目名称候选：{', '.join(list(dict.fromkeys(unknown))[:3])}")
    return infos, warnings


def verify_profile(
    profile: dict[str, Any],
    docs: list[dict[str, Any]],
    output_text: str = "",
    evidence: dict[str, Any] | None = None,
    used_sources: list[str] | None = None,
    used_roles: list[str] | None = None,
    task: str | None = None,
) -> dict[str, Any]:
    missing_fields = [field for field in REQUIRED_FIELDS if _is_empty(profile.get(field))]

    anchor_docs = [doc for doc in docs if doc.get("role") == "anchor"]
    anchor_document = profile.get("anchor_document") or (anchor_docs[0].get("name", "") if anchor_docs else "")
    supporting_count = len([doc for doc in docs if doc.get("role") == "supporting"])
    anchor_missing = not anchor_document or not anchor_docs

    parse_errors = []
    empty_docs = []
    for doc in docs:
        status = str(doc.get("parse_status", ""))
        if status == "parse_error":
            parse_errors.append({"file": doc.get("name", ""), "warning": doc.get("parse_warning", "")})
        if int(doc.get("char_count", 0)) == 0 and doc.get("role") == "anchor":
            empty_docs.append(str(doc.get("name", "")))

    parse_warnings_summary = _parse_warnings_summary(docs)
    noisy_output = _find_noisy_output(output_text) if output_text else []
    suspicious_long_fields = _find_suspicious_long_fields(profile)
    field_duplication = _check_field_duplication(profile)
    repeated_phrases = _find_repeated_phrases(output_text) if output_text else []
    source_coverage_summary = _source_coverage(output_text, evidence, used_sources, used_roles, task)
    unsupported_claims = _find_unsupported_claims(output_text, profile, evidence) if output_text else []
    claim_evidence_alignment = _claim_evidence_alignment(output_text, profile, evidence) if output_text else {
        "checked_count": 0,
        "supported_count": 0,
        "weak_claims": [],
        "ok": True,
        "details": [],
    }
    alias_infos, alias_warnings = _check_alias_conflict(profile)

    warnings: list[str] = []
    infos: list[str] = alias_infos

    if anchor_missing:
        warnings.append("缺少 anchor document，无法建立主事实来源。")
    if empty_docs:
        warnings.append(f"anchor 文档为空或未成功解析：{', '.join(empty_docs)}")
    if parse_errors:
        warnings.append("存在解析失败文件。")
    if parse_warnings_summary:
        infos.append(f"存在 {len(parse_warnings_summary)} 条解析提示，详见 parse_warnings_summary。")
    if noisy_output:
        warnings.append("生成结果疑似混入目录、页眉页脚、章节号、页码或公式残片。")
    if suspicious_long_fields:
        warnings.append("部分 profile 字段过长或疑似混入脏文本。")
    if field_duplication["duplicated_field_pairs"]:
        warnings.append("项目画像展示摘要存在字段间高度重复，请检查抽取结果。")
    if field_duplication["summary_quality_warnings"]:
        warnings.extend(field_duplication["summary_quality_warnings"])
    if repeated_phrases:
        warnings.append("生成结果存在重复句子或拼接痕迹。")
    if output_text and not source_coverage_summary["ok"]:
        warnings.append("生成结果来源覆盖不足，或未使用 anchor 证据。")
    if source_coverage_summary.get("over_rely_on_supporting"):
        warnings.append("evidence 过度依赖 supporting documents，未体现 anchor 优先。")
    if unsupported_claims:
        warnings.append(f"生成结果包含证据中未支撑的关键声明：{', '.join(unsupported_claims)}")
    if output_text and not claim_evidence_alignment["ok"]:
        warnings.append("生成结果存在较多缺少直接证据重叠的声明，请检查 claim-evidence 对齐。")
    warnings.extend(alias_warnings)

    if not missing_fields:
        infos.append("通用项目画像必填字段已覆盖。")
    if anchor_document:
        infos.append(f"anchor document: {anchor_document}")
    if supporting_count:
        infos.append(f"supporting documents: {supporting_count} 个")
    if output_text and not noisy_output:
        infos.append("生成结果未发现明显脏文本。")
    if output_text and source_coverage_summary["ok"]:
        infos.append("生成结果来源角色与覆盖满足轻量检查。")

    passed = not missing_fields and not parse_errors and not noisy_output and not anchor_missing and not empty_docs

    return {
        "passed": passed,
        "warnings": list(dict.fromkeys(warnings)),
        "infos": list(dict.fromkeys(infos)),
        "missing_fields": missing_fields,
        "parse_errors": parse_errors,
        "empty_docs": empty_docs,
        "noisy_output": noisy_output,
        "suspicious_long_fields": suspicious_long_fields,
        "field_duplication": field_duplication,
        "duplicated_field_pairs": field_duplication["duplicated_field_pairs"],
        "summary_quality_warnings": field_duplication["summary_quality_warnings"],
        "repeated_phrases": repeated_phrases,
        "unsupported_claims": unsupported_claims,
        "claim_evidence_alignment": claim_evidence_alignment,
        "source_coverage_summary": source_coverage_summary,
        "anchor_document": anchor_document,
        "supporting_document_count": supporting_count,
        "parse_warnings_summary": parse_warnings_summary,
        "project_name_candidates": profile.get("project_name_candidates") or profile.get("_project_name_candidates") or [],
    }
