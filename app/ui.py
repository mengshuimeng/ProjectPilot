from __future__ import annotations

import json
import html
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.llm_client import get_llm_status
from app.parser import SUPPORTED_EXTS
from app.pipeline import run_extract, run_generate, run_verify

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SESSIONS_DIR = PROJECT_ROOT / "data" / "sessions"
ALLOWED_TYPES = ["txt", "md", "pdf", "docx", "pptx", "doc", "ppt"]
ROLE_LABELS = {
    "anchor": "主材料",
    "supporting": "补充材料",
}
STATUS_LABELS = {
    "parsed": "已解析",
    "empty": "空文件",
    "unsupported": "不支持",
    "parse_error": "解析失败",
    "parse_warning": "有提示",
}
TASK_LABELS = {
    "intro": "项目简介",
    "innovation": "创新点",
    "defense": "答辩稿",
    "readme": "README 草稿",
}
TASK_NAMES = ["intro", "innovation", "defense", "readme"]
MODE_LABELS = {
    "Harness + LLM": "增强模式",
    "Rule-based": "本地模式",
    "llm": "在线生成",
    "fallback": "本地生成",
}


def _next_action(profile: dict[str, Any], report: dict[str, Any], visible_tasks: list[str]) -> tuple[str, str]:
    if not profile:
        return "先上传一个主材料文件，然后点击“保存上传并抽取”。", "blue"
    if not report:
        return "项目概览已建立，下一步建议点击“运行校验”。", "yellow"
    if not visible_tasks:
        return "校验已完成，下一步建议点击“生成全部”或在右侧单独生成。", "green"
    if report.get("warnings"):
        return "当前已有结果，建议优先展示校验提示和证据链，再说明 retry 修复。", "yellow"
    return "当前流程已完成，可以直接录屏展示项目概览、结果和证据链。", "green"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _safe_filename(name: str) -> str:
    return Path(name).name.replace("/", "_").replace("\\", "_")


def _new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _session_root(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def _active_root() -> Path:
    session_id = str(st.session_state.get("session_id", "")).strip()
    return _session_root(session_id) if session_id else PROJECT_ROOT


def _active_raw_dir() -> Path:
    root = _active_root()
    return root / "raw" if root != PROJECT_ROOT else RAW_DIR


def _active_processed_dir() -> Path:
    root = _active_root()
    return root / "processed" if root != PROJECT_ROOT else PROCESSED_DIR


def _active_outputs_dir() -> Path:
    root = _active_root()
    return root / "outputs" if root != PROJECT_ROOT else OUTPUTS_DIR


def _create_session(reason: str = "upload") -> Path:
    session_id = _new_session_id()
    root = _session_root(session_id)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "processed").mkdir(parents=True, exist_ok=True)
    (root / "outputs").mkdir(parents=True, exist_ok=True)
    (root / "session.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "reason": reason,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    st.session_state["session_id"] = session_id
    return root


def _clear_dir(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in target.rglob("*"):
        if path.is_file():
            path.unlink()
    for path in sorted([item for item in target.rglob("*") if item.is_dir()], reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def _save_uploaded_files(anchor_file: Any, supporting_files: list[Any]) -> dict[str, Any]:
    root = _create_session("upload")
    raw_dir = root / "raw"
    processed_dir = root / "processed"
    _clear_dir(raw_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    anchor_name = _safe_filename(anchor_file.name)
    (raw_dir / anchor_name).write_bytes(anchor_file.getvalue())

    supporting_names: list[str] = []
    for uploaded_file in supporting_files:
        file_name = _safe_filename(uploaded_file.name)
        if file_name == anchor_name:
            file_name = f"supporting_{file_name}"
        (raw_dir / file_name).write_bytes(uploaded_file.getvalue())
        supporting_names.append(file_name)

    manifest = {
        "session_id": st.session_state["session_id"],
        "anchor_document": anchor_name,
        "supporting_documents": supporting_names,
    }
    (processed_dir / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def _has_raw_files() -> bool:
    if not str(st.session_state.get("session_id", "")).strip():
        return False
    raw_dir = _active_raw_dir()
    return raw_dir.exists() and any(path.is_file() for path in raw_dir.rglob("*"))


def _save_current_uploads(anchor_file: Any, supporting_files: list[Any]) -> dict[str, Any] | None:
    if anchor_file is None:
        return None
    manifest = _save_uploaded_files(anchor_file, supporting_files)
    _hide_generated_outputs()
    st.session_state["profile"] = {}
    st.session_state["report"] = {}
    st.session_state["docs"] = []
    return manifest


def _extract_current_materials(anchor_file: Any, supporting_files: list[Any]) -> dict[str, Any] | None:
    _save_current_uploads(anchor_file, supporting_files)
    if anchor_file is None and not _has_raw_files():
        st.error("请先上传一个主材料文件。")
        return None
    profile = run_extract(_active_root())
    st.session_state["profile"] = profile
    _refresh_docs_from_disk()
    return profile


def _write_demo_materials() -> None:
    root = _create_session("demo_reset")
    raw_dir = root / "raw"
    processed_dir = root / "processed"
    _clear_dir(raw_dir)
    anchor_name = "demo_anchor_project.md"
    supporting_name = "demo_supporting_notes.md"
    (raw_dir / anchor_name).write_text(
        "\n".join(
            [
                "# 基于多模态感知与智能决策的柔性质检分拣机器人系统",
                "项目名称：基于多模态感知与智能决策的柔性质检分拣机器人系统",
                "项目类型：硬件 / IoT 项目",
                "项目背景：柔性制造场景中，小批量、多品类产品检测和分拣频繁变化，传统人工质检效率低、稳定性不足。",
                "痛点：人工质检成本高，检测结果受经验影响，分拣流程难以及时适配新产品。",
                "目标用户：智能制造实验室、课程项目团队和中小型产线管理者。",
                "技术路线：采用视觉识别、传感器采集、机械臂控制和边缘端决策，实现缺陷识别与自动分拣。",
                "系统架构：系统由感知采集层、边缘识别层、运动执行层和平台管理层组成。",
                "创新点：多模态感知融合、柔性分拣策略、轻量化部署和可追踪质检记录。",
                "交付成果：机器人原型、识别模型、分拣控制程序、演示视频和项目说明文档。",
                "后续优化：继续扩充缺陷样本，提升复杂光照下的识别稳定性。",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / supporting_name).write_text(
        "PPT 提纲：背景痛点、系统架构、核心模块、实验结果、创新点、应用前景。",
        encoding="utf-8",
    )
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "input_manifest.json").write_text(
        json.dumps(
            {
                "session_id": st.session_state["session_id"],
                "anchor_document": anchor_name,
                "supporting_documents": [supporting_name],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    st.session_state["profile"] = run_extract(root)
    st.session_state["report"] = run_verify(root)
    _refresh_docs_from_disk()
    _hide_generated_outputs()


def _badge_list(items: list[str], limit: int = 16) -> None:
    if not items:
        st.caption("暂无")
        return
    st.markdown(
        " ".join(f"<span class='tag'>{item}</span>" for item in items[:limit]),
        unsafe_allow_html=True,
    )


def _doc_table(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "文件": doc.get("name", ""),
            "角色": ROLE_LABELS.get(str(doc.get("role", "")), str(doc.get("role", ""))),
            "类型": doc.get("suffix", ""),
            "状态": STATUS_LABELS.get(str(doc.get("parse_status", "")), str(doc.get("parse_status", ""))),
            "字符数": doc.get("char_count", 0),
            "提示": doc.get("parse_warning", ""),
        }
        for doc in docs
    ]


def _role_text(roles: list[str]) -> str:
    labels = [ROLE_LABELS.get(str(role), str(role)) for role in roles if str(role).strip()]
    return "、".join(labels) or "暂无"


def _mode_text(mode: str) -> str:
    return MODE_LABELS.get(mode, mode or "未知")


def _init_clean_session() -> None:
    if st.session_state.get("ui_clean_session_initialized"):
        return
    st.session_state["ui_clean_session_initialized"] = True
    st.session_state["profile"] = {}
    st.session_state["report"] = {}
    st.session_state["docs"] = []
    st.session_state["visible_tasks"] = []
    st.session_state["session_id"] = ""


def _refresh_docs_from_disk() -> None:
    docs_payload = _read_json(_active_processed_dir() / "documents.json")
    st.session_state["docs"] = docs_payload.get("documents", [])


def _show_task(task_name: str) -> None:
    visible_tasks = list(st.session_state.get("visible_tasks", []))
    if task_name not in visible_tasks:
        visible_tasks.append(task_name)
    st.session_state["visible_tasks"] = visible_tasks


def _hide_generated_outputs() -> None:
    st.session_state["visible_tasks"] = []


def _short_text(value: Any, limit: int = 260) -> str:
    if isinstance(value, list):
        text = "；".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = str(value or "").strip()
    if not text:
        return "暂无"
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _compact_list(value: Any, limit: int = 10) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [part.strip(" -，,；;") for part in value.replace("\n", "；").split("；")]
    else:
        items = []
    clean_items: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in clean_items:
            clean_items.append(text)
    return clean_items[:limit]


def _section_title(step: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="step-heading">
            <span class="step-pill">{html.escape(step)}</span>
            <div>
                <div class="step-title">{html.escape(title)}</div>
                <div class="step-subtitle">{html.escape(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _status_pill(label: str, value: str, tone: str = "neutral") -> str:
    return (
        f"<span class='status-pill status-{tone}'>"
        f"<b>{html.escape(label)}</b> {html.escape(value or '暂无')}"
        "</span>"
    )


def _file_card(name: str, caption: str = "") -> None:
    caption_html = f"<div class='file-caption'>{html.escape(caption)}</div>" if caption else ""
    st.markdown(
        f"""
        <div class="file-card">
            <div class="file-name">{html.escape(name)}</div>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _summary_card(title: str, body: Any, tone: str = "neutral") -> None:
    st.markdown(
        f"""
        <div class="summary-card summary-{tone}">
            <div class="summary-title">{html.escape(title)}</div>
            <div class="summary-body">{html.escape(_short_text(body, 360))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _display_summary(profile: dict[str, Any], summary_key: str) -> str:
    display = profile.get("display_summaries") or {}
    text = str(display.get(summary_key, "")).strip() if isinstance(display, dict) else ""
    return text or "当前材料中未提取到高质量内容，待补充"


def _summary_sources(profile: dict[str, Any], summary_key: str) -> list[dict[str, Any]]:
    sources = profile.get("display_summary_sources") or {}
    if isinstance(sources, dict):
        return list(sources.get(summary_key, []) or [])
    return []


def _summary_candidates(profile: dict[str, Any], candidate_key: str) -> list[dict[str, Any]]:
    candidates = profile.get("field_candidates") or {}
    if isinstance(candidates, dict):
        return list(candidates.get(candidate_key, []) or [])
    return []


def _render_profile_summary_card(
    title: str,
    summary_key: str,
    candidate_key: str,
    profile: dict[str, Any],
    tone: str = "neutral",
) -> None:
    _summary_card(title, _display_summary(profile, summary_key), tone)
    used_sources = _summary_sources(profile, summary_key)
    candidates = _summary_candidates(profile, candidate_key)
    with st.expander(f"{title}来源", expanded=False):
        if used_sources:
            for item in used_sources:
                st.caption(
                    f"{ROLE_LABELS.get(str(item.get('role', '')), item.get('role', ''))} | "
                    f"{item.get('source', '未知来源')}"
                )
        else:
            st.caption("暂无明确来源，或当前字段为待补充。")
        if candidates:
            st.markdown("**参考片段**")
            for item in candidates[:5]:
                st.caption(f"- {item.get('text', '')}")


def _report_one_liner(report: dict[str, Any]) -> str:
    if not report:
        return "尚未运行校验。"
    if report.get("passed"):
        return "项目概览与输出内容已通过当前校验。"
    return "发现需要关注的问题，建议先查看提示后再用于提交。"


def _visible_task_content(task_name: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    task_visible = task_name in st.session_state.get("visible_tasks", [])
    if not task_visible:
        return "", {}, {}
    outputs_dir = _active_outputs_dir()
    return (
        _read_text(outputs_dir / f"{task_name}.md"),
        _read_json(outputs_dir / f"{task_name}_meta.json"),
        _read_json(outputs_dir / f"{task_name}_evidence.json"),
    )


def _latest_visible_task() -> str | None:
    visible_tasks = [task for task in st.session_state.get("visible_tasks", []) if task in TASK_NAMES]
    return visible_tasks[-1] if visible_tasks else None


def _evidence_summary(task_name: str | None, profile: dict[str, Any]) -> dict[str, Any]:
    if not task_name:
        return {}
    _, meta, evidence = _visible_task_content(task_name)
    chunks = evidence.get("chunks", []) if isinstance(evidence, dict) else []
    anchor_sources = sorted({chunk.get("source", "") for chunk in chunks if chunk.get("role") == "anchor"})
    supporting_sources = sorted({chunk.get("source", "") for chunk in chunks if chunk.get("role") == "supporting"})
    return {
        "task": task_name,
        "chunks": chunks,
        "anchor_sources": [item for item in anchor_sources if item],
        "supporting_sources": [item for item in supporting_sources if item],
        "retry": bool(meta.get("retry_used") or meta.get("retry_applied")),
        "mode": _mode_text(str(meta.get("generation_mode") or meta.get("mode") or "未知")),
        "paths": meta.get("paths", {}),
        "anchor_document": evidence.get("anchor_document") or profile.get("anchor_document") or "暂无",
        "used_sources": list(meta.get("used_sources", [])),
        "used_roles": list(meta.get("used_roles", [])),
        "claim_evidence_alignment": (meta.get("final_verify_report") or {}).get("claim_evidence_alignment", {}),
        "source_coverage_summary": (meta.get("final_verify_report") or {}).get("source_coverage_summary", {}),
    }


def _claim_support_summary(report: dict[str, Any]) -> str:
    claim = report.get("claim_evidence_alignment") or {}
    if not claim:
        return "暂无 claim-support 摘要。"
    checked = int(claim.get("checked_count", 0))
    supported = int(claim.get("supported_count", 0))
    ratio = float(claim.get("support_ratio", 0.0))
    return f"已检查 {checked} 条声明，{supported} 条获得 evidence 支撑，支撑率 {ratio:.0%}。"


st.set_page_config(page_title="ProjectPilot", layout="wide")
_init_clean_session()
st.markdown(
    """
    <style>
    .block-container { padding-top: 2.35rem; padding-bottom: 2rem; max-width: 1320px; }
    .hero-wrap { border-bottom: 1px solid #e5ebf3; padding: 0.15rem 0 0.9rem; margin-bottom: 0.8rem; }
    .hero-title { font-size: 2.05rem; line-height: 1.35; font-weight: 760; margin: 0; padding: 0.12rem 0 0.05rem; color: #102033; letter-spacing: 0; overflow: visible; }
    .hero-subtitle { color: #526173; font-size: 1rem; margin: 0.12rem 0 0.72rem; line-height: 1.55; }
    .flow-line { color: #64748b; font-size: 0.88rem; margin-top: 0.2rem; }
    .status-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 1.15rem; }
    .status-pill { display: inline-flex; gap: 0.35rem; align-items: center; border: 1px solid #d8e0eb; border-radius: 999px; padding: 0.28rem 0.7rem; background: #f8fafc; color: #334155; font-size: 0.86rem; }
    .status-blue { border-color: #bfdbfe; background: #eff6ff; color: #1d4ed8; }
    .status-green { border-color: #bbf7d0; background: #f0fdf4; color: #166534; }
    .status-yellow { border-color: #fde68a; background: #fffbeb; color: #92400e; }
    .step-heading { display: flex; align-items: flex-start; gap: 0.72rem; margin: 1.05rem 0 0.65rem; }
    .step-pill { border-radius: 999px; padding: 0.2rem 0.58rem; background: #2563eb; color: white; font-size: 0.78rem; font-weight: 700; white-space: nowrap; }
    .step-title { font-size: 1.2rem; font-weight: 760; color: #102033; line-height: 1.25; }
    .step-subtitle { color: #64748b; font-size: 0.92rem; margin-top: 0.08rem; }
    .upload-title { font-size: 1.08rem; font-weight: 760; color: #102033; margin-bottom: 0.2rem; }
    .upload-desc { color: #64748b; font-size: 0.9rem; min-height: 2.5rem; }
    .anchor-accent { border-left: 4px solid #2563eb; padding-left: 0.65rem; }
    .supporting-accent { border-left: 4px solid #94a3b8; padding-left: 0.65rem; }
    .file-card { border: 1px solid #dbe3ee; border-radius: 8px; padding: 0.55rem 0.65rem; background: #f8fafc; margin: 0.28rem 0; }
    .file-name { font-weight: 700; color: #1e293b; overflow-wrap: anywhere; }
    .file-caption { color: #64748b; font-size: 0.84rem; margin-top: 0.12rem; }
    .tag { display: inline-block; border: 1px solid #cfd8e3; border-radius: 8px; padding: 0.18rem 0.5rem; margin: 0.12rem; background: #f7fafc; color: #263548; }
    .summary-card { border: 1px solid #dbe3ee; border-radius: 8px; padding: 0.72rem 0.8rem; background: #ffffff; margin-bottom: 0.55rem; }
    .summary-blue { border-color: #bfdbfe; background: #f8fbff; }
    .summary-green { border-color: #bbf7d0; background: #f8fffb; }
    .summary-title { color: #64748b; font-size: 0.84rem; margin-bottom: 0.25rem; }
    .summary-body { color: #152238; line-height: 1.62; }
    .source-note { color: #64748b; font-size: 0.88rem; line-height: 1.55; }
    </style>
    """,
    unsafe_allow_html=True,
)

llm_status = get_llm_status()
docs = list(st.session_state.get("docs", []))
profile = dict(st.session_state.get("profile", {}))
report = dict(st.session_state.get("report", {}))
anchor_doc = profile.get("anchor_document") or next((doc.get("name") for doc in docs if doc.get("role") == "anchor"), "未选择")
session_id = str(st.session_state.get("session_id", "")).strip()
mode_tone = "blue" if llm_status.get("mode") == "Harness + LLM" else "yellow"
visible_tasks = list(st.session_state.get("visible_tasks", []))
next_action_text, next_action_tone = _next_action(profile, report, visible_tasks)

model_state = "已连接" if llm_status.get("available") else "本地处理"
st.markdown(
    "<div class='hero-wrap'>"
    "<div class='hero-title'>ProjectPilot</div>"
    "<div class='hero-subtitle'>通用项目材料整理与答辩生成助手</div>"
    "<div class='status-row'>"
    + _status_pill("工作模式", _mode_text(llm_status["mode"]), mode_tone)
    + _status_pill("处理方式", model_state, "neutral")
    + _status_pill("会话", session_id or "未创建", "neutral")
    + _status_pill("主材料", str(anchor_doc), "green" if anchor_doc != "未选择" else "neutral")
    + "</div>"
    "<div class='flow-line'>上传材料 → 整理项目概览 → 生成答辩与说明文档</div>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='status-row'>{_status_pill('当前建议', next_action_text, next_action_tone)}</div>",
    unsafe_allow_html=True,
)

_section_title("步骤 1", "上传材料", "先确定一个主材料，再按需补充 PPT、README、说明书或测试文档。")
upload_left, upload_right = st.columns([1.15, 1])
with upload_left:
    with st.container(border=True):
        st.markdown(
            "<div class='anchor-accent'><div class='upload-title'>主材料上传（必填）</div>"
            "<div class='upload-desc'>上传一个最能代表项目全貌的文件，后续整理会优先参考它。</div></div>",
            unsafe_allow_html=True,
        )
        anchor_upload = st.file_uploader(
            "选择主材料文件",
            type=ALLOWED_TYPES,
            accept_multiple_files=False,
            key="anchor_uploader",
            label_visibility="collapsed",
        )
        if anchor_upload is not None:
            _file_card(anchor_upload.name, "待保存为本次整理的主材料")
        elif anchor_doc != "未选择":
            _file_card(str(anchor_doc), "当前会话主材料")
        else:
            st.info("请先上传一个主材料文件。")
        st.caption("稳定支持：txt / md / pdf / docx / pptx；兼容支持：doc / ppt。")

with upload_right:
    with st.container(border=True):
        st.markdown(
            "<div class='supporting-accent'><div class='upload-title'>补充材料上传（可选）</div>"
            "<div class='upload-desc'>可上传 PPT、README、说明书、测试文档等，让整理结果更完整。</div></div>",
            unsafe_allow_html=True,
        )
        supporting_uploads = st.file_uploader(
            "选择补充材料",
            type=ALLOWED_TYPES,
            accept_multiple_files=True,
            key="supporting_uploader",
            label_visibility="collapsed",
        )
        if supporting_uploads:
            for uploaded_file in supporting_uploads[:5]:
                _file_card(uploaded_file.name, "待保存为补充材料")
            if len(supporting_uploads) > 5:
                st.caption(f"还有 {len(supporting_uploads) - 5} 个文件将在保存时一并处理。")
        else:
            supporting_docs = profile.get("supporting_documents", [])
            if supporting_docs:
                for file_name in supporting_docs[:5]:
                    _file_card(str(file_name), "当前会话补充材料")
            else:
                st.caption("没有补充材料也可以运行。")
        st.caption("补充材料用于完善细节；内容冲突时默认以主材料为准。")

_section_title("步骤 2", "整理与生成", "保存材料、运行校验，或一次性生成全部交付物。")
with st.container(border=True):
    action_cols = st.columns([1.35, 1, 1, 0.9, 0.95])
    with action_cols[0]:
        if st.button("生成全部", type="primary", width="stretch"):
            profile_result = _extract_current_materials(anchor_upload, list(supporting_uploads or []))
            if profile_result is None:
                st.stop()
            st.session_state["report"] = run_verify(_active_root())
            for task_name in ("intro", "innovation", "defense", "readme"):
                run_generate(_active_root(), task_name)
            st.session_state["report"] = run_verify(_active_root())
            st.session_state["profile"] = _read_json(_active_processed_dir() / "profile.json")
            _refresh_docs_from_disk()
            st.session_state["visible_tasks"] = list(TASK_NAMES)
            st.success("四类产物已生成。")
            st.rerun()
    with action_cols[1]:
        if st.button("保存上传并抽取", width="stretch"):
            if anchor_upload is None:
                st.error("请先上传一个主材料文件。")
            else:
                manifest = _save_current_uploads(anchor_upload, list(supporting_uploads or []))
                st.session_state["profile"] = run_extract(_active_root())
                st.session_state["report"] = run_verify(_active_root())
                _refresh_docs_from_disk()
                _hide_generated_outputs()
                st.success(f"已保存主材料：{manifest['anchor_document'] if manifest else ''}")
                st.rerun()
    with action_cols[2]:
        if st.button("运行校验", width="stretch"):
            if anchor_upload is not None:
                _extract_current_materials(anchor_upload, list(supporting_uploads or []))
            elif not _has_raw_files():
                st.error("请先上传一个主材料文件。")
            else:
                st.session_state["profile"] = run_extract(_active_root())
                _refresh_docs_from_disk()
            if _has_raw_files():
                st.session_state["report"] = run_verify(_active_root())
                st.rerun()
    with action_cols[3]:
        if st.button("清空页面", width="stretch"):
            st.session_state["profile"] = {}
            st.session_state["report"] = {}
            st.session_state["docs"] = []
            st.session_state["visible_tasks"] = []
            st.session_state["session_id"] = ""
            st.rerun()
    with action_cols[4]:
        if st.button("重置 Demo 示例", width="stretch"):
            _write_demo_materials()
            st.success("已创建新的 Demo 会话。")
            st.rerun()

_section_title("步骤 3", "查看结果", "左侧查看项目概览，右侧查看检查状态和生成内容。")
main_col, side_col = st.columns([1.05, 1.2])

with main_col:
    with st.container(border=True):
        st.markdown("#### 项目概览")
        if profile:
            st.markdown(f"**{profile.get('project_name') or '未识别项目名称'}**")
            st.caption(profile.get("project_type") or "未识别项目类型")
            metric_a, metric_b = st.columns(2)
            with metric_a:
                st.metric("主材料", profile.get("anchor_document") or "暂无")
            with metric_b:
                st.metric("补充材料数", len(profile.get("supporting_documents", [])))

            _render_profile_summary_card("背景摘要", "background_summary", "background_candidates", profile, "blue")
            _render_profile_summary_card("痛点摘要", "pain_points_summary", "pain_point_candidates", profile)
            _render_profile_summary_card("创新点摘要", "innovation_summary", "innovation_candidates", profile, "green")

            st.markdown("**核心技术**")
            _badge_list(_compact_list(profile.get("core_technologies"), 18))
            st.markdown("**系统模块**")
            _badge_list(_compact_list(profile.get("system_modules"), 18))

            detail_a, detail_b = st.columns(2)
            with detail_a:
                _render_profile_summary_card("交付物", "deliverables_summary", "deliverable_candidates", profile)
            with detail_b:
                _render_profile_summary_card("局限性", "limitations_summary", "limitation_candidates", profile)
        else:
            st.info("上传主材料后点击“保存上传并抽取”，或点击“重置 Demo 示例”创建一个干净示例会话。")

    if docs:
        with st.expander("查看解析文件列表", expanded=False):
            st.dataframe(_doc_table(docs), width="stretch", hide_index=True)

with side_col:
    with st.container(border=True):
        st.markdown("#### 检查状态")
        if report:
            warn_count = len(report.get("warnings", []))
            info_count = len(report.get("infos", []))
            if report.get("passed"):
                st.success("校验通过")
            else:
                st.warning("存在需要关注的提示")
            m1, m2, m3 = st.columns(3)
            m1.metric("状态", "通过" if report.get("passed") else "需关注")
            m2.metric("警告", warn_count)
            m3.metric("提示", info_count)
            st.caption(_report_one_liner(report))
            for warning in report.get("warnings", [])[:3]:
                st.warning(warning)
            if not report.get("warnings"):
                for info in report.get("infos", [])[:2]:
                    st.info(info)
            claim_alignment = report.get("claim_evidence_alignment") or {}
            if claim_alignment:
                st.caption(_claim_support_summary(report))
        else:
            st.info("尚未生成校验报告。")

    tabs = st.tabs([TASK_LABELS[task_name] for task_name in TASK_NAMES])
    for tab, task_name in zip(tabs, TASK_NAMES):
        with tab:
            content, meta, _ = _visible_task_content(task_name)
            warnings = list((meta.get("final_verify_report") or {}).get("warnings", [])) if meta else []
            if warnings:
                st.warning("当前内容存在提示：" + "；".join(str(item) for item in warnings[:2]))

            if st.button(f"生成{TASK_LABELS[task_name]}", key=f"generate_{task_name}", width="stretch"):
                profile_result = _extract_current_materials(anchor_upload, list(supporting_uploads or []))
                if profile_result is None:
                    st.stop()
                st.session_state["report"] = run_verify(_active_root())
                result = run_generate(_active_root(), task_name)
                st.session_state["report"] = result["meta"]["final_verify_report"]
                st.session_state["profile"] = _read_json(_active_processed_dir() / "profile.json")
                _refresh_docs_from_disk()
                _show_task(task_name)
                st.rerun()

            if content:
                with st.container(border=True):
                    st.markdown(content)
            else:
                st.info("暂无输出。可点击本页签内按钮单独生成，或在步骤 2 点击“生成全部”。")

            if meta:
                final_report = meta.get("final_verify_report") or {}
                evidence_summary_cols = st.columns(4)
                evidence_summary_cols[0].metric("来源数量", len(meta.get("used_sources", [])))
                evidence_summary_cols[1].metric("来源角色", _role_text(list(meta.get("used_roles", []))))
                evidence_summary_cols[2].metric("retry", "已发生" if meta.get("retry_used") or meta.get("retry_applied") else "未发生")
                evidence_summary_cols[3].metric("支撑率", f"{float((final_report.get('claim_evidence_alignment') or {}).get('support_ratio', 0.0)):.0%}")

                st.caption(_claim_support_summary(final_report))

                source_col, mode_col = st.columns([1.25, 0.75])
                with source_col:
                    st.markdown("**参考材料**")
                    st.markdown(
                        f"<div class='source-note'>{html.escape('、'.join(meta.get('used_sources', [])) or '暂无')}</div>",
                        unsafe_allow_html=True,
                    )
                with mode_col:
                    st.markdown("**处理信息**")
                    st.caption(f"方式：{_mode_text(str(meta.get('generation_mode') or meta.get('mode') or '未知'))}")
                    st.caption("自动修正：已发生" if meta.get("retry_used") or meta.get("retry_applied") else "自动修正：未发生")
                    st.caption(f"材料类型：{_role_text(list(meta.get('used_roles', [])))}")

                claim_alignment = final_report.get("claim_evidence_alignment") or {}
                if claim_alignment.get("details"):
                    with st.expander("查看 claim-support 摘要", expanded=False):
                        for item in claim_alignment.get("details", [])[:3]:
                            st.markdown(f"**声明**：{item.get('claim', '暂无')}")
                            st.caption(
                                f"来源：{item.get('best_source', '暂无')} | "
                                f"角色：{ROLE_LABELS.get(str(item.get('best_role', '')), str(item.get('best_role', '')))} | "
                                f"语义相似度：{float(item.get('best_semantic_similarity', 0.0)):.2f}"
                            )
                            excerpt = str(item.get("best_evidence_excerpt", "")).strip()
                            if excerpt:
                                st.caption(f"证据片段：{excerpt}")

_section_title("材料依据", "参考来源", "展示当前内容参考了哪些主材料和补充材料。")
latest_task = _latest_visible_task()
evidence_info = _evidence_summary(latest_task, profile)
with st.container(border=True):
    if not latest_task or not evidence_info:
        st.info("生成任一内容后，这里会显示材料依据摘要。")
    else:
        st.markdown(f"**当前查看任务：{TASK_LABELS.get(latest_task, latest_task)}**")
        ev_a, ev_b, ev_c, ev_d = st.columns(4)
        ev_a.metric("主材料", evidence_info.get("anchor_document", "暂无"))
        ev_b.metric("参考片段", len(evidence_info.get("chunks", [])))
        ev_c.metric("处理方式", evidence_info.get("mode", "未知"))
        ev_d.metric("自动修正", "已发生" if evidence_info.get("retry") else "未发生")

        claim_report = evidence_info.get("claim_evidence_alignment") or {}
        if claim_report:
            st.caption(
                f"claim-support 对齐：{int(claim_report.get('supported_count', 0))}/"
                f"{int(claim_report.get('checked_count', 0))}，"
                f"支撑率 {float(claim_report.get('support_ratio', 0.0)):.0%}"
            )
        source_coverage = evidence_info.get("source_coverage_summary") or {}
        if source_coverage:
            st.caption(
                f"anchor_used={source_coverage.get('anchor_used', False)} | "
                f"covered_sources={source_coverage.get('covered_count', 0)} | "
                f"minimum_expected={source_coverage.get('minimum_expected', 0)}"
            )

        st.markdown("**主材料来源**")
        _badge_list(evidence_info.get("anchor_sources", []) or [evidence_info.get("anchor_document", "暂无")], 8)
        st.markdown("**补充材料来源**")
        supporting_sources = evidence_info.get("supporting_sources", [])
        if supporting_sources:
            _badge_list(supporting_sources, 12)
        else:
            st.caption("当前内容未使用补充材料，或尚未找到可用补充片段。")

        if evidence_info.get("used_sources"):
            st.markdown("**本次实际使用来源**")
            _badge_list(evidence_info.get("used_sources", []), 12)

        chunks = list(evidence_info.get("chunks", []))
        if chunks:
            with st.expander("查看关键 evidence 片段", expanded=False):
                for chunk in chunks[:4]:
                    st.markdown(
                        f"**{chunk.get('source', '未知来源')}**"
                        f" · {ROLE_LABELS.get(str(chunk.get('role', '')), str(chunk.get('role', '')))}"
                        f" · score={chunk.get('score', 0)}"
                    )
                    st.caption(chunk.get("text", ""))

        paths = evidence_info.get("paths", {})
        if paths:
            with st.expander("查看产物路径", expanded=False):
                for label, path in paths.items():
                    st.caption(f"{label}: {path}")

st.caption(f"支持格式：{', '.join(sorted(ext.lstrip('.') for ext in SUPPORTED_EXTS))}。旧版 doc / ppt 为兼容支持，依赖本地转换环境。")
