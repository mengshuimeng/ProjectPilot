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

FIELD_KEYWORDS = {
    "background_summary": ["背景", "意义", "现状", "需求", "研究现状", "应用价值"],
    "pain_point_summary": ["痛点", "问题", "不足", "挑战", "难点", "效率低", "分散"],
    "target_users": ["用户", "景区", "游客", "管理", "安保", "管理人员"],
    "innovation_summary": ["创新", "改进", "优势", "特色", "亮点", "Harness", "校验", "证据"],
    "experiment_summary": ["实验", "结果", "准确率", "精度", "召回率", "mAP", "Rank-1"],
    "application_scenarios": ["应用", "场景", "景区", "安全", "行为分析", "答辩", "README"],
    "limitations": ["不足", "局限", "问题", "限制", "扫描版"],
    "future_work": ["未来", "后续", "展望", "优化方向", "接入"],
}

TECH_VOCAB = [
    "YOLOv8",
    "YOLO",
    "SENet",
    "ResNet50",
    "PCBNet",
    "Triplet Loss",
    "TriHard Loss",
    "ID Loss",
    "PyTorch",
    "Flask",
    "Vue",
    "ECharts",
    "Market-1501",
    "Ubuntu",
    "Codex",
    "Cursor",
    "Claude Code",
    "LLM",
    "Harness",
]

MODULE_RULES = {
    "多文档解析": ["PDF", "Markdown", "PPT", "文档读取", "解析"],
    "文本清洗与分块": ["清洗", "分块", "chunk", "脏文本"],
    "结构化项目画像": ["项目画像", "结构化", "profile", "字段"],
    "证据检索": ["证据", "检索", "来源", "retrieval", "evidence"],
    "LLM 生成": ["LLM", "生成", "提示词", "prompt"],
    "自动校验与重试": ["校验", "验证", "重试", "反馈闭环", "verify"],
    "行人检测": ["检测", "YOLO"],
    "行人重识别": ["重识别", "ReID", "PCBNet"],
    "特征提取": ["特征提取", "ResNet", "特征向量"],
    "前端可视化": ["前端", "Vue", "ECharts"],
    "后端接口": ["后端", "Flask", "接口"],
}

NOISE_PATTERNS = [
    r"^\s*目录\s*$",
    r"^\s*致\s*谢\s*$",
    r"^致\s*谢\b",
    r"致\s*谢\s+不经意",
    r"^\s*thanks\s*$",
    r"新疆大学本科毕业论文（设计）",
    r"^\s*第[一二三四五六七八九十\d]+章\b",
    r"上一章|本章节|本章将|本章主要",
    r"^\s*图\s*\d+[\-\.]?\d*",
    r"^\s*表\s*\d+[\-\.]?\d*",
    r"^\s*\d+\s*$",
    r"^\s*[-=]{3,}\s*$",
    r"^\s*[A-Za-z]?\s*=\s*.+",
    r"^\s*\(\s*\d+\s*\)\s*$",
]

SOURCE_PRIORITY = {
    "project_notes.md": 3.0,
    "README_source.md": 2.8,
    "ppt_outline.md": 2.4,
    "dachuang_application.pdf": 1.8,
    "reid_thesis.pdf": 0.8,
}


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


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
    if len(text) > 30 and _symbol_digit_ratio(text) > 0.55:
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
        new_doc["raw_char_count"] = int(doc.get("char_count", len(raw_text)))
        new_doc["text"] = cleaned_text
        new_doc["char_count"] = len(cleaned_text)
        new_doc["paragraph_count"] = len(split_paragraphs(cleaned_text))
        prepared.append(new_doc)
    return prepared


def extract_project_name_from_text(text: str) -> str:
    def clean_name_candidate(candidate: str) -> str:
        candidate = normalize_text(candidate)
        candidate = re.sub(r"^#+\s*", "", candidate)
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
        ]:
            if marker in candidate:
                candidate = candidate.split(marker, 1)[0]
        for alias in PROJECT_NAME_ALIASES:
            if _compact_name(alias) in _compact_name(candidate):
                return alias
        return candidate.strip(" ：:-")

    patterns = [
        r"(?:项目名称|课题名称|项目名)[:：]\s*([^\n]{6,120})",
        r"《([^》]{6,80})》",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = clean_name_candidate(match.group(1))
            if "基于" in candidate and ("系统" in candidate or "识别" in candidate):
                return candidate

    for line in text.splitlines()[:40]:
        line = clean_name_candidate(line)
        if 8 <= len(line) <= 60 and "ProjectPilot：" in line:
            return line
    return ""


def collect_project_name_candidates(docs: list[dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    all_text = "\n".join(str(doc.get("text", "")) for doc in docs)

    for doc in docs:
        name = extract_project_name_from_text(str(doc.get("text", "")))
        if name:
            candidates.append(name)

    for alias in PROJECT_NAME_ALIASES:
        if _compact_name(alias) in _compact_name(all_text):
            candidates.append(alias)

    return list(dict.fromkeys(normalize_text(candidate) for candidate in candidates if candidate))


def select_project_name(docs: list[dict[str, Any]]) -> tuple[str, list[str]]:
    raw_candidates = collect_project_name_candidates(docs)
    if not raw_candidates:
        return CANONICAL_PROJECT_NAME, []

    normalized_candidates = [normalize_project_name(candidate) for candidate in raw_candidates]
    if CANONICAL_PROJECT_NAME in normalized_candidates:
        return CANONICAL_PROJECT_NAME, raw_candidates

    project_name, _ = Counter(normalized_candidates).most_common(1)[0]
    return project_name, raw_candidates


def score_paragraph(paragraph: str, keywords: list[str]) -> int:
    lower = paragraph.lower()
    return sum(lower.count(keyword.lower()) for keyword in keywords)


def summarize_candidate(paragraph: str, max_chars: int = 220) -> str:
    text = normalize_text(re.sub(r"^#+\s*", "", paragraph))
    pieces = re.split(r"(?<=[。！？；])", text)
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


def collect_field_snippets(
    docs: list[dict[str, Any]],
    keywords: list[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, str, str]] = []

    for doc in docs:
        source = str(doc.get("name", ""))
        for para in split_paragraphs(str(doc.get("text", ""))):
            if is_noise_paragraph(para):
                continue
            score = score_paragraph(para, keywords)
            if score > 0:
                weighted_score = score * SOURCE_PRIORITY.get(source, 1.0)
                candidates.append((weighted_score, source, summarize_candidate(para)))

    candidates.sort(key=lambda item: (item[0], -len(item[2])), reverse=True)

    selected: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for score, source, text in candidates:
        if text in seen_texts:
            continue
        selected.append({"source": source, "text": text, "score": score})
        seen_texts.add(text)
        if len(selected) >= limit:
            break

    return selected


def extract_technologies(docs: list[dict[str, Any]]) -> list[str]:
    all_text = "\n".join(str(doc.get("text", "")) for doc in docs)
    found: list[str] = []
    for tech in TECH_VOCAB:
        if tech.lower() in all_text.lower():
            found.append(tech)
    return found


def extract_modules(docs: list[dict[str, Any]]) -> list[str]:
    all_text = "\n".join(str(doc.get("text", "")) for doc in docs)
    found: list[str] = []
    for module_name, keywords in MODULE_RULES.items():
        if any(keyword.lower() in all_text.lower() for keyword in keywords):
            found.append(module_name)
    return found


def _join_snippets(snippets: list[dict[str, Any]]) -> str:
    text = "；".join(str(item.get("text", "")) for item in snippets if item.get("text"))
    return text[:520].rstrip("；,， ")


def build_profile(docs: list[dict[str, Any]]) -> dict[str, Any]:
    prepared_docs = prepare_documents(docs)
    project_name, project_candidates = select_project_name(prepared_docs)

    field_sources: dict[str, list[dict[str, Any]]] = {}
    field_values: dict[str, str] = {}
    for field, keywords in FIELD_KEYWORDS.items():
        snippets = collect_field_snippets(prepared_docs, keywords)
        field_sources[field] = snippets
        field_values[field] = _join_snippets(snippets)

    profile: dict[str, Any] = {
        "project_name": project_name or CANONICAL_PROJECT_NAME,
        "core_technologies": extract_technologies(prepared_docs),
        "system_modules": extract_modules(prepared_docs),
        "background_summary": field_values.get("background_summary", ""),
        "pain_point_summary": field_values.get("pain_point_summary", ""),
        "innovation_summary": field_values.get("innovation_summary", ""),
        "experiment_summary": field_values.get("experiment_summary", ""),
        "application_scenarios": field_values.get("application_scenarios", ""),
        "target_users": field_values.get("target_users", ""),
        "limitations": field_values.get("limitations", ""),
        "future_work": field_values.get("future_work", ""),
        "project_name_candidates": project_candidates,
        "field_sources": field_sources,
        "doc_stats": [
            {
                "name": doc.get("name", ""),
                "suffix": doc.get("suffix", ""),
                "raw_char_count": doc.get("raw_char_count", doc.get("char_count", 0)),
                "char_count": doc.get("char_count", 0),
                "paragraph_count": doc.get("paragraph_count", 0),
            }
            for doc in prepared_docs
        ],
    }

    # Compatibility keys for the first rule-based version and older tests.
    profile["background"] = profile["background_summary"]
    profile["pain_point"] = profile["pain_point_summary"]
    profile["innovation_points"] = profile["innovation_summary"]
    profile["experiment_results"] = profile["experiment_summary"]
    profile["_field_sources"] = {
        field: [item["source"] for item in snippets] for field, snippets in field_sources.items()
    }
    profile["_project_name_candidates"] = project_candidates
    profile["_doc_stats"] = profile["doc_stats"]
    return profile
