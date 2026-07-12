"""Offline semantic documentation drift checks for Finance Bot.

The checker reads Python sources with AST where possible and imports only the
pure command registry. It never initializes Telegram, gspread, Gemini, or HTTP
clients. Failures include the affected path and a practical correction.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CURRENT_DOCS = (
    "01-project-overview.md", "02-architecture.md", "03-data-model.md",
    "04-user-flows.md", "05-safety-and-confirmation.md", "06-google-sheets.md",
    "07-ai-and-gemini.md", "08-configuration-and-deployment.md",
    "09-function-reference.md", "10-maintenance.md", "testing.md",
    "operations/runbook.md", "help_manual.md", "documentation-source-of-truth.md",
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
COMMAND_RE = re.compile(r"(?<![\w/])/([a-z][a-z0-9_]*)", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts and ".pytest_cache" not in path.parts)


def extract_env_names() -> set[str]:
    """Return literal environment names consumed by application Python code."""

    names: set[str] = set()
    for path in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            function_name = ""
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            is_environ_get = (
                function_name == "get"
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"environ", "os_environ"}
            )
            if function_name not in {"getenv", "_parse_int_env", "_parse_float_env", "_parse_bool_env"} and not is_environ_get:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
    return names


def env_example_names() -> set[str]:
    names = set()
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=", line.strip())
        if match:
            names.add(match.group(1))
    return names


def load_command_metadata() -> tuple[set[str], set[str], set[str], set[str]]:
    sys.path.insert(0, str(ROOT))
    from app.bot.command_registry import (  # pylint: disable=import-outside-toplevel
        COMPATIBILITY_COMMANDS,
        DEPRECATED_COMMANDS,
        HIDDEN_COMMANDS,
        INTERNAL_TESTING_COMMANDS,
        PUBLIC_COMMANDS,
    )

    return set(PUBLIC_COMMANDS), set(COMPATIBILITY_COMMANDS), set(DEPRECATED_COMMANDS), set(HIDDEN_COMMANDS) | set(INTERNAL_TESTING_COMMANDS)


def load_sheet_schemas() -> dict[str, list[str]]:
    """Extract `SHEET_SCHEMAS` safely from the module AST without importing gspread."""

    config_tree = ast.parse((ROOT / "app/config.py").read_text(encoding="utf-8"))
    names: dict[str, str] = {}
    for node in config_tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id.startswith("SHEET_") and isinstance(node.value, ast.Constant):
                names[node.targets[0].id] = str(node.value.value)

    tree = ast.parse((ROOT / "app/sheets/client.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "SHEET_SCHEMAS" for target in node.targets):
            result: dict[str, list[str]] = {}
            assert isinstance(node.value, ast.Dict)
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Name) and isinstance(value, ast.List):
                    result[names[key.id]] = [str(item.value) for item in value.elts if isinstance(item, ast.Constant)]
            return result
    raise RuntimeError("SHEET_SCHEMAS not found")


def check_links(errors: list[str]) -> None:
    for path in markdown_files():
        if "audit" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            clean = target.split("#", 1)[0].strip().strip("<>")
            if not clean or re.match(r"^[a-z]+://", clean) or clean.startswith("mailto:"):
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: unresolved link `{target}`")


def check_headings_and_paths(errors: list[str]) -> None:
    for path in markdown_files():
        if "audit" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        headings = [re.sub(r"\s+#+$", "", heading).strip().lower() for heading in HEADING_RE.findall(text)]
        duplicates = [heading for heading, count in Counter(headings).items() if count > 1]
        if duplicates:
            errors.append(f"{path.relative_to(ROOT)}: duplicate headings: {', '.join(duplicates)}")
        if "app/app/" in text.replace("\\", "/"):
            errors.append(f"{path.relative_to(ROOT)}: obsolete `app/app/` path")


def check_index(errors: list[str]) -> None:
    index = (DOCS / "README.md").read_text(encoding="utf-8")
    for relative in CURRENT_DOCS:
        if relative not in index:
            errors.append(f"docs/README.md: missing primary document `{relative}`")
    required_notice = "historical audit and implementation records"
    if required_notice not in index.lower():
        errors.append("docs/README.md: docs/audit historical-source notice is missing")


def check_commands(errors: list[str]) -> None:
    public, compatibility, deprecated, hidden = load_command_metadata()
    surfaces = {
        "help": (ROOT / "app/bot/handler_parts/help_content.py").read_text(encoding="utf-8"),
        "manual": (DOCS / "help_manual.md").read_text(encoding="utf-8"),
    }
    covered = set().union(*(set(COMMAND_RE.findall(text)) for text in surfaces.values()))
    missing = public - covered
    if missing:
        errors.append(f"command coverage: public commands missing from help/manual: {', '.join(sorted(missing))}")
    advertised_hidden = hidden & covered
    if advertised_hidden:
        errors.append(f"command coverage: hidden/internal commands advertised: {', '.join(sorted(advertised_hidden))}")
    registry_commands = public | compatibility | deprecated | hidden
    documented = set(COMMAND_RE.findall("\n".join(surfaces.values())))
    allowed_words = {"command", "commands"}
    orphan = documented - registry_commands - allowed_words
    if orphan:
        errors.append(f"command coverage: documented commands absent from registry: {', '.join(sorted(orphan))}")
    manual = surfaces["manual"].lower()
    for command in compatibility | deprecated:
        if f"/{command}" in manual and not re.search(rf"(?:compatib|deprecated|tidak lagi)[^\n]*`?/{re.escape(command)}`,?", manual):
            errors.append(f"docs/help_manual.md: /{command} must be labeled compatibility/deprecated")


def check_environment(errors: list[str]) -> None:
    supported = extract_env_names()
    example = env_example_names()
    missing = supported - example
    extra = example - supported
    if missing:
        errors.append(f".env.example: missing supported variables: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f".env.example: variables not found in application sources: {', '.join(sorted(extra))}")
    config_doc = (DOCS / "08-configuration-and-deployment.md")
    if config_doc.exists():
        text = config_doc.read_text(encoding="utf-8")
        undocumented = supported - set(re.findall(r"`([A-Z][A-Z0-9_]*)`", text))
        if undocumented:
            errors.append(f"{config_doc.relative_to(ROOT)}: undocumented variables: {', '.join(sorted(undocumented))}")


def check_schemas(errors: list[str]) -> None:
    path = DOCS / "03-data-model.md"
    if not path.exists():
        errors.append("docs/03-data-model.md: missing schema documentation")
        return
    text = path.read_text(encoding="utf-8")
    for sheet, columns in load_sheet_schemas().items():
        if f"`{sheet}`" not in text:
            errors.append(f"docs/03-data-model.md: missing worksheet `{sheet}`")
        for column in columns:
            if f"`{column}`" not in text:
                errors.append(f"docs/03-data-model.md: `{sheet}` missing column `{column}`")


def check_policy_and_privacy(errors: list[str]) -> None:
    current_paths = [DOCS / name for name in CURRENT_DOCS if (DOCS / name).exists()] + [ROOT / "README.md"]
    for path in current_paths:
        text = path.read_text(encoding="utf-8")
        if re.search(r"\b\d{2,4}\s+passed\b", text, re.IGNORECASE) and "dated" not in text.lower() and "verification date" not in text.lower():
            errors.append(f"{path.relative_to(ROOT)}: test count must be labeled as a dated snapshot")
    all_docs = "\n".join(path.read_text(encoding="utf-8") for path in markdown_files())
    secret_patterns = (
        r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b",
        r"\bAIza[A-Za-z0-9_-]{20,}\b",
        r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    )
    for pattern in secret_patterns:
        if re.search(pattern, all_docs):
            errors.append("documentation: possible raw credential or private key found")
            break
    source_truth = (DOCS / "documentation-source-of-truth.md").read_text(encoding="utf-8")
    if "docs/help_manual.md" not in source_truth or "scripts/generate_help_manual_pdf.py" not in source_truth:
        errors.append("documentation-source-of-truth.md: generated PDF source/command not declared")
    manual = (DOCS / "help_manual.md").read_text(encoding="utf-8").lower()
    if "contoh" in manual and not any(word in manual for word in ("fiktif", "synthetic", "dummy")):
        errors.append("docs/help_manual.md: examples must be identified as fictional/dummy data")


def run_checks() -> list[str]:
    errors: list[str] = []
    check_links(errors)
    check_headings_and_paths(errors)
    check_index(errors)
    check_commands(errors)
    check_environment(errors)
    check_schemas(errors)
    check_policy_and_privacy(errors)
    return errors


def print_inventory() -> None:
    public, compatibility, deprecated, hidden = load_command_metadata()
    print(f"public_commands={len(public)}")
    print(f"compatibility_commands={len(compatibility)}")
    print(f"deprecated_commands={len(deprecated)}")
    print(f"hidden_internal_commands={len(hidden)}")
    print(f"environment_variables={len(extract_env_names())}")
    schemas = load_sheet_schemas()
    print(f"worksheets={len(schemas)}")
    print(f"worksheet_columns={sum(len(columns) for columns in schemas.values())}")
    print(f"markdown_files={len(markdown_files())}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Finance Bot documentation without external services.")
    parser.add_argument("--inventory", action="store_true", help="Print canonical inventory counts before checking.")
    args = parser.parse_args()
    if args.inventory:
        print_inventory()
    errors = run_checks()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Documentation checks failed: {len(errors)} issue(s).")
        return 1
    print("Documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
