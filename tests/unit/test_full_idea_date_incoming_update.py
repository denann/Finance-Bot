from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import ast
import re
import sys
import types

from app.clock import freeze_business_time
from app.bot.handler_parts.transaction_flow import attach_split_bill_if_any
from app.nlp.normalizer import extract_amount_from_text
from app.nlp.parse_safety import CLARIFICATION, assess_parse_safety, detect_pre_parse_clarification_flags
from app.nlp.regex_parser import detect_date_result, parse_debt_input, parse_with_regex


FROZEN = datetime(2026, 8, 9, 9, 0, tzinfo=ZoneInfo("Asia/Jakarta"))


def test_natural_absolute_dates_honor_year_and_beat_day_only_prefix():
    with freeze_business_time(FROZEN):
        assert detect_date_result("4 Juli 2025").value == "2025-07-04"
        assert detect_date_result("tgl 4 Juli 2025").value == "2025-07-04"
        assert detect_date_result("tanggal 4 Juli 2025").value == "2025-07-04"
        assert detect_date_result("4 Juli").value == "2026-07-04"
        assert detect_date_result("tgl 30").value == "2026-08-30"
        invalid = detect_date_result("31 Februari 2026")
        assert invalid.status == "invalid" and invalid.value is None


def test_historical_concrete_month_date_does_not_become_false_pending_but_future_does():
    with freeze_business_time(FROZEN):
        historical = "Transfer dari Annisa 183.615k 4 Juli 2025 via BSI"
        flags, _ = detect_pre_parse_clarification_flags(historical)
        assert "possible_pending_expense" not in flags

        future = "Transfer dari Annisa 183.615k 4 Juli 2027 via BSI"
        future_flags, _ = detect_pre_parse_clarification_flags(future)
        assert "possible_pending_expense" in future_flags

        future_claimed_actual = "Sudah transfer dari Annisa 183.615k 4 Juli 2027 via BSI"
        claimed_flags, _ = detect_pre_parse_clarification_flags(future_claimed_actual)
        assert "possible_pending_expense" in claimed_flags

        planned = "Transfer dari Annisa bulan depan 183k via BSI"
        assert assess_parse_safety(planned, parse_with_regex(planned) or {})["recommended_action"] == CLARIFICATION


def test_pending_preview_edit_invalid_date_cannot_survive_as_raw_save_value():
    source = Path("app/bot/handler_parts/transaction_flow.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"_strip_preview_edit_value", "_parse_preview_edit_pair"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    ns = {
        "re": re,
        "PREVIEW_EDIT_KEY_ALIASES": {"date": "date", "tanggal": "date"},
        "parse_human_amount": lambda value: float(extract_amount_from_text(value) or 0),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "transaction_flow.py", "exec"), ns)
    parse_pair = ns["_parse_preview_edit_pair"]
    assert parse_pair("date=31 Februari 2026") == {}
    assert parse_pair("date=4 Juli 2025") == {"date": "2025-07-04"}


def test_clear_incoming_transfer_is_income_without_swallowing_financial_contrasts(monkeypatch):
    from app.nlp import regex_parser

    monkeypatch.setattr(regex_parser, "get_runtime_account_snapshot", lambda: (("Cash", "BCA", "BSI", "DANA", "GoPay", "Seabank"), True))
    with freeze_business_time(FROZEN):
        incoming = "Transfer dari Annisa 183.615k 4 Juli 2025 via BSI"
        parsed = parse_with_regex(incoming)
        assert parsed["type"] == "income"
        assert parsed["amount"] == 183615
        assert parsed["date"] == "2025-07-04"
        assert parsed["account"] == "BSI"
        assert assess_parse_safety(incoming, parsed)["recommended_action"] != CLARIFICATION

        settlement = parse_debt_input("Annisa bayar hutang 183k")
        assert settlement and settlement["intent"] == "add_payment"

        borrowing = parse_debt_input("saya pinjam 183k dari Budi")
        assert borrowing and borrowing["intent"] == "add_payable"

        own_transfer = parse_with_regex("transfer 183k dari BCA ke DANA")
        assert own_transfer["type"] == "transfer"
        assert own_transfer["account"] == "BCA" and own_transfer["to_account"] == "DANA"


def test_actual_message_routing_keeps_debt_before_parse_safety():
    source = Path("app/bot/handler_parts/message_handlers.py").read_text(encoding="utf-8")
    early_debt = source.index("early_debt_parsed = parse_debt_input(user_text)")
    pre_safety = source.index("pre_parse_assessment = assess_parse_safety(user_text, {})")
    assert early_debt < pre_safety


def test_amount_regressions_stay_intact():
    assert extract_amount_from_text("183.615k") == 183615
    assert extract_amount_from_text("183,615k") == 183615
    assert extract_amount_from_text("1.5jt") == 1500000
    assert extract_amount_from_text("1,5 juta") == 1500000


def test_explicit_split_after_bayar_keeps_subject_out_of_person_routing():
    """Keep explicit utility split inputs out of person-payment ambiguity."""

    for subject in ("pam", "air"):
        raw = f"Bayar {subject} 199.200k dibagi 4 sama alpat opik sapto tanggal 20"
        parsed = parse_with_regex(raw)
        assert parsed is not None
        attach_split_bill_if_any(parsed, raw)

        pre_flags = assess_parse_safety(raw, {})["risk_flags"]
        parsed_flags = assess_parse_safety(raw, parsed)["risk_flags"]
        assert "person_plus_bayar_without_debt_keyword" not in pre_flags
        assert "split_participants_missing" not in parsed_flags
        assert parsed["subject"] == subject.title()
        assert parsed["split_bill"]["person_names"] == ["Alpat", "Opik", "Sapto"]


def test_incoming_person_grammar_defers_to_full_and_runtime_own_account_names(monkeypatch):
    from app.nlp import regex_parser

    multiword = parse_with_regex("Transfer dari Sea Bank 183k ke DANA")
    assert multiword["type"] == "transfer"
    assert str(multiword["account"]).lower().replace(" ", "") == "seabank"
    assert multiword["to_account"] == "DANA"

    monkeypatch.setattr(regex_parser, "get_runtime_account_snapshot", lambda: (("Blu", "DANA"), True))
    runtime = regex_parser.parse_with_regex("Transfer dari Blu 183k ke DANA")
    assert runtime["type"] == "transfer"
    assert runtime["account"] == "Blu"
    assert runtime["to_account"] == "DANA"

    person = regex_parser.parse_with_regex("Transfer dari Annisa 183k ke DANA")
    assert person["type"] == "income"


def test_single_parse_uses_one_runtime_account_snapshot_even_if_provider_would_change(monkeypatch):
    from app.nlp import regex_parser

    calls = []
    responses = [
        ["Blu", "DANA"],
        ["Cash", "BCA", "BSI", "DANA", "GoPay"],
    ]

    def changing_accounts():
        index = min(len(calls), len(responses) - 1)
        calls.append(index)
        return list(responses[index])

    def changing_snapshot():
        return tuple(changing_accounts()), True

    monkeypatch.setattr(regex_parser, "get_runtime_account_snapshot", changing_snapshot)
    parsed = regex_parser.parse_with_regex("Transfer dari Blu 183k ke DANA")

    assert parsed["type"] == "transfer"
    assert parsed["account"] == "Blu"
    assert parsed["to_account"] == "DANA"
    assert calls == [0]


def test_single_parse_does_not_reread_runtime_accounts_after_classification(monkeypatch):
    from app.nlp import regex_parser

    calls = 0

    def first_read_only():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("runtime account provider was re-read within one parse")
        return ["My Wallet", "DANA"]

    def first_snapshot_only():
        return tuple(first_read_only()), True

    monkeypatch.setattr(regex_parser, "get_runtime_account_snapshot", first_snapshot_only)
    parsed = regex_parser.parse_with_regex("Transfer dari MyWallet 183k ke DANA")

    assert parsed["type"] == "transfer"
    assert parsed["account"] == "My Wallet"
    assert parsed["to_account"] == "DANA"
    assert calls == 1


def test_degraded_runtime_account_snapshot_fails_closed_without_breaking_healthy_person_income(monkeypatch):
    from app.nlp import regex_parser

    fallback = ("Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "Seabank")
    monkeypatch.setattr(regex_parser, "get_runtime_account_snapshot", lambda: (fallback, False))

    degraded = regex_parser.parse_with_regex("Transfer dari Blu 183k ke DANA")
    assert degraded["type"] == "ambiguous"
    assert degraded["parse_ambiguity"] == "runtime_account_source_unavailable"
    safety = assess_parse_safety("Transfer dari Blu 183k ke DANA", degraded)
    assert safety["recommended_action"] == CLARIFICATION
    assert "runtime_account_source_unavailable" in safety["risk_flags"]

    built_in = regex_parser.parse_with_regex("Transfer dari BCA 183k ke DANA")
    assert built_in["type"] == "transfer"
    assert built_in["account"] == "BCA" and built_in["to_account"] == "DANA"

    monkeypatch.setattr(regex_parser, "get_runtime_account_snapshot", lambda: (fallback, True))
    person = regex_parser.parse_with_regex("Transfer dari Annisa 183k ke DANA")
    assert person["type"] == "income"


def test_resolver_account_snapshot_preserves_provider_provenance_without_changing_legacy_fallback():
    source = Path("app/services/resolver_service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_account_names_snapshot"
    )

    def fail_read(_sheet):
        raise RuntimeError("sheets down")

    defaults = ["Cash", "BCA", "DANA"]
    failed_ns = {
        "get_all_records": fail_read,
        "SHEET_ACCOUNTS": "accounts",
        "DEFAULT_ACCOUNT_NAMES": defaults,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), "resolver_service.py", "exec"), failed_ns)
    assert failed_ns["get_account_names_snapshot"]() == (defaults, False)

    healthy_ns = {
        "get_all_records": lambda _sheet: [{"account_name": "Blu"}, {"account_name": "DANA"}],
        "SHEET_ACCOUNTS": "accounts",
        "DEFAULT_ACCOUNT_NAMES": defaults,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), "resolver_service.py", "exec"), healthy_ns)
    assert healthy_ns["get_account_names_snapshot"]() == (["Blu", "DANA"], True)


def test_runtime_snapshot_threads_degraded_provenance_from_resolver(monkeypatch):
    from app.nlp import regex_parser

    fake_resolver = types.ModuleType("app.services.resolver_service")
    fake_resolver.get_account_names_snapshot = lambda: (["Cash", "BCA", "DANA"], False)
    monkeypatch.setitem(sys.modules, "app.services.resolver_service", fake_resolver)

    assert regex_parser.get_runtime_account_snapshot() == (("Cash", "BCA", "DANA"), False)
