from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.extractor import is_noise_paragraph, normalize_text, strip_outline_markers
from app.llm_client import LLMClient, get_llm_status


TASK_PROMPTS = {
    "intro": "intro_generator.md",
    "innovation": "innovation_generator.md",
    "defense": "defense_generator.md",
    "readme": "readme_generator.md",
}

JSON_SCHEMA_HINT = {
    "content": "生成的 Markdown 或正文内容",
    "used_sources": ["anchor.pdf", "supporting.md"],
    "used_roles": ["anchor", "supporting"],
    "notes": ["简要说明如何使用证据，或说明证据不足之处"],
}

DISPLAY_KEY_BY_PROFILE_FIELD = {
    "background": "background_summary",
    "pain_points": "pain_points_summary",
    "innovation_points": "innovation_summary",
    "deliverables": "deliverables_summary",
    "limitations": "limitations_summary",
}

DISPLAY_FALLBACKS = {
    "background_summary": "当前材料中未提取到高质量内容，待补充",
    "pain_points_summary": "当前材料中未提取到高质量内容，待补充",
    "innovation_summary": "当前材料中未提取到高质量内容，待补充",
    "deliverables_summary": "当前材料中未明确给出交付物描述，待补充",
    "limitations_summary": "当前材料中未明确给出局限性描述，待补充",
}


def _join_list(items: list[str], sep: str = "、") -> str:
    return sep.join(str(item) for item in items if str(item).strip()) or "待补充"


def _clean_generated_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if is_noise_paragraph(line):
            continue
        lines.append(raw_line.rstrip())

    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"。{2,}", "。", cleaned)
    cleaned = re.sub(r"([，,；;：:])。", "。", cleaned)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned


def _safe_summary(value: Any, default: str, max_chars: int = 180) -> str:
    text = normalize_text(str(value or ""))
    dirty_markers = [
        "致谢",
        "致 谢",
        "上一章",
        "本章节",
        "本章将",
        "新疆大学本科毕业论文",
        "项目负责人",
        "任务分工",
        "姓名 学号",
        "联系电话",
        "",
        "",
        "query 图片",
        "平均精度",
        "项目概述 项目名称",
    ]
    if not text or any(marker in text for marker in dirty_markers):
        return default
    if len(text) > max_chars:
        end = text.rfind("。", 0, max_chars)
        if end >= 40:
            return text[: end + 1]
        return text[:max_chars].rstrip("；,， ")
    return text


def _readable_text(value: Any) -> str:
    text = strip_outline_markers(str(value or ""))
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _sentence_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9.+#-]{1,}|[\u4e00-\u9fff]{2,}", normalize_text(text)))
    compact = re.sub(r"\s+", "", text)
    if len(tokens) < 3:
        tokens.update(compact[index : index + 2] for index in range(max(0, len(compact) - 1)))
    return {token.lower() for token in tokens if token.strip()}


def _similarity(left: str, right: str) -> float:
    left_tokens = _sentence_tokens(left)
    right_tokens = _sentence_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _too_similar(text: str, selected: list[str], threshold: float = 0.6) -> bool:
    return any(_similarity(text, item) > threshold for item in selected)


def compress_summary(sentences: Any, max_sentences: int = 2, max_chars: int = 180) -> str:
    if isinstance(sentences, str):
        raw_sentences = re.split(r"(?<=[。！？!?；;])\s*", sentences)
    elif isinstance(sentences, list):
        raw_sentences = [str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in sentences]
    else:
        raw_sentences = []

    selected: list[str] = []
    for raw_sentence in raw_sentences:
        sentence = _readable_text(raw_sentence).strip("；;，,。 ")
        if not sentence or is_noise_paragraph(sentence):
            continue
        if _too_similar(sentence, selected, threshold=0.68):
            continue
        if len(sentence) > max_chars:
            sentence = _safe_summary(sentence, "", max_chars=max_chars)
        candidate = "。".join(selected + [sentence]).strip("。")
        if len(candidate) > max_chars and selected:
            break
        selected.append(sentence)
        if len(selected) >= max_sentences:
            break

    if not selected:
        return ""
    summary = "。".join(sentence.rstrip("。") for sentence in selected).strip()
    if summary and not re.search(r"[。！？!?]$", summary):
        summary += "。"
    if len(summary) > max_chars:
        summary = _safe_summary(summary, "", max_chars=max_chars)
    return summary


def build_display_summaries(profile: dict[str, Any]) -> dict[str, str]:
    existing = dict(profile.get("display_summaries") or {})
    candidates = dict(profile.get("field_candidates") or {})
    candidate_keys = {
        "background_summary": "background_candidates",
        "pain_points_summary": "pain_point_candidates",
        "innovation_summary": "innovation_candidates",
        "deliverables_summary": "deliverable_candidates",
        "limitations_summary": "limitation_candidates",
    }
    raw_fallback_keys = {
        "background_summary": "background",
        "pain_points_summary": "pain_points",
        "innovation_summary": "innovation_points",
        "deliverables_summary": "deliverables",
        "limitations_summary": "limitations",
    }

    summaries: dict[str, str] = {}
    selected_texts: list[str] = []
    for summary_key, candidate_key in candidate_keys.items():
        text = compress_summary(existing.get(summary_key, ""), max_sentences=2, max_chars=180)
        if not text:
            text = compress_summary(candidates.get(candidate_key, []), max_sentences=2, max_chars=180)
        if not text and summary_key not in {"deliverables_summary", "limitations_summary"}:
            text = compress_summary(profile.get(raw_fallback_keys[summary_key], ""), max_sentences=2, max_chars=180)
        if text and _too_similar(text, selected_texts, threshold=0.6):
            text = ""
        if not text:
            text = DISPLAY_FALLBACKS[summary_key]
        summaries[summary_key] = text
        if "待补充" not in text:
            selected_texts.append(text)
    return summaries


def _field(profile: dict[str, Any], key: str, default: str, max_chars: int = 180) -> str:
    summary_key = DISPLAY_KEY_BY_PROFILE_FIELD.get(key)
    if summary_key:
        display_text = build_display_summaries(profile).get(summary_key, "")
        if display_text and "待补充" not in display_text:
            return _safe_summary(_readable_text(display_text), default, max_chars=max_chars)
        if key in {"deliverables", "limitations"}:
            return display_text or default
    return _safe_summary(_readable_text(profile.get(key, "")), default, max_chars=max_chars)


def _list_field(profile: dict[str, Any], key: str, limit: int = 6) -> list[str]:
    value = profile.get(key, [])
    if isinstance(value, str):
        parts = re.split(r"[、,，;；\n]+", value)
    else:
        parts = list(value or [])

    cleaned: list[str] = []
    for item in parts:
        text = _readable_text(item).strip("：:；;，,。 ")
        if not text or text in cleaned:
            continue
        if len(text) > 42:
            text = text[:42].rstrip("：:；;，,。 ") + "..."
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _join_profile_list(profile: dict[str, Any], key: str, default: str, limit: int = 6) -> str:
    items = _list_field(profile, key, limit=limit)
    return _join_list(items) if items else default


def _target_text(profile: dict[str, Any], default: str = "相关使用者") -> str:
    text = _field(profile, "target_users", default, 100)
    match = re.search(r"面向([^，。；]{2,40}?)(?:场景|用户|对象|设计)", text)
    if match:
        target = match.group(1).strip()
        return target if target.endswith("场景") else target + "场景"
    if "是一套" in text or len(text) > 80:
        return default
    return text


def _markdown_bullets(items: list[str], fallback: str = "- 待补充") -> str:
    if not items:
        return fallback
    return "\n".join(f"- {item}" for item in items)


def _read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_skill_bundle(project_root: Path) -> dict[str, str]:
    skills_dir = project_root / "skills"
    return {
        "project_schema": _read_file(skills_dir / "project_schema.md"),
        "writing_rules": _read_file(skills_dir / "writing_rules.md"),
        "source_priority": _read_file(skills_dir / "source_priority.md"),
        "demo_rubric": _read_file(skills_dir / "demo_rubric.md"),
        "quality_guardrails": _read_file(skills_dir / "quality_guardrails.md"),
        "repository_rules": _read_file(skills_dir / "repository_rules.md"),
    }


def _load_prompt(project_root: Path, filename: str) -> str:
    prompt = _read_file(project_root / "prompts" / filename)
    skills = _load_skill_bundle(project_root)
    for name, content in skills.items():
        prompt = prompt.replace("{{" + name + "}}", content)
    return prompt


def _profile_for_prompt(profile: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "anchor_document",
        "supporting_documents",
        "source_roles",
        "project_name",
        "project_type",
        "background",
        "pain_points",
        "target_users",
        "core_technologies",
        "system_architecture",
        "system_modules",
        "innovation_points",
        "experiment_results",
        "deliverables",
        "limitations",
        "future_work",
        "display_summaries",
    ]
    return {key: profile.get(key) for key in keys}


def _evidence_sources(evidence: dict[str, Any] | None) -> list[str]:
    if not evidence:
        return []
    return list(dict.fromkeys(str(chunk.get("source", "")) for chunk in evidence.get("chunks", []) if chunk.get("source")))


def _evidence_roles(evidence: dict[str, Any] | None) -> list[str]:
    if not evidence:
        return []
    return list(dict.fromkeys(str(chunk.get("role", "")) for chunk in evidence.get("chunks", []) if chunk.get("role")))


def _build_user_prompt(task: str, profile: dict[str, Any], evidence: dict[str, Any]) -> str:
    payload = {
        "task": task,
        "profile": _profile_for_prompt(profile),
        "evidence": evidence,
    }
    return (
        "请基于以下 JSON 上下文生成结果。输出必须是 JSON，包含 content、used_sources、used_roles、notes。\n"
        "anchor 是主事实来源；supporting 只能作为补充，冲突时以 anchor 为准。\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def generate_intro(profile: dict[str, Any]) -> str:
    project_name = profile.get("project_name") or "该项目"
    project_type = profile.get("project_type") or "通用项目"
    background = _field(profile, "background", "围绕真实项目场景中的核心问题展开", 90)
    pain_points = _field(profile, "pain_points", "解决传统流程效率低、准确性或体验不足的问题", 80)
    target_users = _target_text(profile)
    techs = _join_profile_list(profile, "core_technologies", "关键技术或方法", limit=4)
    return (
        f"{project_name}是一个{project_type}，面向{target_users}。项目背景是{background}，"
        f"重点解决{pain_points}。系统结合{techs}等技术或方法，形成面向实际应用的项目方案，"
        f"用于提升项目实现、展示和交付过程的完整性与可解释性。"
    )


def generate_innovation_points(profile: dict[str, Any]) -> str:
    project_name = profile.get("project_name") or "该项目"
    project_type = profile.get("project_type") or "通用项目"
    pain_points = _field(profile, "pain_points", "目标场景中效率、准确性或协同成本方面的问题", 90)
    modules = _join_profile_list(profile, "system_modules", "核心功能模块", limit=5)
    techs = _join_profile_list(profile, "core_technologies", "关键技术路线", limit=5)
    deliverables = _field(profile, "deliverables", "形成可演示、可复用的项目成果", 100)

    lines = [
        "## 创新点总结",
        f"1. 场景聚焦：{project_name}面向{project_type}的实际需求，围绕{pain_points}设计解决方案，而不是停留在单点功能演示。",
        f"2. 技术整合：项目结合{techs}，把算法、硬件、软件或流程能力整合到同一套可运行方案中。",
        f"3. 模块化实现：系统围绕{modules}组织功能，便于分阶段开发、测试和展示。",
        f"4. 成果导向：项目交付侧重于{deliverables}，更适合课程作业、项目答辩和后续迭代。",
        "5. 生成流程可追踪：本次材料生成保留主材料优先、补充材料增强、证据检索、自动校验和重试修复记录，降低多文档整理时的误写风险。",
    ]
    return "\n".join(lines)


def generate_defense_script(profile: dict[str, Any]) -> str:
    project_name = profile.get("project_name") or "该项目"
    project_type = profile.get("project_type") or "通用项目"
    background = _field(profile, "background", "项目面向真实应用场景中的具体需求展开", 130)
    pain_points = _field(profile, "pain_points", "现有方式在效率、准确性、成本或体验方面仍存在不足", 130)
    users = _target_text(profile, "目标用户")
    architecture = _field(profile, "system_architecture", "系统采用分层或模块化架构，将数据处理、核心功能和展示交互连接起来", 150)
    innovation = _field(profile, "innovation_points", "项目在场景适配、技术集成和工程落地方面具有一定创新性", 150)
    results = _field(profile, "experiment_results", "项目已形成阶段性验证结果", 120)
    deliverables = _field(profile, "deliverables", "项目已形成可展示的系统或文档成果", 110)
    limitations = _field(profile, "limitations", "后续仍可在数据规模、稳定性和应用拓展方面继续优化", 100)
    future = _field(profile, "future_work", "后续将继续完善功能、测试和部署体验", 100)
    modules = _join_profile_list(profile, "system_modules", "核心功能模块", limit=6)
    techs = _join_profile_list(profile, "core_technologies", "关键技术或方法", limit=6)

    return f"""# 3分钟答辩稿

各位老师好，我汇报的项目是《{project_name}》，它属于{project_type}。

首先介绍项目背景。{background}。项目主要面向{users}，重点解决的问题是：{pain_points}。

围绕这个问题，项目采用了{techs}等技术或方法。整体方案是：{architecture}。从功能上看，系统主要包括{modules}等部分，这些模块共同支撑从输入、处理、核心计算到结果展示或交付的完整流程。

项目的创新点主要体现在三个方面：第一，针对具体应用场景做了适配，不只是简单复用通用方案；第二，将关键技术与工程实现结合，提升了系统的可用性；第三，通过模块化设计让后续测试、优化和扩展更加清晰。根据已有材料，项目的阶段性结果是：{results}。

目前项目已经形成的交付成果包括：{deliverables}。当然，项目仍然存在一些可以继续改进的地方，例如：{limitations}。下一步计划是：{future}。

以上就是我的项目汇报，谢谢各位老师。

本稿由 ProjectPilot 基于主材料优先、补充材料增强的证据流程生成，并经过自动校验与必要的清理，尽量避免混入目录、页眉页脚或旧版本表述。
"""


def generate_readme(profile: dict[str, Any]) -> str:
    project_name = profile.get("project_name") or "未命名项目"
    project_type = profile.get("project_type") or "通用项目"
    intro = generate_intro(profile)
    background = _field(profile, "background", "项目围绕真实应用需求展开。", 160)
    pain_points = _field(profile, "pain_points", "项目用于解决现有流程中的效率、准确性或体验问题。", 140)
    architecture = _field(profile, "system_architecture", "系统采用模块化方案组织核心能力。", 180)
    deliverables = _field(profile, "deliverables", "项目成果可用于演示、部署或课程提交。", 140)
    limitations = _field(profile, "limitations", "当前版本仍可继续完善。", 120)
    future = _field(profile, "future_work", "后续将继续优化功能、性能、测试和使用体验。", 120)
    techs = _join_profile_list(profile, "core_technologies", "待补充", limit=8)
    modules = _markdown_bullets(_list_field(profile, "system_modules", limit=10))
    innovations = _markdown_bullets(_list_field(profile, "innovation_points", limit=5))

    return f"""# {project_name}

## 项目简介

{intro}

## 项目类型

{project_type}

## 背景与痛点

{background}

{pain_points}

## 核心技术 / 方法

{techs}

## 系统架构

{architecture}

## 主要模块

{modules}

## 创新点

{innovations}

## 交付成果

{deliverables}

## 限制与不足

{limitations}

## 后续优化

{future}
"""


def generate_output(profile: dict[str, Any], output_type: str) -> str:
    output_type = output_type.lower()
    if output_type == "intro":
        return _clean_generated_text(generate_intro(profile))
    if output_type == "innovation":
        return _clean_generated_text(generate_innovation_points(profile))
    if output_type == "defense":
        return _clean_generated_text(generate_defense_script(profile))
    if output_type == "readme":
        return _clean_generated_text(generate_readme(profile))
    raise ValueError(f"Unsupported output type: {output_type}")


def generate_artifact(
    profile: dict[str, Any],
    output_type: str,
    evidence: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    output_type = output_type.lower()
    if output_type not in {"intro", "innovation", "defense", "readme"}:
        raise ValueError(f"Unsupported output type: {output_type}")

    project_root = project_root or Path.cwd()
    evidence = evidence or {"task": output_type, "chunks": [], "source_summary": {}, "role_summary": {}}
    llm = LLMClient()
    llm_status = get_llm_status()

    if llm_status["available"]:
        system_prompt = _load_prompt(project_root, "system_role.md")
        task_prompt = _load_prompt(project_root, TASK_PROMPTS[output_type])
        result = llm.generate_json(
            system_prompt=f"{system_prompt}\n\n{task_prompt}",
            user_prompt=_build_user_prompt(output_type, profile, evidence),
            schema_hint=JSON_SCHEMA_HINT,
        )
        if result.get("ok") and isinstance(result.get("json"), dict):
            payload = result["json"]
            content = _clean_generated_text(str(payload.get("content", "")))
            if content:
                return {
                    "content": content,
                    "used_sources": payload.get("used_sources") or _evidence_sources(evidence),
                    "used_roles": payload.get("used_roles") or _evidence_roles(evidence),
                    "notes": payload.get("notes") or [],
                    "mode": "llm",
                    "llm": {
                        "model": result.get("model", llm_status["model"]),
                        "usage": result.get("usage", {}),
                        "compat_retry": result.get("compat_retry", ""),
                    },
                    "fallback_reason": "",
                    "fallback_detail": "",
                }
        fallback_reason = result.get("error", "empty_llm_content")
        fallback_detail = result.get("detail", "")
    else:
        fallback_reason = llm_status.get("reason", "llm_unavailable")
        fallback_detail = ""

    content = generate_output(profile, output_type)
    return {
        "content": content,
        "used_sources": _evidence_sources(evidence),
        "used_roles": _evidence_roles(evidence),
        "notes": ["LLM 未启用或调用失败，已使用规则版 fallback。"],
        "mode": "fallback",
        "llm": llm_status,
        "fallback_reason": fallback_reason,
        "fallback_detail": fallback_detail,
    }


def repair_artifact(
    draft: dict[str, Any],
    profile: dict[str, Any],
    output_type: str,
    evidence: dict[str, Any],
    verify_report: dict[str, Any],
    project_root: Path | None = None,
) -> dict[str, Any]:
    project_root = project_root or Path.cwd()
    llm_status = get_llm_status()
    original_content = str(draft.get("content", ""))

    if not llm_status["available"]:
        repaired = dict(draft)
        repaired["content"] = _clean_generated_text(original_content)
        repaired.setdefault("notes", []).append("LLM 未启用，retry repair 仅执行本地脏文本清理。")
        repaired["retry_applied"] = True
        repaired["retry_mode"] = "local_clean"
        return repaired

    llm = LLMClient()
    system_prompt = _load_prompt(project_root, "system_role.md")
    repair_prompt = _load_prompt(project_root, "retry_repair.md")
    payload = {
        "task": output_type,
        "draft": original_content,
        "verify_report": verify_report,
        "profile": _profile_for_prompt(profile),
        "evidence": evidence,
    }
    result = llm.generate_json(
        system_prompt=f"{system_prompt}\n\n{repair_prompt}",
        user_prompt="请修复以下生成稿并返回 JSON。\n" + json.dumps(payload, ensure_ascii=False, indent=2),
        schema_hint=JSON_SCHEMA_HINT,
    )

    if result.get("ok") and isinstance(result.get("json"), dict):
        payload_json = result["json"]
        content = _clean_generated_text(str(payload_json.get("content", "")))
        if content:
            return {
                "content": content,
                "used_sources": payload_json.get("used_sources") or draft.get("used_sources") or _evidence_sources(evidence),
                "used_roles": payload_json.get("used_roles") or draft.get("used_roles") or _evidence_roles(evidence),
                "notes": payload_json.get("notes") or [],
                "mode": draft.get("mode", "llm"),
                "llm": {"model": result.get("model", llm_status["model"]), "usage": result.get("usage", {})},
                "fallback_reason": draft.get("fallback_reason", ""),
                "fallback_detail": draft.get("fallback_detail", ""),
                "retry_applied": True,
                "retry_mode": "llm",
            }

    repaired = dict(draft)
    repaired["content"] = _clean_generated_text(original_content)
    repaired.setdefault("notes", []).append(f"LLM retry 失败，已保留本地清理结果：{result.get('error', 'unknown_error')}")
    repaired["retry_applied"] = True
    repaired["retry_mode"] = "local_clean_after_retry_error"
    return repaired
