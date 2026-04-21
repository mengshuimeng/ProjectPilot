from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent
TMP_ROOT = PROJECT_ROOT / "data" / "sessions" / "_pytest_tmp"


@pytest.fixture
def tmp_path() -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TMP_ROOT / f"case-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
