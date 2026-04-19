from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    fitz = None

TEXT_EXTS = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".csv"}


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception:
            return ""
    return ""


def read_pdf_file(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return ""
    if fitz is None:
        return "[PDF_PARSE_ERROR] PyMuPDF is not installed. Run: pip install -r requirements.txt"
    try:
        parts: list[str] = []
        with fitz.open(path) as doc:
            for page in doc:
                parts.append(page.get_text("text"))
        return "\n".join(parts).strip()
    except Exception as exc:
        return f"[PDF_PARSE_ERROR] {exc}"


def parse_document(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text = read_pdf_file(path)
    elif suffix in TEXT_EXTS:
        text = read_text_file(path)
    else:
        text = ""

    return {
        "name": path.name,
        "path": str(path),
        "suffix": suffix,
        "text": text,
        "char_count": len(text),
    }


def load_documents(raw_dir: Path) -> list[dict[str, Any]]:
    if not raw_dir.exists():
        return []

    docs: list[dict[str, Any]] = []
    for path in sorted(raw_dir.iterdir()):
        if path.is_file():
            docs.append(parse_document(path))
    return docs
