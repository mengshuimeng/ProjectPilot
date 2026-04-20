from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.chunker import split_paragraphs

CANONICAL_PROJECT_NAME = "基于改进Yolo和PCBNet的景区行人重识别系统"

PROJECT_NAME_ALIASES = [
    "基于改进Yolo和PCBNet的景区行人重识别系统",
    "基于改进Yolo 和PCBNet 的景区行人重识别系统",
    "基于 Web 的景区行人重识别系统",
    "基于Web的景区行人重识别系统",
    "基于Web的智能行人重识别系统",
]

GENERIC_FIELD_KEYWORDS = {
    "background": ["背景", "意义", "现状", "需求", "研究现状", "应用价值", "项目背景", "problem", "motivation"],
    "pain_points": ["痛点", "问题", "不足", "挑战", "难点", "效率低", "分散", "瓶颈", "pain", "challenge"],
    "target_users": ["用户", "对象", "受众", "客户", "管理", "教师", "学生", "企业", "target user"],
    "system_architecture": ["架构", "流程", "方案", "技术路线", "pipeline", "architecture", "workflow", "模块关系"],
    "innovation_points": ["创新", "改进", "优势", "特色", "亮点", "贡献", "innovation", "novelty"],
    "experiment_results": ["实验", "结果", "评估", "测试", "准确率", "精度", "召回率", "mAP", "Rank-1", "指标"],
    "deliverables": ["成果", "交付", "产物", "输出", "功能", "实现", "deliverable", "artifact"],
    "limitations": ["不足", "局限", "问题", "限制", "风险", "缺陷", "limitation"],
    "future_work": ["未来", "后续", "展望", "优化方向", "改进方向", "future work", "roadmap"],
}

TECH_VOCAB = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C++",
    "PyTorch",
    "TensorFlow",
    "OpenCV",
    "YOLOv8",
    "YOLO",
    "SENet",
    "ResNet50",
    "PCBNet",
    "Triplet Loss",
    "TriHard Loss",
    "ID Loss",
    "Flask",
    "FastAPI",
    "Django",
    "Vue",
    "React",
    "ECharts",
    "Spring Boot",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "Docker",
    "LLM",
    "RAG",
    "Harness",
    "Streamlit",
    "OpenAI",
    "DeepSeek",
    "Codex",
    "Cursor",
    "Claude Code",
]

GENERIC_MODULE_RULES = {
    "感知采集": ["传感器", "图像采集", "数据采集", "相机", "摄像头", "深度相机"],
    "智能识别": ["视觉识别", "目标检测", "图像识别", "异常判定", "模型识别", "AI识别"],
    "运动控制": ["运动控制", "底盘", "电机", "PID", "路径跟踪", "巡线"],
    "避障导航": ["避障", "导航", "定位", "路径规划", "北斗", "里程计"],
    "通信传输": ["通信", "WiFi", "4G", "蓝牙", "串口", "消息传输"],
    "平台管理": ["平台", "任务管理", "报警", "工单", "报表", "历史记录"],
    "数据展示": ["可视化", "图表", "展示", "看板", "统计分析"],
    "模型训练与推理": ["训练", "模型", "推理", "TensorRT", "部署"],
    "用户交互": ["界面", "前端", "页面", "APP", "小程序", "Web"],
    "数据管理": ["数据库", "存储", "数据表", "记录", "同步"],
}

NOISE_PATTERNS = [
    r"^\s*目录\s*$",
    r"^\s*致\s*谢\s*$",
    r"^致\s*谢\b",
    r"致\s*谢\s+不经意",
    r"^\s*thanks\s*$",
    r"新疆大学本科毕业论文（设计）",
    r"^\s*第\s*[一二三四五六七八九十\d]+\s*章\b",
    r"上一章|本章节|本章将|本章主要",
    r"项目负责人.*任务分工",
    r"姓名\s+学号\s+学院",
    r"联系电话\s+任务分工\s+签名",
    r"||Rank\s*（?\d|query\s*图片|AP[:：]?\s*平均精度",
    r"^\s*图\s*\d+[\-\.]?\d*",
    r"^\s*表\s*\d+[\-\.]?\d*",
    r"^\s*\d+\s*$",
    r"^\s*[-=]{3,}\s*$",
    r"^\s*[A-Za-z]?\s*=\s*.+",
    r"^\s*\(\s*\d+\s*\)\s*$",
]


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def strip_outline_markers(text: str) -> str:
    cleaned = normalize_text(text)
    for _ in range(3):
        before = cleaned
        cleaned = re.sub(r"^\s*第\s*[一二三四五六七八九十\d]+\s*章\s*", "", cleaned)
        cleaned = re.sub(r"^\s*\d+(?:\.\d+){0,4}\s*", "", cleaned)
        cleaned = re.sub(
            r"^(作品概述|作品简介|项目概述|项目简介|需求分析|开发背景|技术方案|方案实现|测试报告|应用前景|当前应用情况|核心功能)\s*",
            "",
            cleaned,
        )
        if cleaned == before:
            break
    return cleaned.strip()


def _compact_name(text: str) -> str:
    return normalize_text(text).replace(" ", "").replace("：", ":")


def normalize_project_name(name: str) -> str:
    compact = _compact_name(name)
    alias_map = {_compact_name(alias): CANONICAL_PROJECT_NAME for alias in PROJECT_NAME_ALIASES}
    return alias_map.get(compact, normalize_text(name))


def is_known_project_alias(name: str) -> bool:
    return normalize_project_name(name) == CANONICAL_PROJECT_NAME


def _symbol_digit_ratio(text: str) -> float:
    chars = [char for char in text if not char.isspace()]
    if not chars:
        return 1.0
    noisy = [char for char in chars if char.isdigit() or char in "=+-*/()[]{}<>|\\_^~`.,;:%"]
    return len(noisy) / len(chars)


def is_noise_paragraph(paragraph: str) -> bool:
    text = normalize_text(paragraph)
    if not text:
        return True
    lower = text.lower()
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    if len(text) <= 8 and _symbol_digit_ratio(text) > 0.55:
        return True
    if len(text) <= 20 and any(token in lower for token in ["copyright", "page"]):
        return True
    if len(text) > 30 and _symbol_digit_ratio(text) > 0.5:
        return True
    return False


def clean_document_text(text: str) -> str:
    cleaned: list[str] = []
    for paragraph in split_paragraphs(text):
        lines = []
        for line in paragraph.splitlines():
            line = normalize_text(line)
            if not is_noise_paragraph(line):
                lines.append(line)
        para = normalize_text(" ".join(lines))
        if para and not is_noise_paragraph(para):
            cleaned.append(para)
    return "\n\n".join(dict.fromkeys(cleaned))


def prepare_documents(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for doc in docs:
        raw_text = str(doc.get("text", ""))
        cleaned_text = clean_document_text(raw_text)
        new_doc = dict(doc)
        new_doc["role"] = doc.get("role", "supporting")
        new_doc["raw_char_count"] = int(doc.get("char_count", len(raw_text)))
        new_doc["text"] = cleaned_text
        new_doc["char_count"] = len(cleaned_text)
        new_doc["paragraph_count"] = len(split_paragraphs(cleaned_text))
        prepared.append(new_doc)
    return prepared


def _clean_name_candidate(candidate: str) -> str:
    candidate = strip_outline_markers(candidate)
    candidate = re.sub(r"^#+\s*", "", candidate)
    candidate = re.sub(r"^(?:项目名称|课题名称|项目名|系统名称|论文题目|题目|名称)\s*[:：]\s*", "", candidate)
    candidate = candidate.replace("**", "").replace("《", "").replace("》", "")
    for marker in [
        "项目类型",
        "申请人",
        "学生姓名",
        "所属院系",
        "所在学院",
        "专 业",
        "专业",
        "PPT 提纲",
        "PPT提纲",
        "项目背景",
        "背景",
        "痛点",
        "目标用户",
        "技术路线",
        "系统架构",
        "创新点",
        "交付成果",
        "摘要",
        "关键词",
        "作者",
        "指导教师",
    ]:
        if marker in candidate:
            candidate = candidate.split(marker, 1)[0]
    candidate = candidate.strip()
    candidate = re.split(r"[;；]\s*[\u4e00-\u9fff]{2,4}(?:[;；]|\s*$)", candidate, maxsplit=1)[0].strip()
    for alias in PROJECT_NAME_ALIASES:
        if _compact_name(alias) in _compact_name(candidate):
            return alias
    title_match = re.match(r"(.{4,80}?(?:系统|平台|项目|方案|机器人|装置|设备|工具|助手))\s+[\u4e00-\u9fff]{2,4}$", candidate)
    if title_match:
        candidate = title_match.group(1)
    return candidate.strip(" ：:-")


def _is_bad_project_name_candidate(candidate: str) -> bool:
    text = normalize_text(candidate)
    if not text:
        return True
    bad_markers = ["摘要", "关键词", "参考文献", "心得体会", "指导教师", "作者", "姓名", "学号"]
    if any(marker in text for marker in bad_markers):
        return True
    if re.search(r"[\u4e00-\u9fff]{2,4}[;；][\u4e00-\u9fff]{2,4}", text):
        return True
    if len(text) > 80 or len(text) < 4:
        return True
    if not any(token in text for token in ["项目", "系统", "平台", "工具", "助手", "方案", "机器人", "装置", "设备"]):
        return True
    return False


def _project_name_score(candidate: str, role: str = "supporting") -> int:
    score = 8 if role == "anchor" else 2
    for token in ["项目", "系统", "平台", "机器人", "装置", "设备", "方案"]:
        if token in candidate:
            score += 3
    for token in ["基于", "智能", "识别", "管理", "检测", "分拣", "助手"]:
        if token in candidate:
            score += 1
    if len(candidate) <= 35:
        score += 2
    return score


def extract_project_name_from_text(text: str, fallback_name: str = "") -> str:
    search_text = strip_outline_markers(text)
    patterns = [
        r"(?:项目名称|课题名称|项目名|系统名称|论文题目|题目|名称)[:：]\s*([^\n]{4,120})",
        r"《([^》]{4,90})》",
        r"^#\s+(.{4,80})$",
        r"([A-Za-z0-9\u4e00-\u9fff\s+/\-]{4,80}(?:系统|平台|工具|助手|方案|项目))\s*(?:是|为)",
    ]
    for pattern in patterns:
        match = re.search(pattern, search_text, flags=re.MULTILINE)
        if not match:
            continue
        candidate = _clean_name_candidate(match.group(1))
        if not _is_bad_project_name_candidate(candidate) and not is_noise_paragraph(candidate):
            return normalize_project_name(candidate)

    for line in search_text.splitlines()[:50]:
        candidate = _clean_name_candidate(line)
        if not _is_bad_project_name_candidate(candidate):
            return normalize_project_name(candidate)
    return fallback_name


def _anchor_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors = [doc for doc in docs if doc.get("role") == "anchor"]
    return anchors or docs[:1]


def collect_project_name_candidates(docs: list[dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for doc in docs:
        name = extract_project_name_from_text(str(doc.get("text", "")), fallback_name="")
        if name:
            candidates.append(name)

    all_text = "\n".join(str(doc.get("text", "")) for doc in docs)
    for alias in PROJECT_NAME_ALIASES:
        if _compact_name(alias) in _compact_name(all_text):
            candidates.append(alias)

    return list(dict.fromkeys(normalize_text(candidate) for candidate in candidates if candidate))


def select_project_name(docs: list[dict[str, Any]]) -> tuple[str, list[str]]:
    candidates = collect_project_name_candidates(docs)
    if candidates:
        normalized = [normalize_project_name(candidate) for candidate in candidates]
        for candidate in normalized:
            if candidate == CANONICAL_PROJECT_NAME:
                return CANONICAL_PROJECT_NAME, candidates
        anchor_candidate = extract_project_name_from_text(str(_anchor_docs(docs)[0].get("text", "")), "")
        if anchor_candidate:
            return normalize_project_name(anchor_candidate), candidates
        scored = sorted(
            ((candidate, _project_name_score(candidate)) for candidate in normalized if not _is_bad_project_name_candidate(candidate)),
            key=lambda item: item[1],
            reverse=True,
        )
        if scored:
            return scored[0][0], candidates
        project_name, _ = Counter(normalized).most_common(1)[0]
        return project_name, candidates

    anchor = _anchor_docs(docs)[0] if docs else {}
    fallback = str(anchor.get("name", "未识别项目")).rsplit(".", 1)[0]
    return fallback or "未识别项目", candidates


def score_paragraph(paragraph: str, keywords: list[str]) -> int:
    lower = paragraph.lower()
    return sum(lower.count(keyword.lower()) for keyword in keywords)


def summarize_candidate(paragraph: str, max_chars: int = 220) -> str:
    text = strip_outline_markers(re.sub(r"^#+\s*", "", paragraph))
    pieces = re.split(r"(?<=[。！？；.!?])", text)
    summary = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(summary) + len(piece) <= max_chars:
            summary += piece
        elif not summary:
            summary = piece[:max_chars].rstrip()
            break
    return summary or text[:max_chars].rstrip()


def _role_weight(role: str) -> float:
    return 3.0 if role == "anchor" else 1.0


def collect_field_snippets(
    docs: list[dict[str, Any]],
    keywords: list[str],
    limit: int = 4,
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, str, str, str]] = []
    for doc in docs:
        source = str(doc.get("name", ""))
        role = str(doc.get("role", "supporting"))
        for para in split_paragraphs(str(doc.get("text", ""))):
            if is_noise_paragraph(para):
                continue
            score = score_paragraph(para, keywords)
            if score > 0:
                weighted_score = score * _role_weight(role)
                candidates.append((weighted_score, source, role, summarize_candidate(para)))

    candidates.sort(key=lambda item: (item[0], item[2] == "anchor", -len(item[3])), reverse=True)

    selected: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for score, source, role, text in candidates:
        if text in seen_texts:
            continue
        selected.append({"source": source, "role": role, "text": text, "score": round(score, 3)})
        seen_texts.add(text)
        if len(selected) >= limit:
            break
    return selected


def _join_snippets(snippets: list[dict[str, Any]], max_chars: int = 620) -> str:
    text = "；".join(str(item.get("text", "")) for item in snippets if item.get("text"))
    return text[:max_chars].rstrip("；,， ")


def infer_project_type(docs: list[dict[str, Any]]) -> str:
    text = "\n".join(str(doc.get("text", "")) for doc in _anchor_docs(docs))
    lower = text.lower()
    rules = [
        ("硬件 / IoT 项目", ["硬件", "传感器", "单片机", "嵌入式", "iot", "物联网", "stm32", "巡检小车"]),
        ("AI / 算法项目", ["深度学习", "模型", "训练", "算法", "神经网络", "machine learning", "ai"]),
        ("Web / 软件系统", ["web", "前端", "后端", "接口", "数据库", "系统平台", "管理系统"]),
        ("数据分析项目", ["数据分析", "可视化", "统计", "dashboard", "报表"]),
        ("课程/科研项目", ["课程", "论文", "研究", "实验", "课题"]),
    ]
    for project_type, keywords in rules:
        if any(keyword.lower() in lower for keyword in keywords):
            return project_type
    return "通用项目"


def extract_technologies(docs: list[dict[str, Any]], limit: int = 18) -> list[str]:
    all_text = "\n".join(str(doc.get("text", "")) for doc in docs)
    found: list[str] = []
    for tech in TECH_VOCAB:
        if tech.lower() in all_text.lower():
            found.append(tech)

    regex_terms = re.findall(r"\b[A-Z][A-Za-z0-9.+#-]{1,20}\b(?:\s+[A-Z][A-Za-z0-9.+#-]{1,20}\b)?", all_text)
    for term in regex_terms:
        if term in {"The", "This", "And", "For", "With", "From", "Slide"}:
            continue
        if len(term) <= 2 and term not in {"AI", "UI"}:
            continue
        if term not in found:
            found.append(term)
        if len(found) >= limit:
            break
    return found[:limit]


def extract_modules(docs: list[dict[str, Any]], limit: int = 14) -> list[str]:
    all_text = "\n".join(str(doc.get("text", "")) for doc in docs)
    found: list[str] = []
    for module_name, keywords in GENERIC_MODULE_RULES.items():
        if any(keyword.lower() in all_text.lower() for keyword in keywords):
            found.append(module_name)

    heading_candidates = re.findall(r"(?:^|\n)#{1,4}\s*([^\n]{2,30})", all_text)
    list_candidates = re.findall(r"(?:模块|功能|页面|子系统)[:：]\s*([^\n。；]{2,30})", all_text)
    colon_candidates = re.findall(r"([\u4e00-\u9fffA-Za-z0-9+/\- ]{2,20}(?:层|模块|部分|系统|平台|单元))[:：]", all_text)
    for candidate in heading_candidates + list_candidates + colon_candidates:
        candidate = strip_outline_markers(candidate).strip("-：: ")
        if 2 <= len(candidate) <= 18 and candidate not in found and not is_noise_paragraph(candidate):
            found.append(candidate)
        if len(found) >= limit:
            break
    return found[:limit]


def build_profile(docs: list[dict[str, Any]]) -> dict[str, Any]:
    prepared_docs = prepare_documents(docs)
    anchor_docs = _anchor_docs(prepared_docs)
    supporting_docs = [doc for doc in prepared_docs if doc.get("role") == "supporting"]
    project_name, project_candidates = select_project_name(prepared_docs)

    field_sources: dict[str, list[dict[str, Any]]] = {}
    field_values: dict[str, str] = {}
    for field, keywords in GENERIC_FIELD_KEYWORDS.items():
        snippets = collect_field_snippets(prepared_docs, keywords)
        field_sources[field] = snippets
        field_values[field] = _join_snippets(snippets)

    profile: dict[str, Any] = {
        "anchor_document": anchor_docs[0].get("name", "") if anchor_docs else "",
        "supporting_documents": [doc.get("name", "") for doc in supporting_docs],
        "source_roles": {doc.get("name", ""): doc.get("role", "supporting") for doc in prepared_docs},
        "project_name": project_name,
        "project_type": infer_project_type(prepared_docs),
        "background": field_values.get("background", ""),
        "pain_points": field_values.get("pain_points", ""),
        "target_users": field_values.get("target_users", ""),
        "core_technologies": extract_technologies(prepared_docs),
        "system_architecture": field_values.get("system_architecture", ""),
        "system_modules": extract_modules(prepared_docs),
        "innovation_points": field_values.get("innovation_points", ""),
        "experiment_results": field_values.get("experiment_results", ""),
        "deliverables": field_values.get("deliverables", ""),
        "limitations": field_values.get("limitations", ""),
        "future_work": field_values.get("future_work", ""),
        "project_name_candidates": project_candidates,
        "field_sources": field_sources,
        "doc_stats": [
            {
                "name": doc.get("name", ""),
                "role": doc.get("role", "supporting"),
                "suffix": doc.get("suffix", ""),
                "parse_status": doc.get("parse_status", ""),
                "parse_warning": doc.get("parse_warning", ""),
                "raw_char_count": doc.get("raw_char_count", doc.get("char_count", 0)),
                "char_count": doc.get("char_count", 0),
                "paragraph_count": doc.get("paragraph_count", 0),
            }
            for doc in prepared_docs
        ],
    }

    # Compatibility keys for V1 commands, tests, and existing UI snippets.
    profile["background_summary"] = profile["background"]
    profile["pain_point_summary"] = profile["pain_points"]
    profile["innovation_summary"] = profile["innovation_points"]
    profile["experiment_summary"] = profile["experiment_results"]
    profile["application_scenarios"] = profile["target_users"]
    profile["pain_point"] = profile["pain_points"]
    profile["_field_sources"] = {
        field: [item["source"] for item in snippets] for field, snippets in field_sources.items()
    }
    profile["_project_name_candidates"] = project_candidates
    profile["_doc_stats"] = profile["doc_stats"]
    return profile
