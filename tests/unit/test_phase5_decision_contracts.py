"""Semantic checks for the Phase 5 architecture decision package."""

from __future__ import annotations

from pathlib import Path

from app.sheets.client import SHEET_SCHEMAS


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_current_decision_and_review_trigger_are_declared() -> None:
    adr = read("docs/architecture/adr-001-scale-and-persistence.md").lower()
    triggers = read("docs/architecture/scale-and-migration-triggers.md").lower()

    assert "keep google sheets, single user, and single process" in adr
    assert "review" in adr and "2027-01-12" in adr
    assert all(label in triggers for label in ("green", "amber", "red"))


def test_tenant_mode_cannot_be_enabled_by_current_config_or_schema() -> None:
    config = read("app/config.py").lower()
    assert "tenant_mode" not in config
    assert "tenant_id" not in config
    assert all("tenant_id" not in columns for columns in SHEET_SCHEMAS.values())


def test_future_reconciliation_and_staging_cover_all_current_worksheets() -> None:
    plan = read("docs/architecture/future-migration-and-tenant-plan.md")
    staging = read("docs/testing/phase-5-scale-staging.md")

    assert all(f"`{sheet}`" in plan for sheet in SHEET_SCHEMAS)
    assert all(size in staging for size in ("100", "1,000", "10,000", "25,000", "50,000", "100,000"))
    assert all(term in staging.lower() for term in ("scheduler", "restart", "reconciliation", "export", "privacy"))


def test_phase5_documents_are_indexed_and_do_not_claim_implementation() -> None:
    index = read("docs/README.md")
    future = read("docs/architecture/future-migration-and-tenant-plan.md").lower()
    required = (
        "phase-5-current-scale-boundary.md", "persistence-contract-assessment.md",
        "persistence-options.md", "scale-and-migration-triggers.md",
        "adr-001-scale-and-persistence.md", "future-migration-and-tenant-plan.md",
        "phase-5-scale-evidence.md", "phase-5-scale-staging.md",
    )
    assert all(name in index for name in required)
    assert "design only" in future
    assert "does not enable tenants" in future
