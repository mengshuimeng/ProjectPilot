from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.extractor import build_profile, prepare_documents
from app.generator import generate_artifact, repair_artifact
from app.parser import load_documents
from app.retriever import retrieve_evidence
from app.verifier import verify_profile

APP_ROOT = Path(__file__).resolve().parent.parent


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _processed_dir(project_root: Path) -> Path:
    if (project_root / "session.json").exists() or project_root.parent.name == "sessions":
        return project_root / "processed"
    return project_root / "data" / "processed"


def _outputs_dir(project_root: Path) -> Path:
    return project_root / "outputs"


def _raw_dir(project_root: Path) -> Path:
    if (project_root / "session.json").exists() or project_root.parent.name == "sessions":
        return project_root / "raw"
    return project_root / "data" / "raw"


def _prompt_root(project_root: Path) -> Path:
    return project_root if (project_root / "prompts").exists() else APP_ROOT


def _manifest_path(project_root: Path) -> Path:
    return _processed_dir(project_root) / "input_manifest.json"


def _load_input_manifest(project_root: Path) -> dict[str, Any]:
    path = _manifest_path(project_root)
    if path.exists():
        return dict(_load_json(path))
    return {}


def _raw_files(project_root: Path) -> list[Path]:
    raw_dir = _raw_dir(project_root)
    if not raw_dir.exists():
        return []
    return [path for path in raw_dir.rglob("*") if path.is_file() and not path.name.startswith(".")]


def _processed_is_fresh(project_root: Path) -> bool:
    processed_dir = _processed_dir(project_root)
    profile_path = processed_dir / "profile.json"
    documents_path = processed_dir / "documents.json"
    if not profile_path.exists() or not documents_path.exists():
        return False

    raw_files = _raw_files(project_root)
    if not raw_files:
        return False

    manifest = _load_input_manifest(project_root)
    try:
        profile = dict(_load_json(profile_path))
        documents_payload = dict(_load_json(documents_path))
    except Exception:
        return False

    docs = list(documents_payload.get("documents", []))
    doc_names = {str(doc.get("name", "")) for doc in docs if doc.get("name")}

    manifest_anchor = str(manifest.get("anchor_document", "")).strip()
    if manifest_anchor and profile.get("anchor_document") != manifest_anchor:
        return False

    manifest_names = {manifest_anchor, *list(manifest.get("supporting_documents", []))}
    manifest_names = {name for name in manifest_names if name}
    if manifest_names and doc_names != manifest_names:
        return False

    raw_names = {path.name for path in raw_files}
    if not manifest_names and doc_names != raw_names:
        return False
    if manifest_names and not manifest_names.issubset(raw_names):
        return False

    input_paths = raw_files + ([_manifest_path(project_root)] if _manifest_path(project_root).exists() else [])
    newest_input = max(path.stat().st_mtime for path in input_paths)
    oldest_processed = min(profile_path.stat().st_mtime, documents_path.stat().st_mtime)
    return oldest_processed >= newest_input


def _load_processed_documents(project_root: Path) -> list[dict[str, Any]]:
    documents_path = _processed_dir(project_root) / "documents.json"
    if documents_path.exists() and _processed_is_fresh(project_root):
        payload = _load_json(documents_path)
        return list(payload.get("documents", []))
    run_extract(project_root)
    return list(_load_json(documents_path).get("documents", []))


def _load_or_create_profile(project_root: Path) -> dict[str, Any]:
    profile_path = _processed_dir(project_root) / "profile.json"
    if profile_path.exists() and _processed_is_fresh(project_root):
        return dict(_load_json(profile_path))
    return run_extract(project_root)


def _latest_output(project_root: Path) -> tuple[str, str]:
    outputs = []
    for path in _outputs_dir(project_root).glob("*.md"):
        if path.name.endswith("_meta.md"):
            continue
        outputs.append(path)
    if not outputs:
        return "", ""
    latest = max(outputs, key=lambda item: item.stat().st_mtime)
    return latest.stem, latest.read_text(encoding="utf-8")


def _should_retry(report: dict[str, Any]) -> bool:
    if report.get("noisy_output"):
        return True
    if report.get("repeated_phrases"):
        return True
    if report.get("unsupported_claims"):
        return True
    coverage = report.get("source_coverage_summary", {})
    if coverage and not coverage.get("ok", True):
        return True
    return False


def run_extract(project_root: Path) -> dict[str, Any]:
    raw_dir = _raw_dir(project_root)
    processed_dir = _processed_dir(project_root)
    manifest = _load_input_manifest(project_root)

    raw_docs = load_documents(raw_dir, anchor_name=manifest.get("anchor_document"))
    docs = prepare_documents(raw_docs)
    profile = build_profile(docs)
    session_path = project_root / "session.json"
    if session_path.exists():
        try:
            profile["session_id"] = str(_load_json(session_path).get("session_id", project_root.name))
        except Exception:
            profile["session_id"] = project_root.name

    _save_json(processed_dir / "documents.json", {"documents": docs})
    _save_json(processed_dir / "profile.json", profile)
    return profile


def run_verify(project_root: Path) -> dict[str, Any]:
    processed_dir = _processed_dir(project_root)

    docs = _load_processed_documents(project_root)
    profile = _load_or_create_profile(project_root)
    task, output_text = _latest_output(project_root)

    evidence_path = _outputs_dir(project_root) / f"{task}_evidence.json"
    meta_path = _outputs_dir(project_root) / f"{task}_meta.json"
    evidence = _load_json(evidence_path) if task and evidence_path.exists() else None
    used_sources: list[str] = []
    if meta_path.exists():
        meta = _load_json(meta_path)
        used_sources = list(meta.get("used_sources", []))
        used_roles = list(meta.get("used_roles", []))
    else:
        used_roles = []

    report = verify_profile(
        profile,
        docs,
        output_text=output_text,
        evidence=evidence,
        used_sources=used_sources,
        used_roles=used_roles,
        task=task,
    )
    _save_json(processed_dir / "verify_report.json", report)
    return report


def run_generate(project_root: Path, output_type: str) -> dict[str, Any]:
    output_type = output_type.lower()
    processed_dir = _processed_dir(project_root)
    outputs_dir = _outputs_dir(project_root)

    profile = _load_or_create_profile(project_root)
    docs = _load_processed_documents(project_root)

    evidence = retrieve_evidence(output_type, profile, docs)
    artifact = generate_artifact(profile, output_type, evidence=evidence, project_root=_prompt_root(project_root))

    initial_report = verify_profile(
        profile,
        docs,
        output_text=artifact["content"],
        evidence=evidence,
        used_sources=list(artifact.get("used_sources", [])),
        used_roles=list(artifact.get("used_roles", [])),
        task=output_type,
    )

    final_artifact = artifact
    retry_applied = False
    final_report = initial_report

    if _should_retry(initial_report):
        final_artifact = repair_artifact(
            artifact,
            profile,
            output_type,
            evidence,
            initial_report,
            project_root=_prompt_root(project_root),
        )
        retry_applied = True
        final_report = verify_profile(
            profile,
            docs,
            output_text=final_artifact["content"],
            evidence=evidence,
            used_sources=list(final_artifact.get("used_sources", [])),
            used_roles=list(final_artifact.get("used_roles", [])),
            task=output_type,
        )

    output_path = outputs_dir / f"{output_type}.md"
    evidence_path = outputs_dir / f"{output_type}_evidence.json"
    meta_path = outputs_dir / f"{output_type}_meta.json"
    report_path = processed_dir / "verify_report.json"

    meta = {
        "task": output_type,
        "session_id": profile.get("session_id", ""),
        "generation_mode": final_artifact.get("mode", "fallback"),
        "mode": final_artifact.get("mode", "fallback"),
        "fallback_reason": final_artifact.get("fallback_reason", ""),
        "fallback_detail": final_artifact.get("fallback_detail", ""),
        "used_sources": final_artifact.get("used_sources", []),
        "used_roles": final_artifact.get("used_roles", []),
        "anchor_document": profile.get("anchor_document", ""),
        "warnings_before_retry": initial_report.get("warnings", []),
        "retry_used": retry_applied or bool(final_artifact.get("retry_applied")),
        "notes": final_artifact.get("notes", []),
        "retry_applied": retry_applied or bool(final_artifact.get("retry_applied")),
        "retry_mode": final_artifact.get("retry_mode", ""),
        "paths": {
            "output": str(output_path),
            "meta": str(meta_path),
            "evidence": str(evidence_path),
            "verify_report": str(report_path),
        },
        "initial_verify_report": initial_report,
        "final_verify_report": final_report,
    }

    _write_text(output_path, final_artifact["content"])
    _save_json(evidence_path, evidence)
    _save_json(meta_path, meta)
    _save_json(report_path, final_report)

    return {
        "content": final_artifact["content"],
        "output_path": str(output_path),
        "meta_path": str(meta_path),
        "evidence_path": str(evidence_path),
        "verify_report_path": str(report_path),
        "meta": meta,
    }


def run_all(project_root: Path) -> dict[str, Any]:
    profile = run_extract(project_root)
    profile_report = run_verify(project_root)
    generated = {}
    for output_type in ("intro", "innovation", "defense", "readme"):
        generated[output_type] = run_generate(project_root, output_type)
    return {
        "profile": profile,
        "profile_report": profile_report,
        "generated": generated,
        "paths": {
            "documents": str(_processed_dir(project_root) / "documents.json"),
            "profile": str(_processed_dir(project_root) / "profile.json"),
            "verify_report": str(_processed_dir(project_root) / "verify_report.json"),
            "outputs": str(_outputs_dir(project_root)),
        },
    }
