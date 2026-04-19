from __future__ import annotations

from pathlib import Path

from app.extractor import CANONICAL_PROJECT_NAME, build_profile
from app.generator import generate_output
from app.llm_client import LLMClient
from app.parser import load_documents, parse_document
from app.pipeline import run_all
from app.retriever import retrieve_evidence
from app.verifier import verify_profile


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_parser_reads_md_and_pdf() -> None:
    md_doc = parse_document(PROJECT_ROOT / "data" / "raw" / "project_notes.md")
    pdf_doc = parse_document(PROJECT_ROOT / "data" / "raw" / "dachuang_application.pdf")
    assert md_doc["char_count"] > 0
    assert pdf_doc["suffix"] == ".pdf"
    assert "text" in pdf_doc


def test_extractor_outputs_canonical_project_name() -> None:
    docs = load_documents(PROJECT_ROOT / "data" / "raw")
    profile = build_profile(docs)
    assert profile["project_name"] == CANONICAL_PROJECT_NAME


def test_retriever_returns_non_empty_evidence() -> None:
    docs = load_documents(PROJECT_ROOT / "data" / "raw")
    profile = build_profile(docs)
    evidence = retrieve_evidence("defense", profile, docs)
    assert evidence["task"] == "defense"
    assert evidence["chunks"]


def test_generator_fallback_outputs_string() -> None:
    docs = load_documents(PROJECT_ROOT / "data" / "raw")
    profile = build_profile(docs)
    content = generate_output(profile, "intro")
    assert isinstance(content, str)
    assert content


def test_llm_client_without_key_does_not_crash(monkeypatch) -> None:
    monkeypatch.delenv("PROJECTPILOT_API_KEY", raising=False)
    monkeypatch.setenv("PROJECTPILOT_LLM_ENABLED", "true")
    result = LLMClient().generate_text("system", "user")
    assert result["ok"] is False
    assert result["fallback"] is True


def test_verifier_returns_passed_key() -> None:
    docs = load_documents(PROJECT_ROOT / "data" / "raw")
    profile = build_profile(docs)
    report = verify_profile(profile, docs)
    assert isinstance(report, dict)
    assert "passed" in report


def test_runall_outputs_required_files(monkeypatch) -> None:
    monkeypatch.setenv("PROJECTPILOT_LLM_ENABLED", "false")
    run_all(PROJECT_ROOT)
    assert (PROJECT_ROOT / "outputs" / "intro.md").exists()
    assert (PROJECT_ROOT / "outputs" / "innovation.md").exists()
    assert (PROJECT_ROOT / "outputs" / "defense.md").exists()
