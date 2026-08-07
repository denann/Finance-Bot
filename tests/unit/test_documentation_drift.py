"""Semantic contracts for the offline documentation drift gate."""

from __future__ import annotations

from scripts import check_docs


def test_documentation_drift_gate_passes_current_repository() -> None:
    assert check_docs.run_checks() == []


def test_command_environment_and_schema_inventories_are_canonical() -> None:
    public, compatibility, deprecated, hidden = check_docs.load_command_metadata()
    schemas = check_docs.load_sheet_schemas()

    assert len(public) == 65
    assert compatibility == deprecated == {
        "liabilities", "liability_add", "liability_update", "liability_off",
    }
    assert hidden == set()
    assert check_docs.extract_env_names() == check_docs.env_example_names()
    assert len(check_docs.extract_env_names()) == 36
    assert len(schemas) == 12
    assert sum(len(columns) for columns in schemas.values()) == 115


def test_beginner_environment_template_exposes_only_required_values() -> None:
    """Advanced overrides stay documented without burdening first-time setup."""

    assert check_docs.active_env_example_names() == {
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GEMINI_API_KEY",
    }


def test_manual_pdf_source_and_historical_policy_are_declared() -> None:
    source_truth = (check_docs.DOCS / "documentation-source-of-truth.md").read_text(encoding="utf-8")
    index = (check_docs.DOCS / "README.md").read_text(encoding="utf-8").lower()

    assert "docs/help_manual.md" in source_truth
    assert "scripts/generate_help_manual_pdf.py" in source_truth
    assert "historical audit and implementation records" in index
