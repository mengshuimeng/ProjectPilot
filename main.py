from __future__ import annotations

import argparse
from pathlib import Path

from app.llm_client import get_llm_status
from app.parser import COMPAT_EXTS, STABLE_EXTS, load_documents
from app.pipeline import run_all, run_extract, run_generate, run_verify
from app.tool_registry import get_tool_status

PROJECT_ROOT = Path(__file__).resolve().parent


def cmd_status() -> None:
    docs = load_documents(PROJECT_ROOT / "data" / "raw")
    non_empty = [doc for doc in docs if int(doc.get("char_count", 0)) > 0]
    anchor = next((doc for doc in docs if doc.get("role") == "anchor"), {})
    supporting = [doc for doc in docs if doc.get("role") == "supporting"]
    stable_count = len([doc for doc in docs if doc.get("suffix") in STABLE_EXTS and doc.get("parse_status") == "parsed"])
    compat_count = len([doc for doc in docs if doc.get("suffix") in COMPAT_EXTS])
    failed_count = len([doc for doc in docs if doc.get("parse_status") in {"unsupported", "parse_error", "parse_warning"} and not doc.get("text")])
    llm_status = get_llm_status()

    print("ProjectPilot 状态检查")
    print(f"原始文档数量: {len(docs)}")
    print(f"非空文件数量: {len(non_empty)}")
    print(f"anchor document: {anchor.get('name', '未识别')}")
    print(f"supporting documents 数量: {len(supporting)}")
    print(f"稳定解析文件数: {stable_count}")
    print(f"兼容格式文件数: {compat_count}")
    print(f"解析失败/未支持文件数: {failed_count}")
    print(f"当前模式: {llm_status['mode']}")
    print(f"LLM 模型: {llm_status['model']}")
    if llm_status.get("reason"):
        print(f"LLM 状态说明: {llm_status['reason']}")
    for doc in docs:
        role = doc.get("role", "supporting")
        status = doc.get("parse_status", "")
        warning = f" | warning: {doc.get('parse_warning')}" if doc.get("parse_warning") else ""
        print(f"- [{role}] {doc['name']} | {status} | {doc['char_count']} chars{warning}")


def cmd_doctor() -> None:
    print("ProjectPilot Doctor")
    llm_status = get_llm_status()
    raw_files = [path for path in (PROJECT_ROOT / "data" / "raw").glob("*") if path.is_file() and not path.name.startswith(".")]
    docs = load_documents(PROJECT_ROOT / "data" / "raw")
    anchor = next((doc for doc in docs if doc.get("role") == "anchor"), {})
    parse_warnings = [doc for doc in docs if doc.get("parse_warning")]
    required_skills = [
        PROJECT_ROOT / "skills" / "project_schema.md",
        PROJECT_ROOT / "skills" / "writing_rules.md",
        PROJECT_ROOT / "skills" / "source_priority.md",
    ]
    required_prompts = [
        PROJECT_ROOT / "prompts" / "system_role.md",
        PROJECT_ROOT / "prompts" / "intro_generator.md",
        PROJECT_ROOT / "prompts" / "innovation_generator.md",
        PROJECT_ROOT / "prompts" / "defense_generator.md",
        PROJECT_ROOT / "prompts" / "retry_repair.md",
    ]

    print(f"- raw 文件: {len(raw_files)} 个")
    print(f"- anchor 存在: {bool(anchor)}")
    print(f"- anchor: {anchor.get('name', '未识别')}")
    print(f"- supporting 数量: {len([doc for doc in docs if doc.get('role') == 'supporting'])}")
    print(f"- parse warnings: {len(parse_warnings)}")
    for doc in parse_warnings:
        print(f"  - {doc.get('name')}: {doc.get('parse_warning')}")
    print(f"- skills 完整: {all(path.exists() for path in required_skills)}")
    print(f"- prompts 完整: {all(path.exists() for path in required_prompts)}")
    print(f"- LLM enabled: {llm_status['enabled']}")
    print(f"- LLM available: {llm_status['available']}")
    print(f"- API base: {llm_status['api_base']}")
    print(f"- model: {llm_status['model']}")
    if llm_status.get("reason"):
        print(f"- fallback 原因: {llm_status['reason']}")
    tool_status = get_tool_status()
    print(f"- 本地工具数量: {len(tool_status['tools'])}")
    print(f"- Office 转换可用: {tool_status['office_convert_available']}")
    print(f"- MCP server connected: {tool_status['mcp_server_connected']}")
    print(f"- MCP 说明: {tool_status['mcp_note']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ProjectPilot CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="查看当前文档和 LLM 状态")
    subparsers.add_parser("doctor", help="检查 raw 文件、skills、prompts 和 LLM 配置")
    subparsers.add_parser("extract", help="抽取结构化项目画像")
    subparsers.add_parser("verify", help="运行校验")

    generate_parser = subparsers.add_parser("generate", help="生成输出")
    generate_parser.add_argument("--type", required=True, choices=["intro", "innovation", "defense", "readme"])

    subparsers.add_parser("runall", help="一次性执行 extract / verify / generate")

    args = parser.parse_args()

    if args.command in (None, "status"):
        cmd_status()
    elif args.command == "doctor":
        cmd_doctor()
    elif args.command == "extract":
        profile = run_extract(PROJECT_ROOT)
        print("已完成结构化抽取。")
        print(f"anchor document: {profile.get('anchor_document') or '未识别'}")
        print(f"supporting documents 数量: {len(profile.get('supporting_documents', []))}")
        print(f"项目名称: {profile.get('project_name') or '未识别'}")
        print(f"项目类型: {profile.get('project_type') or '未识别'}")
        print(f"核心技术数量: {len(profile.get('core_technologies', []))}")
        print(f"系统模块数量: {len(profile.get('system_modules', []))}")
        print(f"profile 路径: {PROJECT_ROOT / 'data' / 'processed' / 'profile.json'}")
    elif args.command == "verify":
        report = run_verify(PROJECT_ROOT)
        print("校验完成。")
        print(f"passed: {report['passed']}")
        print(f"warnings: {len(report.get('warnings', []))}")
        print(f"infos: {len(report.get('infos', []))}")
        for warning in report.get("warnings", []):
            print(f"- warning: {warning}")
        for info in report.get("infos", []):
            print(f"- info: {info}")
        print(f"report 路径: {PROJECT_ROOT / 'data' / 'processed' / 'verify_report.json'}")
    elif args.command == "generate":
        result = run_generate(PROJECT_ROOT, args.type)
        print("生成完成。")
        print(f"输出路径: {result['output_path']}")
        print(f"meta 路径: {result['meta_path']}")
        print(f"evidence 路径: {result['evidence_path']}")
        print(f"verify report 路径: {result['verify_report_path']}")
    elif args.command == "runall":
        result = run_all(PROJECT_ROOT)
        print("全流程执行完成。")
        print(f"documents: {result['paths']['documents']}")
        print(f"profile: {result['paths']['profile']}")
        print(f"verify_report: {result['paths']['verify_report']}")
        for output_type, generated in result["generated"].items():
            print(f"{output_type}: {generated['output_path']}")
            print(f"{output_type} meta: {generated['meta_path']}")
            print(f"{output_type} evidence: {generated['evidence_path']}")


if __name__ == "__main__":
    main()
