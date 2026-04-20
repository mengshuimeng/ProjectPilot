from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.llm_client import get_llm_status
from app.tool_registry import convert_office_document, get_tool_status, search_local_files

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
