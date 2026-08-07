"""Read Finance Bot JSON logs as a terminal table, summary, or Excel-ready CSV.

The application writes JSON Lines because that format is robust for machines and
safe for appending. This offline utility turns the same records into a format
that an owner can inspect without manually parsing raw JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "finance_bot.log"
DISPLAY_COLUMNS = (
    "timestamp",
    "event",
    "correlation_id",
    "transaction_id",
    "raw_input",
    "outcome",
    "error_type",
    "handler",
    "operation",
    "model",
    "duration_ms",
)


def load_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Load valid JSON object records and count malformed lines without failing.

    The bot may be stopped while writing the final line. Ignoring that one
    malformed line keeps owner inspection available while retaining a visible
    warning instead of silently treating it as an application event.
    """

    records: list[dict[str, Any]] = []
    malformed_lines = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                malformed_lines += 1
                continue
            if isinstance(value, dict):
                records.append(value)
            else:
                malformed_lines += 1
    return records, malformed_lines


def display_value(value: Any) -> str:
    """Make structured metadata readable in a fixed-width terminal cell."""

    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def local_timestamp(value: Any) -> str:
    """Format ISO UTC timestamps in Asia/Jakarta for the owner-facing table."""

    raw = str(value or "")
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.astimezone(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S WIB")
    except ValueError:
        return raw


def filtered_records(
    records: Iterable[dict[str, Any]], *, event: str | None, transaction_id: str | None, errors_only: bool
) -> list[dict[str, Any]]:
    """Filter records without changing their order or discarding metadata."""

    result = list(records)
    if event:
        result = [record for record in result if str(record.get("event", "")) == event]
    if transaction_id:
        result = [record for record in result if str(record.get("transaction_id", "")) == transaction_id]
    if errors_only:
        result = [record for record in result if record.get("error_type") or record.get("outcome") == "error"]
    return result


def table_rows(records: Iterable[dict[str, Any]], *, columns: Iterable[str]) -> list[list[str]]:
    """Build display rows while keeping raw records unchanged for CSV export."""

    rows: list[list[str]] = []
    for record in records:
        row: list[str] = []
        for column in columns:
            value = local_timestamp(record.get(column)) if column == "timestamp" else display_value(record.get(column))
            row.append(value)
        rows.append(row)
    return rows


def render_table(columns: Iterable[str], rows: Iterable[Iterable[str]], *, max_width: int = 36) -> str:
    """Render a dependency-free table suitable for a normal PowerShell window."""

    headers = [str(column) for column in columns]
    materialized_rows = [[str(value) for value in row] for row in rows]

    def clip(value: str, width: int) -> str:
        return value if len(value) <= width else f"{value[: max(1, width - 3)]}..."

    widths = [len(header) for header in headers]
    for row in materialized_rows:
        for index, value in enumerate(row):
            widths[index] = min(max(widths[index], len(value)), max_width)
    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [separator]
    lines.append("|" + "|".join(f" {clip(header, widths[index]).ljust(widths[index])} " for index, header in enumerate(headers)) + "|")
    lines.append(separator)
    for row in materialized_rows:
        lines.append("|" + "|".join(f" {clip(value, widths[index]).ljust(widths[index])} " for index, value in enumerate(row)) + "|")
    lines.append(separator)
    return "\n".join(lines)


def csv_columns(records: Iterable[dict[str, Any]]) -> list[str]:
    """Keep common operational fields first, then include discovered metadata."""

    seen = {column for record in records for column in record}
    preferred = [column for column in DISPLAY_COLUMNS if column in seen]
    return preferred + sorted(seen - set(preferred))


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    """Write all selected fields to UTF-8-with-BOM CSV for direct Excel use."""

    columns = csv_columns(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            row = {column: display_value(record.get(column)) for column in columns}
            writer.writerow(row)


def print_summary(records: list[dict[str, Any]]) -> None:
    """Print owner-facing event and error totals without exposing raw payloads."""

    events = Counter(str(record.get("event", "unknown_event")) for record in records)
    errors = Counter(str(record["error_type"]) for record in records if record.get("error_type"))
    print(f"Total event: {len(records)}")
    print("Event terbanyak:")
    for name, count in events.most_common(10):
        print(f"  {count:>4}  {name}")
    if errors:
        print("Error yang tercatat:")
        for name, count in errors.most_common(10):
            print(f"  {count:>4}  {name}")


def parse_args() -> argparse.Namespace:
    """Define the offline owner-facing log reader command-line interface."""

    parser = argparse.ArgumentParser(description="Tampilkan log Finance Bot sebagai tabel atau CSV yang rapi.")
    parser.add_argument("--file", type=Path, default=DEFAULT_LOG_PATH, help="Path file JSON log.")
    parser.add_argument("--limit", type=int, default=30, help="Jumlah event terbaru untuk tabel (default: 30).")
    parser.add_argument("--event", help="Tampilkan hanya nama event ini.")
    parser.add_argument("--transaction-id", help="Tampilkan hanya event untuk ID transaksi ini.")
    parser.add_argument("--errors-only", action="store_true", help="Tampilkan hanya event error.")
    parser.add_argument("--summary", action="store_true", help="Tampilkan ringkasan jumlah event dan error.")
    parser.add_argument("--csv", type=Path, help="Tulis seluruh hasil filter ke CSV yang siap dibuka di Excel.")
    parser.add_argument("--all-fields", action="store_true", help="Sertakan semua field yang ada pada tabel terminal.")
    return parser.parse_args()


def main() -> int:
    """Run the offline reader without importing or starting the bot."""

    args = parse_args()
    path = args.file if args.file.is_absolute() else PROJECT_ROOT / args.file
    if not path.exists():
        print(f"File log belum ditemukan: {path}")
        print("Jalankan bot terlebih dahulu, atau gunakan --file untuk memilih lokasi lain.")
        return 1
    if args.limit < 1:
        print("--limit harus minimal 1.")
        return 2

    records, malformed_lines = load_records(path)
    selected = filtered_records(
        records,
        event=args.event,
        transaction_id=args.transaction_id,
        errors_only=args.errors_only,
    )
    if args.summary:
        print_summary(selected)
    if args.csv:
        output_path = args.csv if args.csv.is_absolute() else PROJECT_ROOT / args.csv
        write_csv(output_path, selected)
        print(f"CSV dibuat: {output_path} ({len(selected)} event)")
    if not args.summary or args.all_fields:
        columns = csv_columns(selected) if args.all_fields else list(DISPLAY_COLUMNS)
        print(render_table(columns, table_rows(selected[-args.limit :], columns=columns)))
        print(f"Menampilkan {min(len(selected), args.limit)} dari {len(selected)} event terpilih.")
    if malformed_lines:
        print(f"Peringatan: {malformed_lines} baris log tidak valid dilewati.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
