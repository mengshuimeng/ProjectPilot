from __future__ import annotations

import json
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
    "Harness + LLM": "Harness + 大模型",
    "Rule-based": "规则兜底",
    "llm": "大模型生成",
    "fallback": "规则兜底",
}


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


st.set_page_config(page_title="ProjectPilot", layout="wide")
_init_clean_session()
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    .hero-title { font-size: 2.4rem; font-weight: 800; margin-bottom: 0.2rem; }
    .hero-subtitle { color: #546371; font-size: 1.05rem; margin-bottom: 1rem; }
    .metric-band { border: 1px solid #d7dee8; border-radius: 8px; padding: 0.85rem; background: #fbfcfe; }
    .tag { display: inline-block; border: 1px solid #cfd8e3; border-radius: 8px; padding: 0.18rem 0.5rem; margin: 0.12rem; background: #f7fafc; }
    .small-muted { color: #65758b; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

llm_status = get_llm_status()
docs = list(st.session_state.get("docs", []))
profile = dict(st.session_state.get("profile", {}))
report = dict(st.session_state.get("report", {}))

st.markdown("<div class='hero-title'>ProjectPilot</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-subtitle'>通用项目材料理解与答辩生成助手</div>", unsafe_allow_html=True)

top_a, top_b, top_c = st.columns([1.1, 1.1, 0.8])
with top_a:
    st.markdown(f"<div class='metric-band'><b>当前模式</b><br>{_mode_text(llm_status['mode'])}</div>", unsafe_allow_html=True)
with top_b:
    st.markdown(f"<div class='metric-band'><b>大模型</b><br>{llm_status['model']}</div>", unsafe_allow_html=True)
with top_c:
    anchor_doc = profile.get("anchor_document") or next((doc.get("name") for doc in docs if doc.get("role") == "anchor"), "未选择")
    st.markdown(f"<div class='metric-band'><b>主材料</b><br>{anchor_doc}</div>", unsafe_allow_html=True)

session_id = str(st.session_state.get("session_id", "")).strip()
st.caption(f"当前会话 ID：{session_id or '未创建'}")

upload_left, upload_right = st.columns(2)
with upload_left:
    st.subheader("主材料上传")
    st.caption("请上传一个主材料文件，系统将优先围绕该文件理解项目。")
    anchor_upload = st.file_uploader(
        "主材料文件（必填）",
        type=ALLOWED_TYPES,
        accept_multiple_files=False,
        key="anchor_uploader",
    )

with upload_right:
    st.subheader("补充材料上传")
    st.caption("可上传其他补充材料，如 PPT、说明书、README、测试文档等。")
    supporting_uploads = st.file_uploader(
        "补充材料（可选，多文件）",
        type=ALLOWED_TYPES,
        accept_multiple_files=True,
        key="supporting_uploader",
    )

actions = st.columns([1, 1, 1, 1, 2])
with actions[0]:
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
with actions[1]:
    if st.button("抽取", width="stretch"):
        profile_result = _extract_current_materials(anchor_upload, list(supporting_uploads or []))
        if profile_result is not None:
            st.session_state["report"] = run_verify(_active_root())
            _hide_generated_outputs()
            st.rerun()
with actions[2]:
    if st.button("校验", width="stretch"):
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
with actions[3]:
    if st.button("生成全部", width="stretch"):
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
with actions[4]:
    if st.button("清空页面", width="stretch"):
        st.session_state["profile"] = {}
        st.session_state["report"] = {}
        st.session_state["docs"] = []
        st.session_state["visible_tasks"] = []
        st.session_state["session_id"] = ""
        st.rerun()
    if st.button("重置 Demo 示例", width="stretch"):
        _write_demo_materials()
        st.success("已创建新的 Demo 会话。")
        st.rerun()

main_col, side_col = st.columns([1.45, 1])

with main_col:
    st.subheader("项目画像")
    if docs:
        st.dataframe(_doc_table(docs), width="stretch", hide_index=True)

    if profile:
        a, b = st.columns(2)
        with a:
            st.markdown("**项目名称**")
            st.write(profile.get("project_name") or "未识别")
            st.markdown("**项目类型**")
            st.write(profile.get("project_type") or "未识别")
            st.markdown("**背景摘要**")
            st.write(profile.get("background") or "暂无")
            st.markdown("**痛点摘要**")
            st.write(profile.get("pain_points") or "暂无")
        with b:
            st.markdown("**主材料文件**")
            st.write(profile.get("anchor_document") or "暂无")
            st.markdown("**补充材料文件**")
            supporting_docs = profile.get("supporting_documents", [])
            st.write("、".join(supporting_docs) if supporting_docs else "无")
            st.markdown("**交付成果**")
            st.write(profile.get("deliverables") or "暂无")
            st.markdown("**限制与不足**")
            st.write(profile.get("limitations") or "暂无")

        st.markdown("**核心技术标签**")
        _badge_list(list(profile.get("core_technologies", [])))
        st.markdown("**系统模块标签**")
        _badge_list(list(profile.get("system_modules", [])))
        st.markdown("**创新点摘要**")
        st.write(profile.get("innovation_points") or "暂无")
    else:
        st.info("上传主材料后点击“保存上传并抽取”，或点击“重置 Demo 示例”创建一个干净示例会话。")

with side_col:
    st.subheader("结果与校验")
    if report:
        status_text = "通过" if report.get("passed") else "需关注"
        st.metric("校验状态", status_text)
        st.write(f"警告：{len(report.get('warnings', []))} | 提示：{len(report.get('infos', []))}")
        for warning in report.get("warnings", [])[:5]:
            st.warning(warning)
        for info in report.get("infos", [])[:5]:
            st.success(info)
    else:
        st.caption("尚未生成校验报告。")

    tabs = st.tabs([TASK_LABELS[task_name] for task_name in TASK_NAMES])
    for tab, task_name in zip(tabs, TASK_NAMES):
        with tab:
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
            task_visible = task_name in st.session_state.get("visible_tasks", [])
            content = _read_text(_active_outputs_dir() / f"{task_name}.md") if task_visible else ""
            meta = _read_json(_active_outputs_dir() / f"{task_name}_meta.json") if task_visible else {}
            if content:
                st.markdown(content)
            else:
                st.caption("暂无输出。")
            if meta:
                st.markdown("**使用来源**")
                st.write("、".join(meta.get("used_sources", [])) or "暂无")
                st.markdown("**来源角色**")
                st.write(_role_text(list(meta.get("used_roles", []))))
                st.markdown("**生成模式**")
                st.write(_mode_text(meta.get("generation_mode") or meta.get("mode") or "未知"))
                st.markdown("**重试修复**")
                st.write("已发生" if meta.get("retry_used") or meta.get("retry_applied") else "未发生")

st.caption(f"支持格式：{', '.join(sorted(ext.lstrip('.') for ext in SUPPORTED_EXTS))}。旧版 doc / ppt 为兼容支持，依赖本地转换环境。")
