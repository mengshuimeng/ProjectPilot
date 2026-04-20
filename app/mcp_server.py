from __future__ import annotations

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
            "然后使用 `python -m app.mcp_server` 启动 ProjectPilot MCP server。"
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


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
