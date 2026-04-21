from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.llm_client import get_llm_status
from app.pipeline import run_extract, run_generate, run_verify
from app.retriever import retrieve_evidence
from app.tool_registry import (
    build_project_knowledge_map,
    compact_profile_summary,
    convert_office_document,
    get_tool_status,
    search_local_files,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised when optional dependency is absent.
    FastMCP = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def _require_mcp() -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "缺少 mcp 依赖。请先运行 `pip install -r requirements.txt`，"
            "然后使用 `python -m app.mcp_server --check` 检查 ProjectPilot MCP server。"
        ) from IMPORT_ERROR
    return FastMCP


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _processed_dir(root: Path) -> Path:
    if (root / "session.json").exists() or root.parent.name == "sessions":
        return root / "processed"
    return root / "data" / "processed"


def _workspace_root(workspace: str = "") -> Path:
    if not workspace:
        return PROJECT_ROOT
    candidate = Path(workspace)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    return candidate


def _load_context(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile_path = _processed_dir(root) / "profile.json"
    documents_path = _processed_dir(root) / "documents.json"
    if not profile_path.exists() or not documents_path.exists():
        profile = run_extract(root)
    else:
        profile = dict(_load_json(profile_path))
    docs_payload = _load_json(documents_path)
    return profile, list(docs_payload.get("documents", []))


def create_server() -> Any:
    fast_mcp = _require_mcp()
    server = fast_mcp("ProjectPilot")

    @server.tool()
    def projectpilot_status() -> dict[str, Any]:
        """Return ProjectPilot workspace, LLM, and local tool status."""
        raw_dir = PROJECT_ROOT / "data" / "raw"
        raw_files = [
            {"name": path.name, "path": str(path), "suffix": path.suffix.lower(), "size": path.stat().st_size}
            for path in sorted(raw_dir.glob("*"))
            if path.is_file() and not path.name.startswith(".")
        ]
        return {
            "project_root": str(PROJECT_ROOT),
            "raw_file_count": len(raw_files),
            "raw_files": raw_files,
            "llm_status": get_llm_status(),
            "tool_status": get_tool_status(),
        }

    @server.tool()
    def search_project_files(query: str = "", suffixes: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Search files in the ProjectPilot workspace by name and suffix."""
        suffix_set = {
            suffix.strip().lower() if suffix.strip().startswith(".") else f".{suffix.strip().lower()}"
            for suffix in suffixes.split(",")
            if suffix.strip()
        }
        return search_local_files(PROJECT_ROOT, query=query, suffixes=suffix_set or None, limit=limit)

    @server.tool()
    def search_raw_materials(query: str = "", suffixes: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Search uploaded/raw project materials."""
        suffix_set = {
            suffix.strip().lower() if suffix.strip().startswith(".") else f".{suffix.strip().lower()}"
            for suffix in suffixes.split(",")
            if suffix.strip()
        }
        return search_local_files(PROJECT_ROOT / "data" / "raw", query=query, suffixes=suffix_set or None, limit=limit)

    @server.tool()
    def convert_office_material(path: str, target_ext: str) -> dict[str, Any]:
        """Convert legacy doc/ppt files to docx/pptx through local LibreOffice."""
        return convert_office_document(Path(path), target_ext)

    @server.tool()
    def extract_project_profile(workspace: str = "") -> dict[str, Any]:
        """Run extract and return a compact project profile summary."""
        root = _workspace_root(workspace)
        profile = run_extract(root)
        return {
            "workspace": str(root),
            "profile": compact_profile_summary(profile),
        }

    @server.tool()
    def retrieve_task_evidence_mcp(task: str, workspace: str = "", limit: int = 8) -> dict[str, Any]:
        """Retrieve task evidence with anchor-priority hybrid lexical+semantic scoring."""
        root = _workspace_root(workspace)
        profile, docs = _load_context(root)
        evidence = retrieve_evidence(task, profile, docs, limit=limit)
        return {
            "workspace": str(root),
            "task": task,
            "retrieval_mode": evidence.get("retrieval_mode", ""),
            "semantic_index_summary": evidence.get("semantic_index_summary", {}),
            "chunks": evidence.get("chunks", []),
            "role_summary": evidence.get("role_summary", {}),
            "source_summary": evidence.get("source_summary", {}),
        }

    @server.tool()
    def verify_project_materials(workspace: str = "") -> dict[str, Any]:
        """Run verifier and return the current verify report."""
        root = _workspace_root(workspace)
        report = run_verify(root)
        return {"workspace": str(root), "report": report}

    @server.tool()
    def project_knowledge_map(workspace: str = "") -> dict[str, Any]:
        """Build a local project knowledge map from the extracted profile."""
        root = _workspace_root(workspace)
        profile, _ = _load_context(root)
        return {"workspace": str(root), "knowledge_map": build_project_knowledge_map(profile)}

    @server.tool()
    def orchestrate_project_task(task: str = "defense", workspace: str = "", generate: bool = False) -> dict[str, Any]:
        """Compose extract, evidence retrieval, verify, and optional generation as one MCP workflow tool."""
        root = _workspace_root(workspace)
        profile = run_extract(root)
        docs_payload = _load_json(_processed_dir(root) / "documents.json")
        docs = list(docs_payload.get("documents", []))
        evidence = retrieve_evidence(task, profile, docs)
        verify_report = run_verify(root)
        response: dict[str, Any] = {
            "workspace": str(root),
            "task": task,
            "profile": compact_profile_summary(profile),
            "evidence": {
                "retrieval_mode": evidence.get("retrieval_mode", ""),
                "semantic_index_summary": evidence.get("semantic_index_summary", {}),
                "role_summary": evidence.get("role_summary", {}),
                "source_summary": evidence.get("source_summary", {}),
                "chunks": evidence.get("chunks", [])[:6],
            },
            "verify_report": verify_report,
        }
        if generate:
            generated = run_generate(root, task)
            response["generated"] = {
                "output_path": generated.get("output_path", ""),
                "meta_path": generated.get("meta_path", ""),
                "evidence_path": generated.get("evidence_path", ""),
            }
        return response

    return server


def _server_summary() -> dict[str, Any]:
    return {
        "name": "ProjectPilot",
        "transport": "stdio",
        "project_root": str(PROJECT_ROOT),
        "tools": [
            "projectpilot_status",
            "search_project_files",
            "search_raw_materials",
            "convert_office_material",
            "extract_project_profile",
            "retrieve_task_evidence_mcp",
            "verify_project_materials",
            "project_knowledge_map",
            "orchestrate_project_task",
        ],
        "client_command": "python",
        "client_args": ["-m", "app.mcp_server", "--stdio"],
    }


def _print_manual_usage() -> None:
    summary = _server_summary()
    print("ProjectPilot MCP server 已就绪。")
    print()
    print("这是一个 stdio MCP server，通常由支持 MCP 的客户端启动。")
    print("不要在普通终端里直接输入空行；MCP 客户端会通过 stdin/stdout 发送 JSON-RPC 消息。")
    print()
    print("客户端配置示例：")
    print(json.dumps({"command": summary["client_command"], "args": summary["client_args"]}, ensure_ascii=False, indent=2))
    print()
    print("本地自检命令：")
    print("python -m app.mcp_server --check")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ProjectPilot stdio MCP server")
    parser.add_argument("--check", action="store_true", help="只检查 MCP server 是否可创建，不进入 stdio 循环")
    parser.add_argument("--stdio", action="store_true", help="强制进入 stdio MCP server 模式")
    args = parser.parse_args(argv)

    if args.check:
        create_server()
        print(json.dumps(_server_summary(), ensure_ascii=False, indent=2))
        return

    if not args.stdio and sys.stdin.isatty():
        _print_manual_usage()
        return

    try:
        create_server().run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        return


if __name__ == "__main__":
    main()
