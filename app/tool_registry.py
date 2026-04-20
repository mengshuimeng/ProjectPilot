from __future__ import annotations

import shutil
import subprocess
import tempfile
import importlib.util
from pathlib import Path
from typing import Any


def list_tools() -> list[dict[str, str]]:
    return [
        {
            "name": "local_file_search",
            "type": "local_tool",
            "description": "在本地工作区中按文件名或扩展名检索项目材料。",
        },
        {
            "name": "office_convert",
            "type": "local_tool",
            "description": "通过本地 LibreOffice 将旧版 doc/ppt 转换为 docx/pptx。",
        },
    ]


def _find_libreoffice() -> str:
    for command in ("soffice", "libreoffice"):
        found = shutil.which(command)
        if found:
            return found
    windows_candidates = [
        Path("C:/Program Files/LibreOffice/program/soffice.exe"),
        Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
    ]
    for candidate in windows_candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def get_tool_status() -> dict[str, Any]:
    office = _find_libreoffice()
    mcp_package_available = importlib.util.find_spec("mcp") is not None
    mcp_server_path = Path(__file__).resolve().parent / "mcp_server.py"
    return {
        "tools": list_tools(),
        "mcp_server_connected": False,
        "mcp_server_available": mcp_server_path.exists(),
        "mcp_package_available": mcp_package_available,
        "mcp_server_command": "python -m app.mcp_server",
        "mcp_note": "已提供 stdio MCP server 入口 `python -m app.mcp_server`；是否连接取决于外部 MCP 客户端配置。",
        "office_convert_available": bool(office),
        "office_convert_command": office,
    }


def search_local_files(root: Path, query: str = "", suffixes: set[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    query_lower = query.lower().strip()
    suffixes = {suffix.lower() for suffix in suffixes} if suffixes else set()
    results: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        if query_lower and query_lower not in path.name.lower():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        results.append({"name": path.name, "path": str(path), "suffix": path.suffix.lower(), "size": size})
        if len(results) >= limit:
            break
    return results


def convert_office_document(path: Path, target_ext: str) -> dict[str, Any]:
    office = _find_libreoffice()
    if not office:
        return {
            "ok": False,
            "converted_path": "",
            "warning": "未检测到 LibreOffice，无法自动转换旧版 doc/ppt。",
            "tool": "office_convert",
        }

    convert_to = "docx" if target_ext == ".docx" else "pptx"
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="projectpilot_convert_"))
        result = subprocess.run(
            [
                office,
                "--headless",
                "--convert-to",
                convert_to,
                "--outdir",
                str(temp_dir),
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            return {
                "ok": False,
                "converted_path": "",
                "warning": f"LibreOffice 转换失败：{detail}",
                "tool": "office_convert",
            }
        converted = temp_dir / f"{path.stem}{target_ext}"
        if not converted.exists():
            matches = list(temp_dir.glob(f"*{target_ext}"))
            converted = matches[0] if matches else converted
        if not converted.exists():
            return {
                "ok": False,
                "converted_path": "",
                "warning": "LibreOffice 转换后未找到目标文件。",
                "tool": "office_convert",
            }
        return {
            "ok": True,
            "converted_path": str(converted),
            "warning": "",
            "tool": "office_convert",
        }
    except Exception as exc:
        return {
            "ok": False,
            "converted_path": "",
            "warning": f"LibreOffice 转换异常：{exc}",
            "tool": "office_convert",
        }
