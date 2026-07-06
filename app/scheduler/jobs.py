"""APScheduler jobs for recurring transactions, reminders, export, and summaries."""



# Import apscheduler.schedulers.asyncio so this module can use its helpers.
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# Import apscheduler.triggers.cron so this module can use its helpers.
from apscheduler.triggers.cron import CronTrigger
# Import datetime so this module can use its helpers.
from datetime import datetime
# Import telegram so this module can use its helpers.
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
# Import app.config so this module can use its helpers.
from app.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID
# Import app.services.report_service so this module can use its helpers.
from app.services.report_service import (
    # Include this value in the surrounding collection or call.
    get_daily_report,
    # Include this value in the surrounding collection or call.
    get_weekly_report,
    # Include this value in the surrounding collection or call.
    get_monthly_report,
    # Include this value in the surrounding collection or call.
    format_rupiah,
    # Include this value in the surrounding collection or call.
    get_effective_expense_amount,
# Close the structure that was opened above.
)
# Import app.bot.handlers so this module can use its helpers.
from app.bot.handlers import build_progress_bar
# Import app.services.budget_service so this module can use its helpers.
from app.services.budget_service import get_budget_summary
# Import app.services.debt_service so this module can use its helpers.
from app.services.debt_service import get_active_debts
# Import app.services.recurring_service so this module can use its helpers.
from app.services.recurring_service import get_due_recurring_rules

# ── Helpers ───────────────────────────────────────────────────────────────────
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
        # Prepare due rules for the next step.
        due_rules = get_due_recurring_rules()

        # Handle the missing or empty due_rules case.
        if not due_rules:
            # Return control to the caller.
            return

        today = datetime.now().strftime("%Y-%m-%d")
        # Open a multi-line structure for the values below.
        lines = [
            "🔁 Recurring Transaction Reminder\n",
            f"📅 Tanggal cek: {today}",
            f"📌 Rule jatuh tempo: {len(due_rules)}",
            "",
            "Sudah bayar belum? Kalau sudah, klik tombol di bawah. Kalau belum, abaikan dulu dan saya ingatkan lagi besok.",
            "",
        # Close the structure that was opened above.
        ]

        # Prepare keyboard for the next step.
        keyboard = []
        # Process each rule in the current collection.
        for rule in due_rules:
            name = str(rule.get("name") or "-").strip()
            amount = format_rupiah(float(rule.get("amount", 0) or 0))
            account = str(rule.get("account") or "-").strip()
            lines.append(f"• {name} — {amount} dari {account}")

            rule_id = str(rule.get("id") or "").strip()
            # Handle the case where rule_id.
            if rule_id:
                # Open a multi-line structure for the values below.
                keyboard.append([
                    # Open a multi-line structure for the values below.
                    InlineKeyboardButton(
                        f"✅ Sudah bayar: {name[:24]}",
                        callback_data=f"recurring_paid:{rule_id}",
                    # Close the structure that was opened above.
                    )
                # Close the structure that was opened above.
                ])

        # Wait for send_message before continuing this flow.
        await send_message(
            "\n".join(lines),
            # Prepare parse mode for the next step.
            parse_mode=None,
            # Prepare reply markup for the next step.
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for send_message before continuing this flow.
        await send_message(
            f"❌ Gagal menjalankan recurring reminder:\n{str(e)}",
            # Prepare parse mode for the next step.
            parse_mode=None,
        # Close the structure that was opened above.
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
    # Prepare bot for the next step.
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    # Wait for bot.send_message before continuing this flow.
    await bot.send_message(
        # Prepare chat id for the next step.
        chat_id=ALLOWED_USER_ID,
        # Prepare text for the next step.
        text=text,
        # Prepare parse mode for the next step.
        parse_mode=parse_mode,
        # Prepare reply markup for the next step.
        reply_markup=reply_markup,
    # Close the structure that was opened above.
    )


# ── Job functions ─────────────────────────────────────────────────────────────

# Define format scheduler expense amount for callers in this flow.
def format_scheduler_expense_amount(net_amount: float, gross_amount: float | None = None) -> str:
    """Format scheduler expense output as net amount with optional gross value.

    Args:
        net_amount: Expense amount after subtracting linked receivable shares.
        gross_amount: Original transaction amount before receivable subtraction.

    Returns:
        `Rpnet (Rpgross)` when net and gross differ, otherwise just `Rpamount`.
    """
    # Prepare net for the next step.
    net = float(net_amount or 0)
    # Prepare gross for the next step.
    gross = float(gross_amount if gross_amount is not None else net)
    # Handle the case where abs(net - gross) > 0.0001.
    if abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    # Return format_rupiah(net) to the caller.
    return format_rupiah(net)


# Define append scheduler top expenses for callers in this flow.
def append_scheduler_top_expenses(lines: list[str], report: dict):
    """Append scheduler Top 3 expenses sorted by net expense.

    Args:
        lines: Mutable Markdown line list for the scheduled summary message.
        report: Daily, weekly, or monthly report dict containing enriched
            transactions.

    Returns:
        None. The function appends lines only when positive net expenses exist.
    """
    # Open a multi-line structure for the values below.
    expenses = [
        txn for txn in (report or {}).get("transactions", [])
        if str((txn or {}).get("type", "")).strip().lower() == "expense"
        # Run this statement as part of the current workflow.
        and get_effective_expense_amount(txn) > 0
    # Close the structure that was opened above.
    ]
    # Prepare top for the next step.
    top = sorted(expenses, key=get_effective_expense_amount, reverse=True)[:3]
    # Handle the missing or empty top case.
    if not top:
        # Return control to the caller.
        return

    lines.append("\n*Top 3 Pengeluaran:*")
    # Process each i, txn in the current collection.
    for i, txn in enumerate(top, 1):
        # Prepare net amount for the next step.
        net_amount = get_effective_expense_amount(txn)
        gross_amount = float((txn or {}).get("amount", 0) or 0)
        # Open a multi-line structure for the values below.
        lines.append(
            f"  {i}. {txn.get('description', '-')} - "
            f"*{format_scheduler_expense_amount(net_amount, gross_amount)}*"
        # Close the structure that was opened above.
        )


# Handle the asynchronous job daily summary workflow.
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
        # Prepare report for the next step.
        report = get_daily_report()

        if report["count"] == 0:
            # Wait for send_message before continuing this flow.
            await send_message(
                f"📅 *Ringkasan Harian — {report['date']}*\n\n"
                f"Tidak ada transaksi hari ini."
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        lines = [f"📅 *Ringkasan Harian — {report['date']}*\n"]
        lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"❌ Pengeluaran: *{format_scheduler_expense_amount(report['total_expense'], report.get('total_gross_expense'))}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Check budget warning
        budget_summary = get_budget_summary()
        warnings = [b for b in budget_summary if b["status"] in ["warning", "over"]]
        # Handle the case where warnings.
        if warnings:
            lines.append("\n⚠️ *Budget Alert:*")
            # Process each w in the current collection.
            for w in warnings:
                # Open a multi-line structure for the values below.
                lines.append(
                    f"  {w['emoji']} {w['category']}: "
                    f"{w['pct_used']}% terpakai"
                # Close the structure that was opened above.
                )

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan harian: {str(e)}")


# Handle the asynchronous job weekly summary workflow.
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
        # Prepare report for the next step.
        report = get_weekly_report()

        # Open a multi-line structure for the values below.
        lines = [
            f"📆 *Ringkasan Mingguan*\n"
            f"_{report['date_from']} s/d {report['date_to']}_\n"
        # Close the structure that was opened above.
        ]

        if report["count"] == 0:
            lines.append("Tidak ada transaksi minggu ini.")
            await send_message("\n".join(lines))
            # Return control to the caller.
            return

        lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"❌ Pengeluaran: *{format_scheduler_expense_amount(report['total_expense'], report.get('total_gross_expense'))}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Pengeluaran per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Run this statement as part of the current workflow.
        append_scheduler_top_expenses(lines, report)

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan mingguan: {str(e)}")


# Handle the asynchronous job monthly summary workflow.
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
        now = datetime.now()
        # Handle the case where now.month == 1.
        if now.month == 1:
            # Run this statement as part of the current workflow.
            year, month = now.year - 1, 12
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Run this statement as part of the current workflow.
            year, month = now.year, now.month - 1

        # Prepare report for the next step.
        report = get_monthly_report(year, month)
        month_name = datetime(year, month, 1).strftime("%B %Y")

        lines = [f"📆 *Laporan Bulanan — {month_name}*\n"]

        if report["count"] == 0:
            lines.append("Tidak ada transaksi bulan ini.")
            await send_message("\n".join(lines))
            # Return control to the caller.
            return

        lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"❌ Pengeluaran: *{format_scheduler_expense_amount(report['total_expense'], report.get('total_gross_expense'))}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Pengeluaran per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Budget warning section for the same monthly period.
        budget_summary = get_budget_summary(f"{year}-{month:02d}")
        # Handle the case where budget_summary.
        if budget_summary:
            lines.append("\n*Budget vs Realisasi:*")
            # Process each item in the current collection.
            for item in budget_summary:
                bar = build_progress_bar(item["pct_used"])
                # Open a multi-line structure for the values below.
                lines.append(
                    f"{item['emoji']} {item['category']}\n"
                    f"  {bar} {item['pct_used']}% — "
                    f"Sisa {format_rupiah(item['remaining'])}"
                # Close the structure that was opened above.
                )

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan bulanan: {str(e)}")


# Handle the asynchronous job debt reminder workflow.
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
        active_debts = get_active_debts(debt_type="payable")
        # Prepare today for the next step.
        today = datetime.now().date()
        # Prepare reminders for the next step.
        reminders = []

        # Process each debt in the current collection.
        for debt in active_debts:
            due_date_str = debt.get("due_date", "")
            # Handle the missing or empty due_date_str case.
            if not due_date_str:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Run this operation in a guarded block so failures can be handled.
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                # Prepare days left for the next step.
                days_left = (due_date - today).days

                # Handle the case where 0 <= days_left <= 3.
                if 0 <= days_left <= 3:
                    # Open a multi-line structure for the values below.
                    reminders.append({
                        "person": debt.get("person_name"),
                        "remaining": float(debt.get("remaining_amount", 0)),
                        "due_date": due_date_str,
                        "days_left": days_left,
                    # Close the structure that was opened above.
                    })
            # Handle an expected failure from the guarded operation above.
            except ValueError:
                # Skip the rest of this loop iteration after handling this case.
                continue

        # Handle the missing or empty reminders case.
        if not reminders:
            # Return # Nothing needs to be reminded right now to the caller.
            return  # Nothing needs to be reminded right now

        lines = ["🔔 *Reminder Hutang*\n"]
        # Process each r in the current collection.
        for r in reminders:
            if r["days_left"] == 0:
                label = "⚠️ *HARI INI!*"
            elif r["days_left"] == 1:
                label = "⚠️ Besok"
            # Handle the fallback path after earlier conditions are skipped.
            else:
                label = f"📅 {r['days_left']} hari lagi"

            # Open a multi-line structure for the values below.
            lines.append(
                f"{label}\n"
                f"  👤 Kepada : {r['person']}\n"
                f"  💰 Sisa   : {format_rupiah(r['remaining'])}\n"
                f"  📅 Jatuh tempo: {r['due_date']}\n"
            # Close the structure that was opened above.
            )

        await send_message("\n".join(lines))

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await send_message(f"⚠️ Gagal cek debt reminder: {str(e)}")


# ── Scheduler setup ───────────────────────────────────────────────────────────

# Define create scheduler for callers in this flow.
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
        # Include this value in the surrounding collection or call.
        job_daily_summary,
        # Include this value in the surrounding collection or call.
        CronTrigger(hour=21, minute=0),
        id="daily_summary",
        name="Daily Summary",
        # Prepare replace existing for the next step.
        replace_existing=True,
    # Close the structure that was opened above.
    )

    # Ringkasan mingguan — setiap Senin jam 08:00 WIB
    scheduler.add_job(
        # Include this value in the surrounding collection or call.
        job_weekly_summary,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_summary",
        name="Weekly Summary",
        # Prepare replace existing for the next step.
        replace_existing=True,
    # Close the structure that was opened above.
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    scheduler.add_job(
        # Include this value in the surrounding collection or call.
        job_monthly_summary,
        # Include this value in the surrounding collection or call.
        CronTrigger(day=1, hour=7, minute=0),
        id="monthly_summary",
        name="Monthly Summary",
        # Prepare replace existing for the next step.
        replace_existing=True,
    # Close the structure that was opened above.
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    scheduler.add_job(
        # Include this value in the surrounding collection or call.
        job_debt_reminder,
        # Include this value in the surrounding collection or call.
        CronTrigger(hour=8, minute=0),
        id="debt_reminder",
        name="Debt Reminder",
        # Prepare replace existing for the next step.
        replace_existing=True,
    # Close the structure that was opened above.
    )

    # Open a multi-line structure for the values below.
    scheduler.add_job(
        # Include this value in the surrounding collection or call.
        job_recurring_run,
        "cron",
        # Prepare hour for the next step.
        hour=6,
        # Prepare minute for the next step.
        minute=30,
        id="recurring_run",
        # Prepare replace existing for the next step.
        replace_existing=True,
    # Close the structure that was opened above.
    )
    # Return scheduler to the caller.
    return scheduler
