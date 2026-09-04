"""APScheduler jobs for recurring transactions, reminders, export, and summaries."""



# Import apscheduler.schedulers.asyncio so this module can use its helpers.
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# Import apscheduler.triggers.cron so this module can use its helpers.
from apscheduler.triggers.cron import CronTrigger
# Import datetime so this module can use its helpers.
from datetime import datetime
from app.clock import business_now
from app.application.external_io import run_scheduled
from app.sheets.client import sheets_request_snapshot
# Import telegram so this module can use its helpers.
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
# Import app.config so this module can use its helpers.
from app.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID
# Import app.services.report_service so this module can use its helpers.
from app.services.report_service import (
    get_daily_report,
    get_weekly_report,
    get_monthly_report,
    format_rupiah,
    get_effective_expense_amount,
)
# Import app.bot.handlers so this module can use its helpers.
from app.bot.handler_parts.common_imports import build_progress_bar
# Import app.services.budget_service so this module can use its helpers.
from app.services.budget_service import get_budget_summary
# Import app.services.debt_service so this module can use its helpers.
from app.services.debt_service import get_active_debts
# Import app.services.recurring_service so this module can use its helpers.
from app.services.recurring_service import get_due_recurring_rules

# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_scheduled_snapshot(function, *args):
    """Run one scheduled read bundle with a request-local Sheets snapshot."""

    with sheets_request_snapshot():
        return function(*args)


def _load_daily_payload():
    return get_daily_report(), get_budget_summary()


def _load_monthly_payload(year: int, month: int):
    return get_monthly_report(year, month), get_budget_summary(f"{year}-{month:02d}")

async def job_recurring_run():
    """Coordinate the job recurring run logic in the scheduler layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        due_rules = await run_scheduled(
            "recurring_due_rules", _load_scheduled_snapshot, get_due_recurring_rules
        )

        # Validate missing due rules before continuing.
        if not due_rules:
            return

        today = business_now().strftime("%Y-%m-%d")
        lines = [
            "🔁 Recurring Transaction Reminder\n",
            f"📅 Tanggal cek: {today}",
            f"📌 Rule jatuh tempo: {len(due_rules)}",
            "",
            "Sudah bayar belum? Kalau sudah, klik tombol di bawah. Kalau belum, abaikan dulu dan saya ingatkan lagi besok.",
            "",
        ]

        # Build keyboard for the response flow.
        keyboard = []
        # Iterate through each rule.
        for rule in due_rules:
            name = str(rule.get("name") or "-").strip()
            amount = format_rupiah(float(rule.get("amount", 0) or 0))
            account = str(rule.get("account") or "-").strip()
            lines.append(f"• {name} — {amount} dari {account}")

            rule_id = str(rule.get("id") or "").strip()
            scheduled_run_date = str(rule.get("next_run_date") or "").strip()
            if rule_id:
                keyboard.append([
                    InlineKeyboardButton(
                        f"✅ Sudah bayar: {name[:24]}",
                        callback_data=f"recurring_paid:{rule_id}:{scheduled_run_date}",
                    )
                ])

        # Send the Telegram response before continuing.
        await send_message(
            "\n".join(lines),
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await send_message(
            f"❌ Gagal menjalankan recurring reminder:\n{str(e)}",
            parse_mode=None,
        )


async def send_message(text: str, parse_mode: str | None = "Markdown", reply_markup=None):
    """Coordinate the send message logic in the scheduler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    # Send the Telegram response before continuing.
    await bot.send_message(
        chat_id=ALLOWED_USER_ID,
        # Prepare text from the incoming input.
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


# ── Job functions ─────────────────────────────────────────────────────────────

# Helper for format scheduler expense amount.
def format_scheduler_expense_amount(net_amount: float, gross_amount: float | None = None) -> str:
    """Format scheduler expense output as net amount with optional gross value.

    Args:
        net_amount: Expense amount after subtracting linked receivable shares.
        gross_amount: Original transaction amount before receivable subtraction.

    Returns:
        `Rpnet (Rpgross)` when net and gross differ, otherwise just `Rpamount`.
    """
    net = float(net_amount or 0)
    gross = float(gross_amount if gross_amount is not None else net)
    if abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    return format_rupiah(net)


# Helper for append scheduler top expenses.
def append_scheduler_top_expenses(lines: list[str], report: dict):
    """Append scheduler Top 3 expenses sorted by net expense.

    Args:
        lines: Mutable Markdown line list for the scheduled summary message.
        report: Daily, weekly, or monthly report dict containing enriched
            transactions.

    Returns:
        None. The function appends lines only when positive net expenses exist.
    """
    expenses = [
        txn for txn in (report or {}).get("transactions", [])
        if str((txn or {}).get("type", "")).strip().lower() == "expense"
        and get_effective_expense_amount(txn) > 0
    ]
    top = sorted(expenses, key=get_effective_expense_amount, reverse=True)[:3]
    # Validate missing top before continuing.
    if not top:
        return

    lines.append("\n*Top 3 Pengeluaran:*")
    # Iterate through each i, txn.
    for i, txn in enumerate(top, 1):
        # Extract net amount for validation.
        net_amount = get_effective_expense_amount(txn)
        gross_amount = float((txn or {}).get("amount", 0) or 0)
        lines.append(
            f"  {i}. {txn.get('description', '-')} - "
            f"*{format_scheduler_expense_amount(net_amount, gross_amount)}*"
        )


async def job_daily_summary():
    """Coordinate the job daily summary logic in the scheduler layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        report, budget_summary = await run_scheduled(
            "daily_summary_data", _load_scheduled_snapshot, _load_daily_payload
        )

        if report["count"] == 0:
            # Send the Telegram response before continuing.
            await send_message(
                f"📅 *Ringkasan Harian — {report['date']}*\n\n"
                f"Tidak ada transaksi hari ini."
            )
            return

        lines = [f"📅 *Ringkasan Harian — {report['date']}*\n"]
        lines.append(f"+ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"- Pengeluaran: *{format_scheduler_expense_amount(report['total_expense'], report.get('total_gross_expense'))}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Check budget warning
        # Budget data was loaded in the same request-scoped worker snapshot.
        warnings = [b for b in budget_summary if b["status"] in ["warning", "over"]]
        if warnings:
            lines.append("\n⚠️ *Budget Alert:*")
            # Iterate through each w.
            for w in warnings:
                lines.append(
                    f"  {w['emoji']} {w['category']}: "
                    f"{w['pct_used']}% terpakai"
                )

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan harian: {str(e)}")


async def job_weekly_summary():
    """Coordinate the job weekly summary logic in the scheduler layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        report = await run_scheduled(
            "weekly_summary_data", _load_scheduled_snapshot, get_weekly_report
        )

        lines = [
            f"📆 *Ringkasan Mingguan*\n"
            f"_{report['date_from']} s/d {report['date_to']}_\n"
        ]

        if report["count"] == 0:
            lines.append("Tidak ada transaksi minggu ini.")
            await send_message("\n".join(lines))
            return

        lines.append(f"+ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"- Pengeluaran: *{format_scheduler_expense_amount(report['total_expense'], report.get('total_gross_expense'))}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Pengeluaran per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        append_scheduler_top_expenses(lines, report)

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan mingguan: {str(e)}")


async def job_monthly_summary():
    """Coordinate the job monthly summary logic in the scheduler layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Date parsing note: keep explicit and relative Indonesian date formats predictable.
        now = business_now()
        if now.month == 1:
            year, month = now.year - 1, 12
        # Use the fallback path when no earlier branch matched.
        else:
            year, month = now.year, now.month - 1

        report, budget_summary = await run_scheduled(
            "monthly_summary_data", _load_scheduled_snapshot, _load_monthly_payload, year, month
        )
        month_name = datetime(year, month, 1).strftime("%B %Y")

        lines = [f"📆 *Laporan Bulanan — {month_name}*\n"]

        if report["count"] == 0:
            lines.append("Tidak ada transaksi bulan ini.")
            await send_message("\n".join(lines))
            return

        lines.append(f"+ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"- Pengeluaran: *{format_scheduler_expense_amount(report['total_expense'], report.get('total_gross_expense'))}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Pengeluaran per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Budget warning section for the same monthly period.
        # Budget data was loaded together with the monthly report.
        if budget_summary:
            lines.append("\n*Budget vs Realisasi:*")
            # Iterate through each item.
            for item in budget_summary:
                bar = build_progress_bar(item["pct_used"])
                lines.append(
                    f"{item['emoji']} {item['category']}\n"
                    f"  {bar} {item['pct_used']}% — "
                    f"Sisa {format_rupiah(item['remaining'])}"
                )

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan bulanan: {str(e)}")


async def job_debt_reminder():
    """Coordinate the job debt reminder logic in the scheduler layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        active_debts = await run_scheduled(
            "debt_reminder_data", _load_scheduled_snapshot, get_active_debts, "payable"
        )
        today = business_now().date()
        reminders = []

        # Iterate through each debt.
        for debt in active_debts:
            due_date_str = debt.get("due_date", "")
            # Validate missing due date str before continuing.
            if not due_date_str:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Run this operation in a guarded block so failures can be handled.
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_left = (due_date - today).days

                if 0 <= days_left <= 3:
                    reminders.append({
                        "person": debt.get("person_name"),
                        "remaining": float(debt.get("remaining_amount", 0)),
                        "due_date": due_date_str,
                        "days_left": days_left,
                    })
            # Handle an expected failure from the guarded operation above.
            except ValueError:
                # Skip the rest of this loop iteration after handling this case.
                continue

        # Validate missing reminders before continuing.
        if not reminders:
            return  # Nothing needs to be reminded right now

        lines = ["🔔 *Reminder Hutang*\n"]
        # Iterate through each r.
        for r in reminders:
            if r["days_left"] == 0:
                label = "⚠️ *HARI INI!*"
            elif r["days_left"] == 1:
                label = "⚠️ Besok"
            # Use the fallback path when no earlier branch matched.
            else:
                label = f"📅 {r['days_left']} hari lagi"

            lines.append(
                f"{label}\n"
                f"  👤 Kepada : {r['person']}\n"
                f"  💰 Sisa   : {format_rupiah(r['remaining'])}\n"
                f"  📅 Jatuh tempo: {r['due_date']}\n"
            )

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal cek debt reminder: {str(e)}")


# ── Scheduler setup ───────────────────────────────────────────────────────────

# Helper for create scheduler.
def create_scheduler() -> AsyncIOScheduler:
    """Coordinate the create scheduler logic in the scheduler layer.

    Args:
        None.

    Returns:
        `AsyncIOScheduler` value as defined by the function signature.

    Side effects:
        May send scheduled Telegram messages or invoke scheduled finance jobs according to the existing job implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    scheduler = AsyncIOScheduler(timezone="Asia/Jakarta")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    scheduler.add_job(
        job_daily_summary,
        CronTrigger(hour=21, minute=0),
        id="daily_summary",
        name="Daily Summary",
        replace_existing=True,
    )

    # Ringkasan mingguan — setiap Senin jam 08:00 WIB
    scheduler.add_job(
        job_weekly_summary,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_summary",
        name="Weekly Summary",
        replace_existing=True,
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    scheduler.add_job(
        job_monthly_summary,
        CronTrigger(day=1, hour=7, minute=0),
        id="monthly_summary",
        name="Monthly Summary",
        replace_existing=True,
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    scheduler.add_job(
        job_debt_reminder,
        CronTrigger(hour=8, minute=0),
        id="debt_reminder",
        name="Debt Reminder",
        replace_existing=True,
    )

    scheduler.add_job(
        job_recurring_run,
        "cron",
        hour=6,
        minute=30,
        id="recurring_run",
        replace_existing=True,
    )
    return scheduler
