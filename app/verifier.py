from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from app.extractor import CANONICAL_PROJECT_NAME, is_known_project_alias, is_noise_paragraph

REQUIRED_FIELDS = [
    "project_name",
    "background_summary",
    "core_technologies",
    "system_modules",
]

REQUIRED_TERMS = ["YOLOv8", "PCBNet", "ResNet50"]

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
        "background_summary",
        "pain_point_summary",
        "innovation_summary",
        "experiment_summary",
        "application_scenarios",
    ]:
        value = str(profile.get(field, ""))
        if len(value) > 900:
            suspicious.append({"field": field, "length": len(value)})
    return suspicious


def _source_coverage(
    output_text: str,
    evidence: dict[str, Any] | None,
    used_sources: list[str] | None,
    task: str | None,
) -> dict[str, Any]:
    evidence_sources = []
    if evidence:
        evidence_sources = [
            str(chunk.get("source", ""))
            for chunk in evidence.get("chunks", [])
            if chunk.get("source")
        ]
    evidence_sources = list(dict.fromkeys(evidence_sources))
    used = list(dict.fromkeys(used_sources or []))
    covered = [source for source in used if source in evidence_sources]
    minimum = 2 if task in {"defense", "innovation", "readme"} else 1
    if len(output_text) < 80:
        minimum = 0
    return {
        "task": task or "",
        "evidence_sources": evidence_sources,
        "used_sources": used,
        "covered_sources": covered,
        "covered_count": len(covered),
        "minimum_expected": minimum,
        "ok": len(covered) >= minimum,
    }


def _find_unsupported_claims(
    output_text: str,
    profile: dict[str, Any],
    evidence: dict[str, Any] | None,
) -> list[str]:
    support_text = _as_text(profile)
    if evidence:
        support_text += "\n" + "\n".join(str(chunk.get("text", "")) for chunk in evidence.get("chunks", []))

    unsupported: list[str] = []
    for term in CLAIM_TERMS:
        if term.lower() in output_text.lower() and term.lower() not in support_text.lower():
            unsupported.append(term)
    return unsupported


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

    if unknown:
        warnings.append(f"发现未登记项目名称候选，请确认：{', '.join(list(dict.fromkeys(unknown))[:5])}")
    return infos, warnings


def verify_profile(
    profile: dict[str, Any],
    docs: list[dict[str, Any]],
    output_text: str = "",
    evidence: dict[str, Any] | None = None,
    used_sources: list[str] | None = None,
    task: str | None = None,
) -> dict[str, Any]:
    missing_fields = [field for field in REQUIRED_FIELDS if _is_empty(profile.get(field))]

    parse_errors = []
    empty_docs = []
    for doc in docs:
        text = str(doc.get("text", ""))
        if text.startswith("[PDF_PARSE_ERROR]"):
            parse_errors.append({"file": doc.get("name", ""), "error": text})
        if int(doc.get("char_count", 0)) == 0:
            empty_docs.append(str(doc.get("name", "")))

    techs = profile.get("core_technologies", [])
    missing_terms = [term for term in REQUIRED_TERMS if term not in techs]

    field_sources = profile.get("field_sources") or {}
    fields_without_sources = [
        field
        for field in ["background_summary", "innovation_summary", "experiment_summary"]
        if not field_sources.get(field)
    ]

    noisy_output = _find_noisy_output(output_text) if output_text else []
    suspicious_long_fields = _find_suspicious_long_fields(profile)
    repeated_phrases = _find_repeated_phrases(output_text) if output_text else []
    source_coverage_summary = _source_coverage(output_text, evidence, used_sources, task)
    unsupported_claims = _find_unsupported_claims(output_text, profile, evidence) if output_text else []
    alias_infos, alias_warnings = _check_alias_conflict(profile)

    warnings: list[str] = []
    infos: list[str] = alias_infos

    if missing_terms:
        warnings.append(f"核心术语覆盖不完整：{', '.join(missing_terms)}")
    if fields_without_sources:
        warnings.append(f"以下关键字段缺少来源支撑：{', '.join(fields_without_sources)}")
    if empty_docs:
        warnings.append(f"以下文件为空或尚未替换为真实材料：{', '.join(empty_docs)}")
    if noisy_output:
        warnings.append("生成结果疑似混入目录、页眉页脚、章节号、页码或公式残片。")
    if suspicious_long_fields:
        warnings.append("部分 profile 字段过长，可能仍混入长段正文。")
    if repeated_phrases:
        warnings.append("生成结果存在重复句子或拼接痕迹。")
    if output_text and not source_coverage_summary["ok"]:
        warnings.append("生成结果来源覆盖不足。")
    if unsupported_claims:
        warnings.append(f"生成结果包含证据中未支撑的关键声明：{', '.join(unsupported_claims)}")
    warnings.extend(alias_warnings)

    if not missing_fields:
        infos.append("必填字段已覆盖。")
    if output_text and not noisy_output:
        infos.append("生成结果未发现明显脏文本。")
    if output_text and source_coverage_summary["ok"]:
        infos.append("生成结果来源覆盖满足轻量检查。")

    passed = not missing_fields and not parse_errors and not noisy_output

    return {
        "passed": passed,
        "warnings": list(dict.fromkeys(warnings)),
        "infos": list(dict.fromkeys(infos)),
        "missing_fields": missing_fields,
        "missing_terms": missing_terms,
        "parse_errors": parse_errors,
        "empty_docs": empty_docs,
        "noisy_output": noisy_output,
        "suspicious_long_fields": suspicious_long_fields,
        "repeated_phrases": repeated_phrases,
        "unsupported_claims": unsupported_claims,
        "fields_without_sources": fields_without_sources,
        "project_name_candidates": profile.get("project_name_candidates") or profile.get("_project_name_candidates") or [],
        "source_coverage_summary": source_coverage_summary,
    }
