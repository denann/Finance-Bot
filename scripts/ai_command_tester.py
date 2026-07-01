r"""
Tester command AI untuk Personal Finance Telegram Bot.

Tujuan:
- Testing parser dan flow command secara lokal, terpisah dari deployment.
- Tidak kirim pesan Telegram.
- Tidak menulis Google Sheets.
- Bisa membaca file .txt berisi banyak case yang dipisah `---`.
- Bisa membuat report Markdown agar gampang dibaca.

Contoh PowerShell:
  python scripts\ai_command_tester.py --input-file tests\input_Test.txt --decision unpaid --markdown report.md
  python scripts\ai_command_tester.py --input "Nasi kuning 22k dibagi 2 sama sapto 09-05-2026" --decision unpaid --json
  python scripts\ai_command_tester.py --sample --markdown report.md
"""
from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
import os
import re
import sys
import types
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Biar print di Windows tidak crash karena emoji/UTF-8 dari dependency.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

warnings.filterwarnings("ignore", category=FutureWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Environment lokal aman + stub import untuk dependency opsional
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_test_env() -> None:
    """Isi env dummy supaya import config tidak error saat testing lokal."""
    defaults = {
        "TELEGRAM_BOT_TOKEN": "TEST_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET": "TEST_SECRET",
        "ALLOWED_USER_ID": "0",
        "GOOGLE_SHEET_ID": "TEST_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON": "service_account.json",
        "WEBHOOK_URL": "https://example.test/webhook",
        "APP_PORT": "8000",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


class _Dummy:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __call__(self, *args: Any, **kwargs: Any) -> "_Dummy":
        return _Dummy(*args, **kwargs)

    def __iter__(self):
        return iter([])

    def __bool__(self) -> bool:
        return False


class _DummyBadRequest(Exception):
    pass


def _module_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _install_optional_import_stubs() -> None:
    """
    Biar tester tetap bisa jalan di environment ringan yang belum install semua
    dependency deployment. Stub hanya untuk import-time; fungsi write/deploy tidak dipakai.
    """
    if not _module_exists("dotenv"):
        dotenv_mod = types.ModuleType("dotenv")
        dotenv_mod.load_dotenv = lambda *args, **kwargs: None
        sys.modules.setdefault("dotenv", dotenv_mod)

    if not _module_exists("telegram"):
        telegram_mod = types.ModuleType("telegram")
        telegram_mod.Update = _Dummy
        telegram_mod.InputFile = _Dummy
        telegram_mod.InlineKeyboardButton = _Dummy
        telegram_mod.InlineKeyboardMarkup = _Dummy

        telegram_ext_mod = types.ModuleType("telegram.ext")
        telegram_ext_mod.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=_Dummy)
        for name in [
            "Application", "ApplicationBuilder", "CommandHandler", "MessageHandler",
            "CallbackQueryHandler", "filters",
        ]:
            setattr(telegram_ext_mod, name, _Dummy)

        telegram_helpers_mod = types.ModuleType("telegram.helpers")
        telegram_helpers_mod.escape_markdown = lambda text, *args, **kwargs: str(text or "")

        telegram_error_mod = types.ModuleType("telegram.error")
        telegram_error_mod.BadRequest = _DummyBadRequest

        sys.modules.setdefault("telegram", telegram_mod)
        sys.modules.setdefault("telegram.ext", telegram_ext_mod)
        sys.modules.setdefault("telegram.helpers", telegram_helpers_mod)
        sys.modules.setdefault("telegram.error", telegram_error_mod)

    if not _module_exists("gspread"):
        gspread_mod = types.ModuleType("gspread")
        gspread_mod.authorize = lambda *args, **kwargs: _Dummy()
        sys.modules.setdefault("gspread", gspread_mod)

    if not _module_exists("google.generativeai"):
        google_mod = sys.modules.get("google") or types.ModuleType("google")
        genai_mod = types.ModuleType("google.generativeai")
        genai_mod.configure = lambda *args, **kwargs: None
        sys.modules.setdefault("google", google_mod)
        sys.modules.setdefault("google.generativeai", genai_mod)
        setattr(google_mod, "generativeai", genai_mod)

    if not _module_exists("google.oauth2.service_account"):
        google_mod = sys.modules.get("google") or types.ModuleType("google")
        oauth2_mod = sys.modules.get("google.oauth2") or types.ModuleType("google.oauth2")
        service_account_mod = types.ModuleType("google.oauth2.service_account")

        class _Credentials:
            @classmethod
            def from_service_account_file(cls, *args: Any, **kwargs: Any) -> "_Credentials":
                return cls()

        service_account_mod.Credentials = _Credentials
        sys.modules.setdefault("google", google_mod)
        sys.modules.setdefault("google.oauth2", oauth2_mod)
        sys.modules.setdefault("google.oauth2.service_account", service_account_mod)
        setattr(google_mod, "oauth2", oauth2_mod)
        setattr(oauth2_mod, "service_account", service_account_mod)

    if not _module_exists("langchain_core.messages"):
        lc_core_mod = sys.modules.get("langchain_core") or types.ModuleType("langchain_core")
        lc_messages_mod = types.ModuleType("langchain_core.messages")

        class HumanMessage:
            def __init__(self, content: Any):
                self.content = content

        lc_messages_mod.HumanMessage = HumanMessage
        sys.modules.setdefault("langchain_core", lc_core_mod)
        sys.modules.setdefault("langchain_core.messages", lc_messages_mod)

    if not _module_exists("langchain_google_genai"):
        lc_google_mod = types.ModuleType("langchain_google_genai")

        class ChatGoogleGenerativeAI:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def invoke(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("LangChain Gemini belum terinstall di environment tester ini.")

        lc_google_mod.ChatGoogleGenerativeAI = ChatGoogleGenerativeAI
        sys.modules.setdefault("langchain_google_genai", lc_google_mod)


# ─────────────────────────────────────────────────────────────────────────────
# Model data inti untuk hasil testing
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AssertionResult:
    path: str
    expected: Any
    actual: Any
    status: str  # PASS | WARNING | FAIL
    message: str = ""


@dataclass
class CommandRun:
    name: str
    input_text: str
    mode: str
    parts: list[str]
    items: list[dict[str, Any]]
    next_action: str
    prompt: str = ""
    preview: str = ""
    after_decision: dict[str, Any] | None = None
    import_warnings: list[str] = field(default_factory=list)


KNOWN_SLASH_COMMANDS = {
    "start", "help", "saldo", "harian", "mingguan", "bulanan", "transaksi", "cari",
    "budget", "budget_history", "set_budget", "hutang", "debt", "debt_void", "debt_edit",
    "recurring", "recurring_add", "recurring_run", "recurring_off", "recurring_edit",
    "export", "health", "last", "delete_txn", "edit_txn", "ask", "coach", "insight", "audit",
    "networth", "assets", "liabilities", "asset_add", "liability_add", "asset_update",
    "liability_update", "asset_off", "liability_off", "networth_snapshot", "networth_history",
    "account", "account_set", "account_add", "account_rename", "account_off",
}


def classify_known_route(text: str) -> dict[str, Any] | None:
    """
    Simulasi routing Telegram/message_handler untuk command yang tidak seharusnya
    masuk parser transaksi. Ini membuat tester tidak false-positive membaca `/bulanan 2026-06`
    sebagai expense amount 2026.
    """
    raw = (text or "").strip()
    low = raw.lower()
    if not raw:
        return None

    if raw.startswith("/"):
        cmd = raw[1:].split()[0].split("@", 1)[0].lower()
        if cmd in KNOWN_SLASH_COMMANDS:
            return {
                "kind": "command",
                "parsed": {"route": "slash_command", "command": cmd, "args": raw.split(maxsplit=1)[1] if len(raw.split(maxsplit=1)) > 1 else ""},
                "raw": raw,
            }
        return {
            "kind": "unknown_command",
            "parsed": {"route": "unknown_slash_command", "command": cmd},
            "raw": raw,
        }

    natural_patterns: list[tuple[str, str]] = [
        (r"^(cek|lihat|tampilkan)\s+saldo\b", "saldo"),
        (r"^(cek|lihat|tampilkan)\s+(hutang|utang|piutang)\b", "hutang"),
        (r"^cari\s+.+", "cari"),
        (r"^(lihat|tampilkan)\s+transaksi\b", "transaksi"),
        (r"^hapus\s+transaksi\s+(nomor\s+)?\d+\b", "delete_txn"),
        (r"^edit\s+transaksi\s+(nomor\s+)?\d+\b", "edit_txn"),
        (r"^set\s+budget\b", "set_budget"),
        (r"^(lihat|cek|tampilkan)\s+budget\b", "budget"),
        (r"^(catat|tambah|add)\s+aset\b", "asset_add"),
        (r"^(catat|tambah|add)\s+(liability|kewajiban)\b", "liability_add"),
        (r"^catat\s+hutang\s+paylater\b", "liability_add"),
        (r"^net\s*worth\b", "networth"),
        (r"^(bayar|catat).+\bsetiap\s+(hari|minggu|bulan|tahun)\b", "recurring_add"),
    ]
    for pattern, intent in natural_patterns:
        if re.search(pattern, low):
            return {
                "kind": "natural_command",
                "parsed": {"route": "local_natural_intent", "intent": intent},
                "raw": raw,
            }

    return None


class CommandTester:
    def __init__(self) -> None:
        _ensure_test_env()
        _install_optional_import_stubs()
        self.import_warnings: list[str] = []
        self.handlers = self._import_handlers()

    def _import_handlers(self):
        try:
            return importlib.import_module("app.bot.handlers")
        except Exception as first_error:
            _install_optional_import_stubs()
            try:
                return importlib.import_module("app.bot.handlers")
            except Exception as second_error:
                raise RuntimeError(
                    "Gagal import app.bot.handlers. Pastikan kamu menjalankan tester "
                    "dari root project dan dependencies sudah install. "
                    f"First error: {type(first_error).__name__}: {first_error}. "
                    f"Second error: {type(second_error).__name__}: {second_error}"
                ) from second_error

    def run_command(self, input_text: str, *, name: str = "manual", decision: str | None = None) -> CommandRun:
        h = self.handlers
        raw_text = (input_text or "").strip()

        # Slash/natural command satu baris harus dites sebagai route command,
        # bukan sebagai transaksi regex.
        routed = classify_known_route(raw_text)
        if routed is not None and "\n" not in raw_text and ";" not in raw_text:
            return CommandRun(
                name=name,
                input_text=input_text,
                mode="single",
                parts=[raw_text],
                items=[self._jsonable_item(routed)],
                next_action=routed["parsed"].get("route", "command_route"),
                prompt=f"Route ke handler: {routed['parsed'].get('command') or routed['parsed'].get('intent')}",
                preview="",
                after_decision=None,
                import_warnings=self.import_warnings,
            )

        parts = h.split_user_inputs(input_text)
        mode = "batch" if len(parts) > 1 else "single"

        items: list[dict[str, Any]] = []
        for part in parts:
            route_item = classify_known_route(part)
            if route_item is not None:
                items.append(route_item)
            else:
                items.append(h.parse_mixed_item(part))

        if mode == "batch":
            transaction_items = [item for item in items if item.get("kind") == "transaction"]
            split_needed = h.mixed_split_bill_needs_decision(transaction_items) if transaction_items else False
            account_needed = h.mixed_needs_account(items) if items else False
            has_missing_amount = any(item.get("kind") == "missing_amount" for item in items)
            has_failed = any(item.get("kind") in {"failed", "unknown_command"} for item in items)

            if has_missing_amount:
                next_action = "ask_missing_amount"
                prompt = "Ada income yang belum punya nominal. Bot harus tanya nominal dulu."
                preview = ""
            elif split_needed:
                next_action = "ask_split_bill_status"
                prompt = h.build_mixed_split_bill_queue_prompt(transaction_items)
                preview = ""
            elif has_failed:
                next_action = "failed_parse"
                prompt = "Ada item yang gagal diparse. Lihat report detail."
                preview = ""
            elif account_needed:
                next_action = "offer_edit_before_account"
                prompt = "Mau edit dulu atau lanjut ke rekening?"
                preview = h.build_mixed_preview(items)
            else:
                next_action = "offer_edit_before_confirm"
                prompt = "Mau edit dulu atau lanjut simpan?"
                preview = h.build_mixed_preview(items) if items else "Command/natural route parsed."

            after_decision = None
            if decision in {"paid", "unpaid"}:
                decided_items = copy.deepcopy(transaction_items)
                if hasattr(h, "apply_split_bill_decision_to_current_mixed"):
                    decided_items, _ = h.apply_split_bill_decision_to_current_mixed(decided_items, decision)
                else:
                    decided_items = h.apply_split_bill_decision_to_mixed(decided_items, decision)
                after_decision = self._summarize_decision(decided_items, decision)

            return CommandRun(
                name=name,
                input_text=input_text,
                mode=mode,
                parts=parts,
                items=self._jsonable_items(items),
                next_action=next_action,
                prompt=str(prompt or ""),
                preview=str(preview or ""),
                after_decision=after_decision,
                import_warnings=self.import_warnings,
            )

        # Input single biasa.
        raw = parts[0] if parts else raw_text
        mixed = items[0] if items else {"kind": "failed", "parsed": {}, "raw": raw}
        parsed = mixed.get("parsed", {}) or {}

        if mixed.get("kind") == "missing_amount":
            next_action = "ask_missing_amount"
            prompt = h.build_missing_amount_prompt(raw, parsed) if hasattr(h, "build_missing_amount_prompt") else "Nominalnya berapa?"
            preview = ""
        elif mixed.get("kind") == "transaction" and h.split_bill_needs_decision(parsed):
            next_action = "ask_split_bill_status"
            prompt = h.build_split_bill_prompt_from_parsed(parsed)
            preview = ""
        elif mixed.get("kind") == "transaction" and h.needs_account(parsed):
            next_action = "offer_edit_before_account"
            prompt = "Mau edit dulu atau lanjut ke rekening?"
            preview = h.build_preview(parsed)
        elif mixed.get("kind") == "debt" and not parsed.get("account"):
            next_action = "ask_account"
            prompt = "Pilih rekening cashflow untuk debt/payment ini."
            preview = h.build_debt_account_prompt(parsed) if hasattr(h, "build_debt_account_prompt") else "Debt parsed."
        elif mixed.get("kind") in {"failed", "unknown_command"}:
            next_action = "failed_parse"
            prompt = "Parser gagal memahami input."
            preview = ""
        elif mixed.get("kind") in {"command", "natural_command"}:
            next_action = parsed.get("route", "command_route")
            prompt = f"Route ke handler: {parsed.get('command') or parsed.get('intent')}"
            preview = ""
        else:
            next_action = "offer_edit_before_confirm" if mixed.get("kind") == "transaction" else "show_preview"
            prompt = "Mau edit dulu atau lanjut simpan?" if mixed.get("kind") == "transaction" else ""
            preview = h.build_preview(parsed) if mixed.get("kind") == "transaction" else "Debt parsed."

        after_decision = None
        if decision in {"paid", "unpaid"} and mixed.get("kind") == "transaction":
            decided_parsed = h.apply_split_bill_decision_to_parsed(copy.deepcopy(parsed), decision)
            after_decision = self._summarize_decision([{"kind": "transaction", "parsed": decided_parsed, "raw": raw}], decision)

        return CommandRun(
            name=name,
            input_text=input_text,
            mode=mode,
            parts=parts,
            items=self._jsonable_items(items),
            next_action=next_action,
            prompt=str(prompt or ""),
            preview=str(preview or ""),
            after_decision=after_decision,
            import_warnings=self.import_warnings,
        )

    def _summarize_decision(self, items: list[dict[str, Any]], decision: str) -> dict[str, Any]:
        split_items = []
        for idx, item in enumerate(items, 1):
            parsed = item.get("parsed", {}) or {}
            split = parsed.get("split_bill") or {}
            if split:
                split_items.append({
                    "index": idx,
                    "description": parsed.get("description"),
                    "amount_after_decision": parsed.get("amount"),
                    "split_status": split.get("status"),
                    "share_amount": split.get("share_amount"),
                    "total_amount": split.get("total_amount"),
                    "total_receivable": 0 if decision == "paid" else split.get("total_receivable"),
                    "person_names": split.get("person_names"),
                })
        return {"decision": decision, "split_items": split_items}

    def _jsonable_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(item, ensure_ascii=False, default=str))

    def _jsonable_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return json.loads(json.dumps(items, ensure_ascii=False, default=str))


# ─────────────────────────────────────────────────────────────────────────────
# Assertions + heuristics
# ─────────────────────────────────────────────────────────────────────────────

def get_path(data: Any, path: str) -> Any:
    current = data
    if not path:
        return current
    for token in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except Exception:
                return None
        elif isinstance(current, dict):
            current = current.get(token)
        else:
            return None
    return current


def compare_value(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return abs(float(actual) - float(expected)) < 1e-6
        except Exception:
            return False
    return actual == expected


def evaluate_expectations(run: CommandRun, expect: dict[str, Any] | None) -> list[AssertionResult]:
    results: list[AssertionResult] = []
    if not expect:
        return results

    run_dict = command_run_to_dict(run)

    for path, expected in (expect.get("paths") or {}).items():
        actual = get_path(run_dict, path)
        ok = compare_value(actual, expected)
        results.append(AssertionResult(
            path=path,
            expected=expected,
            actual=actual,
            status="PASS" if ok else "FAIL",
            message="" if ok else "Value mismatch",
        ))

    for field_name in ["prompt_contains", "preview_contains"]:
        source_field = field_name.replace("_contains", "")
        source = str(getattr(run, source_field) or "")
        for text in expect.get(field_name, []) or []:
            ok = str(text).lower() in source.lower()
            results.append(AssertionResult(
                path=field_name,
                expected=f"contains: {text}",
                actual=source[:500] + ("..." if len(source) > 500 else ""),
                status="PASS" if ok else "FAIL",
                message="Text not found" if not ok else "",
            ))

    if "item_count" in expect:
        actual = len(run.items)
        expected = expect["item_count"]
        ok = actual == expected
        results.append(AssertionResult(
            path="item_count",
            expected=expected,
            actual=actual,
            status="PASS" if ok else "FAIL",
            message="Jumlah item tidak sesuai" if not ok else "",
        ))

    return results


def _has_split_keyword(text: str) -> bool:
    return bool(re.search(r"\b(di\s*-?\s*bagi|dibagi|bagi|split|patungan)\b", text, flags=re.IGNORECASE))


def _split_has_friend_name(text: str) -> bool:
    low = re.sub(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", " ", text.lower())
    if re.search(r"\bsama\s+[a-zA-Z][a-zA-Z\s,]+", low):
        return True
    m = re.search(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|patungan)\s+(?:jadi\s+)?\d+\s+([a-zA-Z][a-zA-Z\s,]*)", low)
    if m:
        tail = m.group(1).strip()
        # Hindari kata umum yang bukan nama.
        if tail and not re.fullmatch(r"(orang|org|x|kali|bagian)", tail):
            return True
    return False


def evaluate_heuristics(run: CommandRun) -> list[AssertionResult]:
    """Auto-check supaya file .txt tanpa expect tetap punya PASS/WARNING/FAIL yang bermakna."""
    results: list[AssertionResult] = []

    if not run.items:
        results.append(AssertionResult("items", "> 0", 0, "FAIL", "Tidak ada item yang diparse."))
        return results

    comment_items = [item.get("raw", "") for item in run.items if str(item.get("raw", "")).lstrip().startswith("#")]
    results.append(AssertionResult(
        "comments_ignored",
        "no item raw starts with #",
        len(comment_items),
        "PASS" if not comment_items else "FAIL",
        "Baris komentar ikut diparse sebagai transaksi." if comment_items else "",
    ))

    failed_items = [item for item in run.items if item.get("kind") in {"failed", "unknown_command"}]
    results.append(AssertionResult(
        "no_failed_items",
        0,
        len(failed_items),
        "PASS" if not failed_items else "FAIL",
        "Ada item kind=failed/unknown_command." if failed_items else "",
    ))

    bad_slash = [item for item in run.items if str(item.get("raw", "")).strip().startswith("/") and item.get("kind") == "transaction"]
    if bad_slash:
        results.append(AssertionResult(
            "slash_command_route",
            "slash command routed as command",
            [item.get("raw") for item in bad_slash],
            "FAIL",
            "Command slash masih masuk parser transaksi.",
        ))
    elif any(str(item.get("raw", "")).strip().startswith("/") for item in run.items):
        results.append(AssertionResult("slash_command_route", "command route", "ok", "PASS"))

    # Decimal koma Indonesia: 24,7k harus tetap satu item dan amount 24700.
    for item in run.items:
        raw = str(item.get("raw", ""))
        match = re.search(r"(\d+)\s*,\s*(\d+)\s*k\b", raw, flags=re.IGNORECASE)
        if not match:
            continue
        expected = int(round(float(f"{match.group(1)}.{match.group(2)}") * 1000))
        actual = item.get("parsed", {}).get("amount") if item.get("kind") == "transaction" else None
        ok = compare_value(actual, expected)
        results.append(AssertionResult(
            "decimal_comma_amount",
            expected,
            actual,
            "PASS" if ok else "FAIL",
            "Nominal koma seperti 24,7k harus dibaca 24700 dan tidak boleh pecah jadi 24 + 7k." if not ok else "",
        ))

    # Jika input utuh punya desimal koma tetapi parts > 1 dan tidak ada item raw yang masih mengandung koma,
    # kemungkinan split_user_inputs memecah koma decimal.
    if re.search(r"\d+\s*,\s*\d+\s*k\b", run.input_text, flags=re.IGNORECASE) and not any(
        re.search(r"\d+\s*,\s*\d+\s*k\b", str(item.get("raw", "")), flags=re.IGNORECASE) for item in run.items
    ):
        results.append(AssertionResult(
            "decimal_comma_split",
            "single decimal amount item",
            run.parts,
            "FAIL",
            "Input decimal koma pecah saat split_user_inputs.",
        ))

    # Incoming from person: "transfer/transaksi dari Annisa 55k" harus income biasa,
    # bukan debt payment dan bukan expense/outcome. Kalau nominal belum ada,
    # bot harus masuk flow tanya nominal.
    own_accounts = {"cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"}
    for idx, item in enumerate(run.items, 1):
        raw = str(item.get("raw", ""))
        incoming_match = re.search(
            r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+(.+?)\s*$",
            raw,
            flags=re.IGNORECASE,
        )
        if incoming_match and not re.search(r"\bdari\s+[^\n]+?\s+ke\s+", raw, flags=re.IGNORECASE):
            source = re.sub(
                r"\b(?:tgl|tanggal)\s*\d{1,2}(?:[-/]\d{1,2}(?:[-/]\d{2,4})?)?\b",
                " ",
                incoming_match.group(1),
                flags=re.IGNORECASE,
            )
            source = re.sub(r"\s+", " ", source).strip().lower()
            first_token = source.split()[0] if source else ""
            if first_token and first_token not in own_accounts:
                actual_kind = item.get("kind")
                actual_type = item.get("parsed", {}).get("type")
                has_amount = bool(re.search(
                    r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)\b|\b\d{4,}\b",
                    raw,
                    flags=re.IGNORECASE,
                ))
                ok = (
                    actual_kind == "transaction" and actual_type == "income"
                ) or (
                    not has_amount and actual_kind == "missing_amount" and actual_type == "income"
                )
                expected = "transaction income" if has_amount else "ask missing amount income"
                results.append(AssertionResult(
                    f"incoming_from_person_income.{idx}",
                    expected,
                    {"kind": actual_kind, "type": actual_type, "raw": raw},
                    "PASS" if ok else "FAIL",
                    "Transfer/transaksi dari orang harus income biasa; kalau nominal belum ada, harus tanya nominal, bukan debt/outcome." if not ok else "",
                ))

    # Split bill: kalau ada nama teman, harus ada split_bill dan next_action harus tanya status.
    split_items = [item for item in run.items if _has_split_keyword(str(item.get("raw", "")))]
    for idx, item in enumerate(split_items, 1):
        raw = str(item.get("raw", ""))
        parsed = item.get("parsed", {}) or {}
        split = parsed.get("split_bill") if item.get("kind") == "transaction" else None
        has_friend = _split_has_friend_name(raw)
        if has_friend and not split:
            results.append(AssertionResult(
                f"split_bill_detected.{idx}",
                "split_bill object exists",
                item,
                "FAIL",
                "Ada keyword split dan nama teman, tapi split_bill tidak terbentuk.",
            ))
        elif not has_friend and not split:
            results.append(AssertionResult(
                f"split_bill_no_friend.{idx}",
                "warning/clarification",
                {"raw": raw, "amount": parsed.get("amount")},
                "WARNING",
                "Ada keyword split tapi tidak ada nama teman; aman jika memang sengaja disimpan sebagai bagian pribadi, tapi sebaiknya minta klarifikasi.",
            ))
        elif split and split.get("status") is None and run.next_action != "ask_split_bill_status":
            results.append(AssertionResult(
                f"split_bill_next_action.{idx}",
                "ask_split_bill_status",
                run.next_action,
                "FAIL",
                "Split bill terbentuk tapi flow tidak tanya sudah dibayar/belum.",
            ))
        elif split:
            results.append(AssertionResult(
                f"split_bill_detected.{idx}",
                "split bill + ask status",
                {"share_amount": split.get("share_amount"), "total_receivable": split.get("total_receivable"), "next_action": run.next_action},
                "PASS",
            ))

    return results


def case_status(assertions: list[AssertionResult]) -> str:
    if any(a.status == "FAIL" for a in assertions):
        return "FAIL"
    if any(a.status == "WARNING" for a in assertions):
        return "WARNING"
    return "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# Diagnosis
# ─────────────────────────────────────────────────────────────────────────────

def deterministic_diagnosis(run: CommandRun, assertions: list[AssertionResult]) -> str:
    failed = [a for a in assertions if a.status == "FAIL"]
    warnings_ = [a for a in assertions if a.status == "WARNING"]
    if not failed and not warnings_:
        return "Semua check lolos. Output parser/flow sesuai ekspektasi test case."

    tips: list[str] = []
    paths = " ".join(a.path for a in failed + warnings_).lower()
    messages = " ".join(a.message for a in failed + warnings_).lower()

    if "split_bill" in paths:
        tips.append("Cek attach_split_bill_if_any(), extract_split_bill_info(), dan urutan flow sebelum account preview.")
    if "decimal_comma" in paths:
        tips.append("Cek split_user_inputs(): jangan split koma yang berada di antara angka, misalnya 24,7k.")
    if "slash_command" in paths:
        tips.append("Pastikan command slash tidak dikirim ke parse_with_regex; harus ditangani CommandHandler/router dulu.")
    if "no_failed_items" in paths or "failed" in messages:
        tips.append("Cek item raw yang gagal; bisa jadi natural command belum masuk local intent atau regex parser terlalu sempit.")
    if not tips:
        tips.append("Cek assertion detail, lalu telusuri parser sesuai path yang fail/warning.")

    detail_rows = [
        f"- {a.status} {a.path}: expected={a.expected!r}, actual={a.actual!r}"
        for a in (failed + warnings_)[:10]
    ]
    return "Ada temuan.\n\nDetail:\n" + "\n".join(detail_rows) + "\n\nDiagnosis awal:\n" + "\n".join(f"- {t}" for t in tips)


def ai_diagnosis(run: CommandRun, assertions: list[AssertionResult]) -> str:
    if not os.getenv("GEMINI_API_KEY"):
        return deterministic_diagnosis(run, assertions)

    try:
        from app.nlp.gemini_langchain_client import generate_text_with_gemini

        prompt = f"""
Kamu adalah AI QA agent untuk Telegram bot finance berbahasa Indonesia.
Tugasmu menganalisis hasil command parser dan memberi diagnosis teknis yang actionable.

INPUT USER:
{run.input_text}

HASIL AKTUAL JSON:
{json.dumps(command_run_to_dict(run), ensure_ascii=False, indent=2)}

ASSERTION RESULTS:
{json.dumps([a.__dict__ for a in assertions], ensure_ascii=False, indent=2)}

Berikan jawaban ringkas dalam Bahasa Indonesia dengan format:
1. Status
2. Bug utama jika ada
3. Kemungkinan lokasi fungsi/file yang perlu dicek
4. Saran patch konkret
""".strip()
        response = generate_text_with_gemini(prompt, temperature=0.0)
        return response.strip() if response else deterministic_diagnosis(run, assertions)
    except Exception as e:
        return deterministic_diagnosis(run, assertions) + f"\n\nAI diagnosis gagal dipanggil: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# IO + report
# ─────────────────────────────────────────────────────────────────────────────

def command_run_to_dict(run: CommandRun) -> dict[str, Any]:
    return {
        "name": run.name,
        "input_text": run.input_text,
        "mode": run.mode,
        "parts": run.parts,
        "items": run.items,
        "next_action": run.next_action,
        "prompt": run.prompt,
        "preview": run.preview,
        "after_decision": run.after_decision,
        "import_warnings": run.import_warnings,
    }


def resolve_input_path(path_text: str) -> Path:
    """Dukung path Windows (`tests\\input_Test.txt`) maupun relatif root project."""
    raw = Path(path_text)
    candidates = [raw]
    if not raw.is_absolute():
        candidates.append(PROJECT_ROOT / raw)
        candidates.append(PROJECT_ROOT / str(path_text).replace("\\", "/"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return raw


def load_cases(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict) and "cases" in data:
        return list(data["cases"])
    if isinstance(data, list):
        return data
    raise ValueError("Format test file harus list atau object dengan key 'cases'.")


def load_text_cases(path: Path, *, decision: str | None = None) -> list[dict[str, Any]]:
    """
    Parsing input .txt untuk testing chat manual.

    Format didukung:
    - Teks biasa tanpa `---`: seluruh file dianggap satu input multi-line.
    - Banyak case dipisah baris `---`: komentar `#` diabaikan dari input,
      komentar pertama dalam block dipakai sebagai nama case.
    """
    text = path.read_text(encoding="utf-8-sig")
    raw_lines = text.splitlines()

    def is_sep(line: str) -> bool:
        return line.strip().strip("\ufeff") == "---"

    has_blocks = any(is_sep(line) for line in raw_lines)
    if not has_blocks:
        return [{"name": path.name, "input": text, "decision": decision}]

    cases: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_name: str | None = None

    def flush() -> None:
        nonlocal current_lines, current_name
        cleaned: list[str] = []
        for line in current_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            cleaned.append(line.rstrip())
        if cleaned:
            cases.append({
                "name": current_name or f"{path.name} case {len(cases) + 1}",
                "input": "\n".join(cleaned),
                "decision": decision,
            })
        current_lines = []
        current_name = None

    for line in raw_lines:
        stripped = line.strip().strip("\ufeff")
        if is_sep(line):
            flush()
            continue
        if stripped.startswith("#") and current_name is None:
            current_name = stripped.lstrip("#").strip() or None
        current_lines.append(line)

    flush()
    return cases


def default_sample_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "split bill single - dibagi",
            "input": "Nasi kuning 22k dibagi 2 sama sapto 09-05-2026",
            "decision": "unpaid",
            "expect": {
                "item_count": 1,
                "paths": {
                    "mode": "single",
                    "next_action": "ask_split_bill_status",
                    "items.0.kind": "transaction",
                    "items.0.parsed.amount": 22000.0,
                    "items.0.parsed.split_bill.share_amount": 11000.0,
                    "items.0.parsed.split_bill.total_receivable": 11000.0,
                    "items.0.parsed.split_bill.person_names.0": "Sapto",
                    "after_decision.split_items.0.amount_after_decision": 22000.0,
                    "after_decision.split_items.0.split_status": "unpaid",
                },
                "prompt_contains": ["Split bill", "Sapto", "Rp22.000", "Rp11.000"],
            },
        },
        {
            "name": "split bill single - paid decision saves own share",
            "input": "Nasi kuning 22k bagi 2 sama sapto 09-05-2026",
            "decision": "paid",
            "expect": {
                "paths": {
                    "next_action": "ask_split_bill_status",
                    "items.0.parsed.amount": 22000.0,
                    "items.0.parsed.split_bill.share_amount": 11000.0,
                    "after_decision.split_items.0.amount_after_decision": 11000.0,
                    "after_decision.split_items.0.total_receivable": 0,
                }
            },
        },
        {
            "name": "bulk multiline with split bill first row",
            "input": "Nasi kuning 22k dibagi 2 sama sapto 09-05-2026\nPrint 6k 09-05-2026\nJajan boba 8k 09-05-2026\nBubur ayam pak blankon 15k 10-05-2026\nNasi goreng gila yasmin 10k 10-05-2026\nWr pecel ayam sambal 10k 11-05-2026\nAlquran 80k 11-05-2026\nBakso tetelan 43k dibagi 2 11-05-2026\nNasi padang 10k 16-05-2026\nAyam dcelup 13k 20-05-2026\nTop up dana 3000k 26-05-2026\nBuah tangan si ibu 24.7 k 27-05-2026\nAyam dcelup 13k 28-05-2026\nSop sopan 5k 29-05-2026\nNasi 5k 30-05-2026\nTeh kotjok 15k 31-05-2026\nWarteg bahari 11k 31-05-2026",
            "decision": "unpaid",
            "expect": {
                "item_count": 17,
                "paths": {
                    "mode": "batch",
                    "next_action": "ask_split_bill_status",
                    "items.0.kind": "transaction",
                    "items.0.parsed.amount": 22000.0,
                    "items.0.parsed.split_bill.share_amount": 11000.0,
                    "items.0.parsed.split_bill.person_names.0": "Sapto",
                    "after_decision.split_items.0.amount_after_decision": 22000.0,
                    "after_decision.split_items.0.split_status": "unpaid",
                },
                "prompt_contains": ["Split bill", "Nasi", "Sapto", "Rp22.000", "Rp11.000"],
            },
        },
        {
            "name": "top up transfer detection",
            "input": "Top up dana 3000k 26-05-2026",
            "expect": {
                "paths": {
                    "items.0.kind": "transaction",
                    "items.0.parsed.type": "transfer",
                    "items.0.parsed.amount": 3000000,
                }
            },
        },
    ]


def write_sample(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": default_sample_cases()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass
class CaseResult:
    run: CommandRun
    assertions: list[AssertionResult]
    diagnosis: str


def run_one_case(tester: CommandTester, case: dict[str, Any], index: int, *, use_ai: bool) -> CaseResult:
    name = case.get("name") or f"case-{index}"
    input_text = case.get("input") or ""
    decision = case.get("decision")
    run = tester.run_command(input_text, name=name, decision=decision)
    assertions = evaluate_expectations(run, case.get("expect")) + evaluate_heuristics(run)
    diagnosis = ai_diagnosis(run, assertions) if use_ai or any(a.status in {"FAIL", "WARNING"} for a in assertions) else deterministic_diagnosis(run, assertions)
    return CaseResult(run=run, assertions=assertions, diagnosis=diagnosis)


def print_case_report(result: CaseResult, *, show_json: bool, use_ai: bool) -> None:
    run = result.run
    assertions = result.assertions
    failed = [a for a in assertions if a.status == "FAIL"]
    warnings_ = [a for a in assertions if a.status == "WARNING"]
    passed = [a for a in assertions if a.status == "PASS"]
    status = case_status(assertions)

    print("\n" + "=" * 100)
    print(f"[{status}] {run.name}")
    print("=" * 100)
    print(f"Mode        : {run.mode}")
    print(f"Item count  : {len(run.items)}")
    print(f"Next action : {run.next_action}")
    print(f"Checks      : {len(passed)} PASS, {len(warnings_)} WARNING, {len(failed)} FAIL")

    if run.prompt:
        print("\nPROMPT / NEXT MESSAGE:")
        print(run.prompt[:1500] + ("..." if len(run.prompt) > 1500 else ""))

    if failed or warnings_ or show_json:
        print("\nCHECK DETAIL:")
        for a in assertions:
            if a.status == "PASS" and not show_json:
                continue
            print(f"[{a.status}] {a.path} | expected={a.expected!r} | actual={a.actual!r}")
            if a.message:
                print(f"  note: {a.message}")

    if use_ai or failed or warnings_:
        print("\nDIAGNOSIS:")
        print(result.diagnosis)

    if show_json:
        print("\nACTUAL JSON:")
        print(json.dumps(command_run_to_dict(run), ensure_ascii=False, indent=2, default=str))


def make_markdown_report(results: list[CaseResult]) -> str:
    total = len(results)
    pass_count = sum(1 for r in results if case_status(r.assertions) == "PASS")
    warn_count = sum(1 for r in results if case_status(r.assertions) == "WARNING")
    fail_count = sum(1 for r in results if case_status(r.assertions) == "FAIL")

    lines: list[str] = []
    lines.append("# AI Command Tester Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total cases | {total} |")
    lines.append(f"| PASS | {pass_count} |")
    lines.append(f"| WARNING | {warn_count} |")
    lines.append(f"| FAIL | {fail_count} |")
    lines.append("")

    if fail_count or warn_count:
        lines.append("## Cases with findings")
        lines.append("")
        for idx, result in enumerate(results, 1):
            status = case_status(result.assertions)
            if status == "PASS":
                continue
            lines.append(f"### {idx}. [{status}] {result.run.name}")
            lines.append("")
            lines.append("**Input**")
            lines.append("")
            lines.append("```text")
            lines.append(result.run.input_text.strip())
            lines.append("```")
            lines.append("")
            lines.append(f"- Mode: `{result.run.mode}`")
            lines.append(f"- Item count: `{len(result.run.items)}`")
            lines.append(f"- Next action: `{result.run.next_action}`")
            lines.append("")
            lines.append("**Findings**")
            lines.append("")
            for a in result.assertions:
                if a.status == "PASS":
                    continue
                lines.append(f"- **{a.status}** `{a.path}` — {a.message or 'Check mismatch'}")
                lines.append(f"  - Expected: `{a.expected}`")
                lines.append(f"  - Actual: `{a.actual}`")
            lines.append("")
            lines.append("**Diagnosis**")
            lines.append("")
            lines.append("```text")
            lines.append(result.diagnosis)
            lines.append("```")
            lines.append("")

    lines.append("## All case results")
    lines.append("")
    lines.append("| # | Status | Case | Mode | Items | Next action |")
    lines.append("|---:|---|---|---|---:|---|")
    for idx, result in enumerate(results, 1):
        status = case_status(result.assertions)
        safe_name = result.run.name.replace("|", "\\|")
        lines.append(f"| {idx} | {status} | {safe_name} | {result.run.mode} | {len(result.run.items)} | `{result.run.next_action}` |")

    lines.append("")
    lines.append("## Raw actual JSON")
    lines.append("")
    lines.append("```json")
    payload = [
        {
            "status": case_status(result.assertions),
            "assertions": [a.__dict__ for a in result.assertions],
            "run": command_run_to_dict(result.run),
        }
        for result in results
    ]
    lines.append(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def run_cases(cases: list[dict[str, Any]], *, show_json: bool, use_ai: bool, markdown_path: Path | None = None) -> int:
    tester = CommandTester()
    results: list[CaseResult] = []

    for i, case in enumerate(cases, 1):
        result = run_one_case(tester, case, i, use_ai=use_ai)
        results.append(result)
        print_case_report(result, show_json=show_json, use_ai=use_ai)

    total = len(results)
    pass_count = sum(1 for r in results if case_status(r.assertions) == "PASS")
    warn_count = sum(1 for r in results if case_status(r.assertions) == "WARNING")
    fail_count = sum(1 for r in results if case_status(r.assertions) == "FAIL")

    print("\n" + "=" * 100)
    print(f"FINAL RESULT: {pass_count} PASS, {warn_count} WARNING, {fail_count} FAIL dari {total} case.")
    if fail_count == 0 and warn_count == 0:
        print("Semua test case lolos.")
    elif fail_count == 0:
        print("Tidak ada FAIL, tapi masih ada WARNING yang perlu direview.")
    else:
        print("Masih ada FAIL yang perlu diperbaiki.")
    print("=" * 100)

    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(make_markdown_report(results), encoding="utf-8")
        print(f"Markdown report ditulis ke: {markdown_path}")

    return 1 if fail_count else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI/local command tester untuk finance bot.")
    src = parser.add_mutually_exclusive_group(required=False)
    src.add_argument("--input", help="Satu command/manual input untuk dites.")
    src.add_argument("--input-file", help="File .txt berisi input manual/multiline. Bisa berisi banyak case dipisah baris ---. ")
    src.add_argument("--file", help="File JSON test cases. Default: tests/command_cases.json jika ada.")
    src.add_argument("--sample", action="store_true", help="Jalankan sample built-in test cases.")

    parser.add_argument("--decision", choices=["paid", "unpaid"], help="Simulasikan keputusan split bill.")
    parser.add_argument("--ai", action="store_true", help="Pakai Gemini untuk diagnosis jika GEMINI_API_KEY tersedia.")
    parser.add_argument("--json", action="store_true", help="Tampilkan actual JSON penuh di console.")
    parser.add_argument("--markdown", help="Tulis report Markdown ke file, contoh: --markdown report.md")
    parser.add_argument("--write-sample", action="store_true", help="Tulis sample test ke tests/command_cases.json lalu keluar.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    default_file = PROJECT_ROOT / "tests" / "command_cases.json"
    if args.write_sample:
        write_sample(default_file)
        print(f"Sample test cases ditulis ke: {default_file}")
        return 0

    if args.input is not None:
        cases = [{"name": "manual input", "input": args.input, "decision": args.decision}]
    elif args.input_file:
        cases = load_text_cases(resolve_input_path(args.input_file), decision=args.decision)
    elif args.file:
        cases = load_cases(resolve_input_path(args.file))
    elif args.sample:
        cases = default_sample_cases()
    elif default_file.exists():
        cases = load_cases(default_file)
    else:
        cases = default_sample_cases()

    markdown_path = Path(args.markdown) if args.markdown else None
    return run_cases(cases, show_json=args.json, use_ai=args.ai, markdown_path=markdown_path)


if __name__ == "__main__":
    raise SystemExit(main())
