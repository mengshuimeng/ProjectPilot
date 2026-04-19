from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.extractor import CANONICAL_PROJECT_NAME, is_noise_paragraph, normalize_text
from app.llm_client import LLMClient, get_llm_status


TASK_PROMPTS = {
    "intro": "intro_generator.md",
    "innovation": "innovation_generator.md",
    "defense": "defense_generator.md",
    "readme": "readme_generator.md",
}

JSON_SCHEMA_HINT = {
    "content": "生成的 Markdown 或正文内容",
    "used_sources": ["project_notes.md", "README_source.md"],
    "notes": ["简要说明如何使用证据，或说明证据不足之处"],
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
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned


def _safe_summary(value: Any, default: str, max_chars: int = 180) -> str:
    text = normalize_text(str(value or ""))
    dirty_markers = ["致谢", "致 谢", "上一章", "本章节", "本章将", "新疆大学本科毕业论文"]
    if not text or any(marker in text for marker in dirty_markers):
        return default
    if len(text) > max_chars:
        end = text.rfind("。", 0, max_chars)
        if end >= 40:
            return text[: end + 1]
        return text[:max_chars].rstrip("；,， ")
    return text


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
    }


def _load_prompt(project_root: Path, filename: str) -> str:
    prompt = _read_file(project_root / "prompts" / filename)
    skills = _load_skill_bundle(project_root)
    for name, content in skills.items():
        prompt = prompt.replace("{{" + name + "}}", content)
    return prompt


def _profile_for_prompt(profile: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "project_name",
        "core_technologies",
        "system_modules",
        "background_summary",
        "pain_point_summary",
        "innovation_summary",
        "experiment_summary",
        "application_scenarios",
        "project_name_candidates",
    ]
    return {key: profile.get(key) for key in keys}


def _evidence_sources(evidence: dict[str, Any] | None) -> list[str]:
    if not evidence:
        return []
    return list(dict.fromkeys(str(chunk.get("source", "")) for chunk in evidence.get("chunks", []) if chunk.get("source")))


def _build_user_prompt(task: str, profile: dict[str, Any], evidence: dict[str, Any]) -> str:
    payload = {
        "task": task,
        "profile": _profile_for_prompt(profile),
        "evidence": evidence,
    }
    return (
        "请基于以下 JSON 上下文生成结果。输出必须是 JSON，包含 content、used_sources、notes。\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def generate_intro(profile: dict[str, Any]) -> str:
    project_name = profile.get("project_name") or CANONICAL_PROJECT_NAME
    techs = _join_list(profile.get("core_technologies", [])[:5])
    pain_point = "项目资料分散、版本口径不一致、人工整理 README 和答辩稿效率低"

    text = (
        f"ProjectPilot 是面向《{project_name}》等课程项目的项目材料理解与答辩生成助手。"
        f"它读取 PDF、Markdown 与 PPT 提纲，围绕{pain_point}等问题，抽取项目画像、检索关键证据，"
        f"结合{techs}等技术背景生成简介、创新点和答辩稿，并通过自动校验与重试修复提升输出可信度。"
    )
    return text


def generate_innovation_points(profile: dict[str, Any]) -> str:
    modules = _join_list(profile.get("system_modules", [])[:5])
    techs = _join_list(profile.get("core_technologies", [])[:5])

    lines = [
        "## 创新点总结",
        f"1. 将分散的 PDF、Markdown 与 PPT 提纲转化为结构化项目画像，覆盖{modules}等关键能力。",
        "2. 通过项目名称归一化、来源优先级和脏文本过滤，减少多版本材料造成的口径冲突。",
        "3. 采用轻量证据检索而非整段堆料，让 LLM 只基于与任务相关的来源生成内容。",
        "4. 在生成后接入 verifier 与一次有限 retry repair，形成可解释的验证与反馈闭环。",
        f"5. 保留规则版 fallback，即使未配置 LLM API，也能基于{techs}等已抽取信息生成可演示结果。",
    ]
    return "\n".join(lines)


def generate_defense_script(profile: dict[str, Any]) -> str:
    project_name = profile.get("project_name") or CANONICAL_PROJECT_NAME
    background = _safe_summary(
        profile.get("background_summary"),
        "课程项目材料来自申请书、论文、PPT 提纲和说明文档。",
        180,
    )
    pain_point = "资料分散、版本表述不统一、人工整理 README 和答辩稿效率低。"
    techs = _join_list(profile.get("core_technologies", [])[:6])
    modules = _join_list(profile.get("system_modules", [])[:6])

    return f"""# 3分钟答辩稿

各位老师好，我汇报的工具是 ProjectPilot：项目材料理解与答辩生成助手，它服务的项目背景是《{project_name}》。

这个选题解决的不是单纯的行人重识别算法问题，而是项目交付中的真实痛点：{pain_point}在准备课程作业、README 和答辩稿时，材料往往分散在 PDF、Markdown、PPT 提纲和说明文档中，人工整理容易混入旧版本信息、论文页眉页脚、目录和致谢等脏文本。

ProjectPilot 的流程是：先读取真实项目材料，清洗并分块，再抽取项目名称、核心技术、系统模块、背景、痛点和创新点等项目画像；随后按 intro、innovation、defense 等不同任务检索相关证据，最后把证据、规则和任务要求交给 LLM 生成内容。当前已识别的技术背景包括 {techs}，系统能力覆盖 {modules}。

在 Harness Engineering 设计上，我做了三层控制。第一是上下文管理，通过 skills/project_schema、writing_rules、source_priority 和 prompts 明确字段、写作规则与来源优先级。第二是外部工具调用，系统通过本地 parser 读取 PDF 和 Markdown，通过 CLI 与 Streamlit 触发流程，并可配置 OpenAI-compatible LLM API。第三是验证与反馈闭环，verifier 会检查必填字段、脏文本、来源覆盖、别名冲突和 unsupported claims；如果生成稿存在关键 warning，pipeline 会把 warning、原稿和 evidence 送回 retry prompt 进行一次有限修复。

因此，这个工具不是网页聊天，而是 Retrieval-Grounded + Harness-Controlled 的 AI 原生工作流。它能把分散材料转成可追踪证据，再生成更干净、更可信、可直接用于 README 和答辩的内容。我的汇报完毕，谢谢各位老师。
"""


def generate_output(profile: dict[str, Any], output_type: str) -> str:
    output_type = output_type.lower()
    if output_type == "intro":
        return _clean_generated_text(generate_intro(profile))
    if output_type == "innovation":
        return _clean_generated_text(generate_innovation_points(profile))
    if output_type == "defense":
        return _clean_generated_text(generate_defense_script(profile))
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
    evidence = evidence or {"task": output_type, "chunks": [], "source_summary": {}}
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
