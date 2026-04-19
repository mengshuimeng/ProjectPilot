from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.llm_client import get_llm_status
from app.parser import load_documents
from app.pipeline import run_extract, run_generate, run_verify


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _badge_list(items: list[str]) -> None:
    if not items:
        st.caption("暂无")
        return
    cols = st.columns(3)
    for index, item in enumerate(items):
        with cols[index % 3]:
            st.markdown(f"`{item}`")


st.set_page_config(page_title="ProjectPilot", layout="wide")

llm_status = get_llm_status()
docs = load_documents(PROJECT_ROOT / "data" / "raw")
profile = st.session_state.get("profile") or _read_json(PROJECT_ROOT / "data" / "processed" / "profile.json")
report = st.session_state.get("report") or _read_json(PROJECT_ROOT / "data" / "processed" / "verify_report.json")
active_task = st.session_state.get("active_task", "defense")
output_text = _read_text(PROJECT_ROOT / "outputs" / f"{active_task}.md")
meta = _read_json(PROJECT_ROOT / "outputs" / f"{active_task}_meta.json")

st.title("ProjectPilot")
st.caption("项目材料理解与答辩生成助手")
st.info(f"当前模式：{llm_status['mode']} | 模型：{llm_status['model']}")

with st.sidebar:
    st.header("数据源概览")
    st.write(f"文档数：{len(docs)}")
    st.write(f"非空文件：{sum(1 for doc in docs if int(doc.get('char_count', 0)) > 0)}")
    for doc in docs:
        st.caption(f"{doc['name']} · {doc['char_count']} chars")

    st.header("Skills 概览")
    for skill_name in ["project_schema.md", "writing_rules.md", "source_priority.md"]:
        path = PROJECT_ROOT / "skills" / skill_name
        st.write(f"{'已加载' if path.exists() else '缺失'} {skill_name}")

    st.header("LLM 配置状态")
    st.write(f"enabled: `{llm_status['enabled']}`")
    st.write(f"available: `{llm_status['available']}`")
    if llm_status.get("reason"):
        st.caption(llm_status["reason"])

    st.header("操作")
    if st.button("抽取", use_container_width=True):
        st.session_state["profile"] = run_extract(PROJECT_ROOT)
        st.success("项目画像已更新")
        st.rerun()
    if st.button("校验", use_container_width=True):
        st.session_state["report"] = run_verify(PROJECT_ROOT)
        st.success("校验报告已更新")
        st.rerun()
    for label, task in [("生成简介", "intro"), ("生成创新点", "innovation"), ("生成答辩稿", "defense")]:
        if st.button(label, use_container_width=True):
            result = run_generate(PROJECT_ROOT, task)
            st.session_state["active_task"] = task
            st.session_state["report"] = result["meta"]["final_verify_report"]
            st.success(f"{label}完成")
            st.rerun()

main_col, right_col = st.columns([1.35, 1])

with main_col:
    st.subheader("项目画像")
    if profile:
        st.markdown(f"**项目名称**：{profile.get('project_name', '未识别')}")
        st.markdown("**背景摘要**")
        st.write(profile.get("background_summary") or "暂无")
        st.markdown("**痛点摘要**")
        st.write(profile.get("pain_point_summary") or "暂无")

        st.markdown("**核心技术**")
        _badge_list(list(profile.get("core_technologies", []))[:12])

        st.markdown("**系统模块**")
        _badge_list(list(profile.get("system_modules", []))[:12])

        st.markdown("**项目名称候选**")
        candidates = profile.get("project_name_candidates", [])
        if candidates:
            for candidate in candidates[:8]:
                st.caption(candidate)
        else:
            st.caption("暂无候选")
    else:
        st.warning("尚未抽取项目画像，请先点击左侧“抽取”。")

with right_col:
    st.subheader("校验报告")
    if report:
        st.metric("passed", str(report.get("passed", False)))
        warnings = report.get("warnings", [])
        infos = report.get("infos", [])
        st.write(f"warnings: {len(warnings)} | infos: {len(infos)}")
        for warning in warnings[:6]:
            st.warning(warning)
        for info in infos[:4]:
            st.success(info)
    else:
        st.caption("尚未生成校验报告。")

    st.subheader("输出预览")
    task = st.selectbox("查看产物", ["intro", "innovation", "defense"], index=["intro", "innovation", "defense"].index(active_task))
    if task != active_task:
        st.session_state["active_task"] = task
        st.rerun()
    if output_text:
        st.markdown(output_text)
    else:
        st.caption("暂无输出，请先生成内容。")

    st.subheader("使用来源")
    used_sources = meta.get("used_sources", [])
    if used_sources:
        for source in used_sources:
            st.caption(source)
    else:
        st.caption("暂无来源映射。")

    if meta:
        st.subheader("生成元信息")
        st.write(f"mode: `{meta.get('mode', '')}`")
        st.write(f"retry: `{meta.get('retry_applied', False)}`")
