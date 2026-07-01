from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, median

from app.config import (
    SHEET_ACCOUNTS,
    SHEET_ASSETS,
    SHEET_BUDGETS,
    SHEET_DEBTS,
    SHEET_TRANSACTIONS,
)
from app.sheets.client import get_all_records
from app.services.report_service import enrich_transactions_with_debt_info

DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
}

FINANCE_QUESTION_KEYWORDS = [
    "insight", "analisis", "ringkasan", "laporan", "narasi",
    "boros", "hemat", "pengeluaran", "pemasukan", "income", "expense",
    "budget", "anggaran", "sisa budget", "jebol", "aman gak", "aman nggak",
    "anomali", "aneh", "tidak biasa", "audit", "data quality", "duplikat",
    "transaksi terbesar", "terakhir", "kapan", "berapa total", "total", "cari transaksi",
    "saran", "coach", "rekomendasi", "nabung", "tabung", "kurangi",
    "pending", "rencana", "pengeluaran akan datang",
    "saldo", "utang", "hutang", "piutang", "net worth", "aset",
]

AVAILABLE_COMMANDS_FOR_AI = [
    "/saldo",
    "/rekening",
    "/harian",
    "/mingguan",
    "/bulanan",
    "/cari",
    "/last",
    "/transaksi",
    "/edit_txn",
    "/delete_txn",
    "/budget",
    "/pending",
    "/hutang",
    "/debt_edit",
    "/debt_void",
    "/insight",
    "/ask",
    "/audit",
    "/coach",
]

STOPWORDS = {
    "aku", "saya", "gue", "gua", "gw", "bulan", "ini", "itu", "di", "ke", "dari", "yang",
    "dan", "atau", "untuk", "berapa", "total", "transaksi", "pengeluaran", "pemasukan",
    "makan", "budget", "aman", "gak", "nggak", "ga", "dong", "ya", "apa", "aja",
    "kapan", "terakhir", "cari", "lihat", "cek", "tolong", "kasih", "saran", "saya",
    "hari", "minggu", "tahun", "periode", "saldo", "rekening", "kenapa", "turun", "naik",
    "bulanini", "hariini", "mingguini",
}

CATEGORY_HINTS = {
    "makan": "Food & Beverage",
    "jajan": "Food & Beverage",
    "kopi": "Food & Beverage",
    "minum": "Food & Beverage",
    "food": "Food & Beverage",
    "transport": "Transport",
    "ojol": "Transport",
    "gojek": "Transport",
    "grab": "Transport",
    "bensin": "Transport",
    "listrik": "Bills & Utilities",
    "token": "Bills & Utilities",
    "internet": "Bills & Utilities",
    "wifi": "Bills & Utilities",
    "belanja": "Shopping",
    "shopping": "Shopping",
    "skincare": "Personal Care",
    "obat": "Health",
    "dokter": "Health",
}


def safe_float(value, default: float = 0.0) -> float:
    """Parse angka rupiah dari Google Sheets tanpa mengalikan numeric float.

    Bug lama: nilai numeric dari Sheets seperti 427500.0 diubah menjadi
    4275000 karena titik desimal dianggap pemisah ribuan dan dihapus.
    """
    if value is None or value == "":
        return default

    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    if not raw:
        return default

    raw = raw.replace("Rp", "").replace("rp", "").replace("IDR", "").replace("idr", "")
    raw = raw.replace(" ", "")

    if "," in raw and "." in raw:
        # Format Indonesia: 427.500,5
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        parts = raw.split(",")
        # 427500,5 atau 427500,50 = desimal; 427,500 = ribuan.
        if len(parts) == 2 and len(parts[-1]) in {1, 2}:
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "." in raw:
        parts = raw.split(".")
        # 427.500 atau 1.427.500 = ribuan.
        # 427500.0 dari numeric float string tetap desimal, jangan hapus titik.
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            raw = raw.replace(".", "")

    raw = re.sub(r"[^0-9.-]", "", raw)

    try:
        return float(raw)
    except Exception:
        return default


def format_rupiah(amount: float) -> str:
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def normalize_month_arg(value: str | None = None) -> str:
    """Support None, YYYY-MM, YYYY/MM, bulan angka, bulan ini."""
    today = datetime.now()
    if not value:
        return current_month()

    raw = str(value).strip().lower().replace("/", "-")
    raw = re.sub(r"\s+", " ", raw)

    if raw in {"bulan ini", "bulanini", "month", "current", "sekarang"}:
        return current_month()

    m = re.search(r"(20\d{2})[-\s](0?[1-9]|1[0-2])", raw)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"

    m = re.fullmatch(r"(0?[1-9]|1[0-2])", raw)
    if m:
        return f"{today.year}-{int(m.group(1)):02d}"

    return current_month()


def previous_month(month: str) -> str:
    year, month_num = map(int, month.split("-"))
    if month_num == 1:
        return f"{year - 1}-12"
    return f"{year}-{month_num - 1:02d}"


def month_bounds(month: str) -> tuple[str, str]:
    year, month_num = map(int, month.split("-"))
    first = datetime(year, month_num, 1)
    if month_num == 12:
        next_first = datetime(year + 1, 1, 1)
    else:
        next_first = datetime(year, month_num + 1, 1)
    last = next_first - timedelta(days=1)
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


def parse_period_from_text(text: str) -> dict:
    raw = str(text or "").lower()
    today = datetime.now().date()

    m = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])", raw)
    if m:
        month = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    m = re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", raw)
    if m:
        month = f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    if any(k in raw for k in ["hari ini", "hariini", "today"]):
        d = today.strftime("%Y-%m-%d")
        return {"type": "day", "month": d[:7], "date_from": d, "date_to": d, "label": d}

    if any(k in raw for k in ["kemarin", "yesterday"]):
        d = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        return {"type": "day", "month": d[:7], "date_from": d, "date_to": d, "label": d}

    if any(k in raw for k in ["minggu ini", "mingguini", "week"]):
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return {
            "type": "week",
            "month": today.strftime("%Y-%m"),
            "date_from": monday.strftime("%Y-%m-%d"),
            "date_to": sunday.strftime("%Y-%m-%d"),
            "label": f"{monday} s/d {sunday}",
        }

    if any(k in raw for k in ["bulan lalu", "last month"]):
        month = previous_month(current_month())
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    month = current_month()
    start, end = month_bounds(month)
    return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}


def normalize_text(value: str) -> str:
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_date_between(date_value: str, date_from: str | None, date_to: str | None) -> bool:
    date_value = str(date_value or "").strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date_value):
        return False
    if date_from and date_value < date_from:
        return False
    if date_to and date_value > date_to:
        return False
    return True


def filter_records_by_period(records: list[dict], date_from: str | None, date_to: str | None) -> list[dict]:
    return [r for r in records if is_date_between(r.get("date", ""), date_from, date_to)]


def get_month_transactions(month: str) -> list[dict]:
    date_from, date_to = month_bounds(month)
    records = get_all_records(SHEET_TRANSACTIONS)
    return filter_records_by_period(records, date_from, date_to)


def enrich_finance_transactions(records: list[dict]) -> list[dict]:
    """Attach debt metadata so AI finance sees expense as Net, not Gross.

    Split bill/piutang membuat cash keluar secara gross, tetapi beban pribadi user
    adalah gross dikurangi piutang yang dibuat dari transaksi itu. Konteks AI
    sengaja memakai net supaya audit, anomali, budget, dan coach tidak
    membesar-besarkan pengeluaran user.
    """
    records = records or []
    if any(
        str((r or {}).get("type", "")).strip().lower() == "expense"
        and "net_expense_after_receivable" in (r or {})
        for r in records
    ):
        return records
    return enrich_transactions_with_debt_info(records)


def get_effective_expense_amount(record: dict) -> float:
    """Nominal expense untuk analisis AI = net setelah piutang split bill."""
    amount = safe_float((record or {}).get("amount"))
    if str((record or {}).get("type", "")).strip().lower() != "expense":
        return amount

    if "net_expense_after_receivable" in (record or {}):
        return max(safe_float((record or {}).get("net_expense_after_receivable")), 0.0)

    receivable = safe_float(
        (record or {}).get("debt_receivable_original", (record or {}).get("debt_receivable_remaining", 0))
    )
    return max(amount - receivable, 0.0)


def summarize_transactions(records: list[dict]) -> dict:
    total_income = 0.0
    total_expense = 0.0  # Net expense setelah piutang split bill.
    total_transfer = 0.0
    expense_by_category = defaultdict(float)
    income_by_category = defaultdict(float)
    expense_by_account = defaultdict(float)
    income_by_account = defaultdict(float)
    cash_out_by_account = defaultdict(float)
    cash_in_by_account = defaultdict(float)

    records = enrich_finance_transactions(records)

    for r in records:
        txn_type = str(r.get("type", "")).strip().lower()
        amount = safe_float(r.get("amount"))
        effective_amount = get_effective_expense_amount(r)
        category = str(r.get("category") or "Uncategorized").strip() or "Uncategorized"
        account = str(r.get("account") or "-").strip() or "-"
        to_account = str(r.get("to_account") or "").strip()

        if txn_type == "income":
            total_income += amount
            income_by_category[category] += amount
            income_by_account[account] += amount
            cash_in_by_account[account] += amount
        elif txn_type == "expense":
            # Untuk AI finance, expense selalu memakai beban bersih pribadi,
            # bukan cashflow gross yang sudah ditagihkan sebagai piutang.
            total_expense += effective_amount
            expense_by_category[category] += effective_amount
            expense_by_account[account] += effective_amount
            cash_out_by_account[account] += effective_amount
        elif txn_type == "transfer":
            total_transfer += amount
            cash_out_by_account[account] += amount
            if to_account:
                cash_in_by_account[to_account] += amount

    def sorted_items(d: dict) -> list[dict]:
        return [
            {"name": k, "amount": v, "amount_display": format_rupiah(v)}
            for k, v in sorted(d.items(), key=lambda x: x[1], reverse=True)
            if abs(v) > 0.0001
        ]

    return {
        "count": len(records),
        "amount_basis": "expense_amount_is_net_after_receivable",
        "total_income": total_income,
        "total_income_display": format_rupiah(total_income),
        "total_expense": total_expense,
        "total_expense_display": format_rupiah(total_expense),
        "total_transfer": total_transfer,
        "total_transfer_display": format_rupiah(total_transfer),
        "net": total_income - total_expense,
        "net_display": format_rupiah(total_income - total_expense),
        "expense_by_category": sorted_items(expense_by_category),
        "income_by_category": sorted_items(income_by_category),
        "expense_by_account": sorted_items(expense_by_account),
        "income_by_account": sorted_items(income_by_account),
        "cash_out_by_account": sorted_items(cash_out_by_account),
        "cash_in_by_account": sorted_items(cash_in_by_account),
    }


def add_contribution(items: list[dict], total: float, limit: int = 8) -> list[dict]:
    result = []
    for item in items[:limit]:
        amount = float(item.get("amount", 0) or 0)
        result.append({
            **item,
            "contribution_pct": round((amount / total * 100), 1) if total else 0,
        })
    return result


def compact_transaction(r: dict) -> dict:
    amount = get_effective_expense_amount(r)
    item = {
        "date": r.get("date", ""),
        "type": r.get("type", ""),
        "amount": amount,
        "amount_display": format_rupiah(amount),
        "category": r.get("category", ""),
        "account": r.get("account", ""),
        "to_account": r.get("to_account", ""),
        "subject": r.get("subject", ""),
        "description": r.get("description", ""),
        "catatan": r.get("catatan", ""),
        "id": r.get("id", ""),
    }
    if str(r.get("type", "")).strip().lower() == "expense":
        item["amount_basis"] = "net_after_receivable"
    return item


def get_top_transactions(records: list[dict], txn_type: str | None = "expense", limit: int = 8) -> list[dict]:
    records = enrich_finance_transactions(records)
    candidates = []
    for r in records:
        if txn_type and str(r.get("type", "")).strip().lower() != txn_type:
            continue
        amount = get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))
        if amount <= 0:
            continue
        candidates.append(r)
    candidates.sort(
        key=lambda x: get_effective_expense_amount(x) if str(x.get("type", "")).strip().lower() == "expense" else safe_float(x.get("amount")),
        reverse=True,
    )
    return [compact_transaction(r) for r in candidates[:limit]]


def get_budget_status(month: str, transactions: list[dict]) -> list[dict]:
    budgets = [
        b for b in get_all_records(SHEET_BUDGETS)
        if str(b.get("month", "")).strip() == month
    ]
    if not budgets:
        return []

    expense_by_category = defaultdict(float)
    for r in enrich_finance_transactions(transactions):
        if str(r.get("type", "")).strip().lower() != "expense":
            continue
        category = str(r.get("category") or "Uncategorized").strip()
        expense_by_category[category.lower()] += get_effective_expense_amount(r)

    result = []
    for b in budgets:
        category = str(b.get("category") or "").strip()
        budget_amount = safe_float(b.get("budget_amount"))
        actual = expense_by_category.get(category.lower(), 0.0)
        remaining = budget_amount - actual
        pct = (actual / budget_amount * 100) if budget_amount else 0
        result.append({
            "category": category,
            "budget": budget_amount,
            "budget_display": format_rupiah(budget_amount),
            "actual": actual,
            "actual_display": format_rupiah(actual),
            "remaining": remaining,
            "remaining_display": format_rupiah(remaining),
            "usage_pct": round(pct, 1),
            "status": "over" if remaining < 0 else "warning" if pct >= 80 else "ok",
        })

    result.sort(key=lambda x: x["usage_pct"], reverse=True)
    return result


def get_accounts_summary() -> dict:
    accounts = []
    total = 0.0
    for acc in get_all_records(SHEET_ACCOUNTS):
        balance = safe_float(acc.get("balance"))
        total += balance
        accounts.append({
            "name": acc.get("account_name") or acc.get("name") or "-",
            "balance": balance,
            "balance_display": format_rupiah(balance),
            "type": acc.get("type", ""),
        })
    accounts.sort(key=lambda x: x["balance"], reverse=True)
    return {"total": total, "total_display": format_rupiah(total), "accounts": accounts}


def get_debt_summary_compact() -> dict:
    debts = get_all_records(SHEET_DEBTS)
    active = []
    totals = defaultdict(float)
    for d in debts:
        status = str(d.get("status") or d.get("is_active") or "").strip().lower()
        remaining = safe_float(d.get("remaining_amount") or d.get("amount"))
        if remaining <= 0 or status in {"settled", "closed", "void", "false"}:
            continue
        debt_type = str(d.get("type") or d.get("debt_type") or "").strip().lower()
        if not debt_type:
            # fallback from category/description
            text = normalize_text(" ".join(str(d.get(k, "")) for k in ["category", "description", "catatan"]))
            debt_type = "receivable" if "piutang" in text else "payable" if "utang" in text or "hutang" in text else "unknown"
        totals[debt_type] += remaining
        active.append({
            "person": d.get("person") or d.get("person_name") or d.get("subject") or "-",
            "type": debt_type,
            "remaining_amount": remaining,
            "remaining_amount_display": format_rupiah(remaining),
            "description": d.get("description", ""),
            "id": d.get("id", ""),
        })
    active.sort(key=lambda x: x["remaining_amount"], reverse=True)
    return {
        "total_payable": totals.get("payable", 0.0),
        "total_payable_display": format_rupiah(totals.get("payable", 0.0)),
        "total_receivable": totals.get("receivable", 0.0),
        "total_receivable_display": format_rupiah(totals.get("receivable", 0.0)),
        "active_count": len(active),
        "top_active": active[:8],
    }


def get_net_worth_compact() -> dict:
    assets = get_all_records(SHEET_ASSETS)
    active_assets = []

    total_assets = 0.0

    for a in assets:
        is_active = str(a.get("is_active", "TRUE")).strip().upper() != "FALSE"
        if not is_active:
            continue
        value = safe_float(a.get("current_value"))
        total_assets += value
        active_assets.append({
            "name": a.get("name", "-"),
            "value": value,
            "value_display": format_rupiah(value),
            "category": a.get("category", ""),
            "quantity": a.get("quantity", ""),
            "unit": a.get("unit", ""),
            "price_per_unit": safe_float(a.get("price_per_unit")),
            "price_per_unit_display": format_rupiah(safe_float(a.get("price_per_unit"))),
        })

    accounts = get_accounts_summary()
    return {
        "total_accounts": accounts["total"],
        "total_accounts_display": format_rupiah(accounts["total"]),
        "total_assets": total_assets,
        "total_assets_display": format_rupiah(total_assets),
        "total_liabilities": 0.0,
        "total_liabilities_display": format_rupiah(0),
        "net_worth": accounts["total"] + total_assets,
        "net_worth_display": format_rupiah(accounts["total"] + total_assets),
        "top_assets": sorted(active_assets, key=lambda x: x["value"], reverse=True)[:8],
        "top_liabilities": [],
        "note": "Liabilities sudah dihapus dari fitur net worth; kewajiban antar orang dikelola via /hutang.",
    }


def detect_anomalies(records: list[dict], month_summary: dict | None = None) -> list[dict]:
    records = enrich_finance_transactions(records)
    expenses = [r for r in records if str(r.get("type", "")).strip().lower() == "expense"]
    amounts = [get_effective_expense_amount(r) for r in expenses if get_effective_expense_amount(r) > 0]
    anomalies = []

    if amounts:
        med = median(amounts)
        avg = mean(amounts)
        threshold = max(200_000, med * 3, avg * 2)
        for r in expenses:
            amount = get_effective_expense_amount(r)
            if amount >= threshold:
                anomalies.append({
                    "type": "large_expense",
                    "severity": "warning",
                    "message": "Nominal pengeluaran net jauh lebih besar dari transaksi biasa.",
                    "transaction": compact_transaction(r),
                    "threshold": threshold,
                    "threshold_display": format_rupiah(threshold),
                    "amount_basis": "net_after_receivable",
                })

    # Potential duplicates: same date + amount + normalized description.
    bucket = defaultdict(list)
    for r in records:
        key = (
            str(r.get("date", "")),
            str(r.get("type", "")),
            int(get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))),
            normalize_text(str(r.get("description", "")))[:40],
        )
        if key[2] > 0 and key[3]:
            bucket[key].append(r)
    for items in bucket.values():
        if len(items) > 1:
            anomalies.append({
                "type": "possible_duplicate",
                "severity": "warning",
                "message": "Ada transaksi yang tanggal, nominal, dan deskripsinya mirip.",
                "transactions": [compact_transaction(x) for x in items[:5]],
            })

    # Category spikes vs share.
    if month_summary:
        total_expense = month_summary.get("total_expense", 0) or 0
        for item in month_summary.get("expense_by_category", [])[:5]:
            amount = item.get("amount", 0)
            pct = (amount / total_expense * 100) if total_expense else 0
            if total_expense and pct >= 45:
                anomalies.append({
                    "type": "category_concentration",
                    "severity": "info",
                    "message": f"Kategori {item.get('name')} menyumbang {pct:.1f}% dari pengeluaran.",
                    "category": item.get("name"),
                    "amount": amount,
                    "amount_display": format_rupiah(amount),
                    "contribution_pct": round(pct, 1),
                })

    return anomalies[:12]


def detect_data_quality_issues(records: list[dict]) -> list[dict]:
    issues = []
    counters = Counter()
    examples = defaultdict(list)

    for r in records:
        txn_type = str(r.get("type", "")).strip().lower()
        amount = safe_float(r.get("amount"))
        date = str(r.get("date", "")).strip()
        account = str(r.get("account") or "").strip()
        to_account = str(r.get("to_account") or "").strip()
        category = str(r.get("category") or "").strip()

        def add_issue(key: str):
            counters[key] += 1
            if len(examples[key]) < 5:
                examples[key].append(compact_transaction(r))

        if txn_type not in {"expense", "income", "transfer"}:
            add_issue("type tidak valid/kosong")
        if amount <= 0:
            add_issue("amount kosong/0")
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date):
            add_issue("tanggal invalid/kosong")
        if txn_type in {"expense", "income", "transfer"} and not account:
            add_issue("account kosong")
        if txn_type == "transfer" and not to_account:
            add_issue("transfer tanpa to_account")
        if txn_type in {"expense", "income"} and to_account:
            add_issue("income/expense punya to_account")
        if txn_type == "expense" and not category:
            add_issue("expense tanpa category")
        if txn_type == "expense" and category == "Other Expense":
            add_issue("expense masih Other Expense")
        if txn_type == "expense" and category == "Utang Tanpa Cashflow":
            add_issue("expense kategori Utang Tanpa Cashflow")
            
    for key, count in counters.most_common():
        issues.append({"issue": key, "count": count, "examples": examples[key]})

    return issues


def compare_summaries(current: dict, previous: dict) -> dict:
    def diff(key: str) -> dict:
        cur = float(current.get(key, 0) or 0)
        prev = float(previous.get(key, 0) or 0)
        delta = cur - prev
        pct = (delta / prev * 100) if prev else None
        return {
            "current": cur,
            "current_display": format_rupiah(cur),
            "previous": prev,
            "previous_display": format_rupiah(prev),
            "delta": delta,
            "delta_display": format_rupiah(delta),
            "delta_pct": round(pct, 1) if pct is not None else None,
        }

    return {
        "income": diff("total_income"),
        "expense": diff("total_expense"),
        "net": diff("net"),
    }


def build_monthly_finance_context(month: str | None = None) -> dict:
    month = normalize_month_arg(month)
    prev_month = previous_month(month)

    records = get_month_transactions(month)
    prev_records = get_month_transactions(prev_month)
    summary = summarize_transactions(records)
    prev_summary = summarize_transactions(prev_records)

    summary["expense_by_category"] = add_contribution(
        summary["expense_by_category"],
        summary["total_expense"],
        limit=10,
    )
    summary["income_by_category"] = add_contribution(
        summary["income_by_category"],
        summary["total_income"],
        limit=8,
    )

    return {
        "period": {"type": "month", "month": month, "previous_month": prev_month},
        "summary": summary,
        "comparison_vs_previous_month": compare_summaries(summary, prev_summary),
        "budget_status": get_budget_status(month, records),
        "top_expenses": get_top_transactions(records, "expense", 10),
        "top_income": get_top_transactions(records, "income", 6),
        "anomalies": detect_anomalies(records, summary),
        "data_quality_issues": detect_data_quality_issues(records),
        "accounts": get_accounts_summary(),
        "debts": get_debt_summary_compact(),
        "net_worth": get_net_worth_compact(),
        "available_commands": AVAILABLE_COMMANDS_FOR_AI,
    }


def extract_keywords(question: str) -> list[str]:
    clean = normalize_text(question)
    # Keep meaningful multi-token known phrases.
    keywords = []
    for phrase in ["food beverage", "other expense", "kopi kenangan", "nasi padang", "ptpt"]:
        if phrase in clean:
            keywords.append(phrase)
    for token in clean.split():
        if len(token) < 3:
            continue
        if token in STOPWORDS:
            continue
        if re.fullmatch(r"\d+", token):
            continue
        keywords.append(token)
    # category hint expansion
    for token in list(keywords):
        if token in CATEGORY_HINTS:
            keywords.append(normalize_text(CATEGORY_HINTS[token]))
    # unique preserve order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            unique.append(k)
            seen.add(k)
    return unique[:8]


def search_relevant_transactions(question: str, date_from: str | None = None, date_to: str | None = None, limit: int = 12) -> list[dict]:
    records = get_all_records(SHEET_TRANSACTIONS)
    records = filter_records_by_period(records, date_from, date_to) if (date_from or date_to) else records
    records = enrich_finance_transactions(records)
    keywords = extract_keywords(question)
    if not keywords:
        return []

    scored = []
    for r in records:
        haystack = normalize_text(" ".join(str(r.get(k, "")) for k in [
            "description", "subject", "category", "catatan", "raw_input", "account", "to_account"
        ]))
        score = 0
        for kw in keywords:
            if kw and kw in haystack:
                score += 2 if len(kw) > 4 else 1
        if score:
            scored_amount = get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))
            scored.append((score, str(r.get("date", "")), scored_amount, r))

    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [compact_transaction(r) for _, _, _, r in scored[:limit]]


def has_explicit_period(question: str) -> bool:
    raw = str(question or "").lower()
    if re.search(r"20\d{2}[-/](0?[1-9]|1[0-2])", raw):
        return True
    if re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", raw):
        return True
    period_words = [
        "hari ini", "hariini", "today", "kemarin", "yesterday",
        "minggu ini", "mingguini", "week", "bulan ini", "bulanini",
        "bulan lalu", "last month", "juni", "july", "juli", "mei",
    ]
    return any(w in raw for w in period_words)


def build_ask_finance_context(question: str) -> dict:
    period = parse_period_from_text(question)
    month_context = build_monthly_finance_context(period.get("month"))

    # Untuk pertanyaan transaksi spesifik seperti "kapan terakhir saya beli kopi?",
    # jangan batasi ke bulan berjalan kecuali user menyebut periode eksplisit.
    explicit_period = has_explicit_period(question)
    relevant = search_relevant_transactions(
        question,
        date_from=period.get("date_from") if explicit_period else None,
        date_to=period.get("date_to") if explicit_period else None,
        limit=15,
    )

    return {
        "question": question,
        "period_requested": period,
        "explicit_period": explicit_period,
        "monthly_context": month_context,
        "relevant_transactions": relevant,
        "keyword_used": extract_keywords(question),
    }


def build_audit_context(month: str | None = None) -> dict:
    month = normalize_month_arg(month)
    records = get_month_transactions(month)
    summary = summarize_transactions(records)
    return {
        "period": {"type": "month", "month": month},
        "summary": summary,
        "anomalies": detect_anomalies(records, summary),
        "data_quality_issues": detect_data_quality_issues(records),
        "top_expenses": get_top_transactions(records, "expense", 8),
    }


def build_coach_context(month: str | None = None, question: str = "") -> dict:
    context = build_monthly_finance_context(month)
    target_saving = None
    raw = str(question or "").lower()
    m = re.search(r"(?:nabung|tabung|saving|hemat)\s+(\d+(?:[.,]\d+)?)\s*(juta|jt|rb|ribu|k)?", raw)
    if m:
        value = float(m.group(1).replace(",", "."))
        unit = m.group(2) or ""
        if unit in {"juta", "jt"}:
            value *= 1_000_000
        elif unit in {"rb", "ribu", "k"}:
            value *= 1_000
        target_saving = value

    context["goal"] = {"target_saving": target_saving}
    context["question"] = question
    return context


def should_handle_finance_question(text: str) -> bool:
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    # Jangan ganggu input transaksi/debt yang punya nominal.
    # Bug yang dicegah: "ditalangin X bayar tabungan Y 100k" mengandung kata
    # "tabungan", tapi itu tetap input debt, bukan pertanyaan RAG/coach.
    has_amount = bool(re.search(r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b", raw))
    transaction_or_debt_markers = [
        "ditalangin", "ditalangi", "dibayarin", "duluin", "nitip",
        "talangin", "talangi", "nalangin", "ngetalangin",
        "minjem", "pinjem", "pinjam", "hutang", "utang", "piutang",
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "topup", "top up", "isi", "ngisi",
        "gaji", "dapat", "dapet", "terima", "masuk", "keluar",
    ]
    if has_amount and any(k in raw for k in transaction_or_debt_markers):
        return False

    # Kalau ada nominal tapi bukan transaksi/debt, finance question tetap boleh
    # hanya jika kalimatnya jelas minta saran/target/budget.
    if has_amount and not any(k in raw for k in ["nabung", "tabung", "target", "budget", "saran", "coach", "hemat"]):
        return False
    # Jangan ganggu command-like single token pendek.
    if len(raw.split()) == 1 and raw not in {"insight", "audit", "coach"}:
        return False
    return any(k in raw for k in FINANCE_QUESTION_KEYWORDS)


def route_finance_question_mode(text: str) -> str:
    raw = str(text or "").lower()
    if any(k in raw for k in ["audit", "anomali", "aneh", "duplikat", "data quality", "data yang salah"]):
        return "audit"
    if any(k in raw for k in ["coach", "saran", "rekomendasi", "nabung", "tabung", "hemat", "kurangi"]):
        return "coach"
    if any(k in raw for k in ["budget", "anggaran", "jebol", "sisa budget"]):
        return "budget_assistant"
    if any(k in raw for k in ["insight", "analisis", "narasi", "ringkasan", "laporan"]):
        return "monthly_insight"
    return "ask"


def deterministic_audit_text(context: dict) -> str:
    lines = [f"🧹 Audit Data {context.get('period', {}).get('month', '-')}"]
    issues = context.get("data_quality_issues", [])
    anomalies = context.get("anomalies", [])

    if not issues and not anomalies:
        return "✅ Tidak ada masalah data/anomali besar yang terlihat untuk periode ini."

    if issues:
        lines.append("\nMasalah kualitas data:")
        for item in issues[:8]:
            lines.append(f"• {item.get('issue')}: {item.get('count')} transaksi")

    if anomalies:
        lines.append("\nAnomali yang perlu dicek:")
        for item in anomalies[:8]:
            if item.get("transaction"):
                txn = item["transaction"]
                lines.append(
                    f"• {item.get('message')} — {txn.get('date')} {txn.get('description')} {format_rupiah(txn.get('amount', 0))}"
                )
            else:
                lines.append(f"• {item.get('message')}")

    return "\n".join(lines)


def deterministic_monthly_text(context: dict) -> str:
    period = context.get("period", {})
    summary = context.get("summary", {})
    lines = [f"📌 Insight {period.get('month', '-')}"]
    lines.append(f"Pemasukan: {format_rupiah(summary.get('total_income', 0))}")
    lines.append(f"Pengeluaran: {format_rupiah(summary.get('total_expense', 0))}")
    lines.append(f"Net: {format_rupiah(summary.get('net', 0))}")

    cats = summary.get("expense_by_category", [])[:3]
    if cats:
        lines.append("\nDriver pengeluaran terbesar:")
        for cat in cats:
            lines.append(
                f"• {cat.get('name')}: {format_rupiah(cat.get('amount', 0))} ({cat.get('contribution_pct', 0)}%)"
            )

    budgets = context.get("budget_status", [])[:3]
    if budgets:
        lines.append("\nBudget yang perlu dipantau:")
        for b in budgets:
            lines.append(f"• {b.get('category')}: {b.get('usage_pct')}% terpakai")

    return "\n".join(lines)
