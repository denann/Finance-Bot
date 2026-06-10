from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from telegram import Bot
from app.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID
from app.services.report_service import (
    get_daily_report,
    get_weekly_report,
    get_monthly_report,
    format_rupiah,
)
from app.bot.handlers import build_progress_bar
from app.services.budget_service import get_budget_summary
from app.services.debt_service import get_active_debts
from app.services.recurring_service import process_due_recurring_rules

# ── Helpers ───────────────────────────────────────────────────────────────────
async def job_recurring_run():
    """
    Jalankan recurring transaction otomatis setiap pagi.
    """
    try:
        result = process_due_recurring_rules()

        count_due = result.get("count_due", 0)
        success = result.get("success", [])
        failed = result.get("failed", [])

        # Kalau tidak ada yang jatuh tempo, tidak perlu spam notif.
        if count_due == 0:
            return

        lines = [
            "🔁 *Recurring Transaction Otomatis*\n",
            f"📅 Tanggal run: `{result.get('run_date')}`",
            f"📌 Rule jatuh tempo: *{count_due}*",
        ]

        if success:
            lines.append("\n✅ *Berhasil dibuat:*")

            for item in success:
                rule = item.get("rule", {})
                lines.append(
                    f"• {rule.get('name', '-')}: "
                    f"{format_rupiah(float(rule.get('amount', 0) or 0))} "
                    f"→ next `{item.get('next_run_date', '-')}`"
                )

        if failed:
            lines.append("\n❌ *Gagal:*")

            for item in failed:
                rule = item.get("rule", {})
                lines.append(
                    f"• {rule.get('name', '-')} — {item.get('message', '-')}"
                )

        await send_message("\n".join(lines))

    except Exception as e:
        await send_message(
            f"❌ Gagal menjalankan recurring otomatis:\n`{str(e)}`"
        )
    
async def send_message(text: str):
    """Kirim pesan ke user via bot."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id=ALLOWED_USER_ID,
        text=text,
        parse_mode="Markdown"
    )


# ── Job functions ─────────────────────────────────────────────────────────────

async def job_daily_summary():
    """Kirim ringkasan harian setiap jam 21:00."""
    try:
        report = get_daily_report()

        if report["count"] == 0:
            await send_message(
                f"📅 *Ringkasan Harian — {report['date']}*\n\n"
                f"Tidak ada transaksi hari ini."
            )
            return

        lines = [f"📅 *Ringkasan Harian — {report['date']}*\n"]
        lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Cek budget warning
        budget_summary = get_budget_summary()
        warnings = [b for b in budget_summary if b["status"] in ["warning", "over"]]
        if warnings:
            lines.append("\n⚠️ *Budget Alert:*")
            for w in warnings:
                lines.append(
                    f"  {w['emoji']} {w['category']}: "
                    f"{w['pct_used']}% terpakai"
                )

        await send_message("\n".join(lines))

    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan harian: {str(e)}")


async def job_weekly_summary():
    """Kirim ringkasan mingguan setiap Senin jam 08:00."""
    try:
        report = get_weekly_report()

        lines = [
            f"📆 *Ringkasan Mingguan*\n"
            f"_{report['date_from']} s/d {report['date_to']}_\n"
        ]

        if report["count"] == 0:
            lines.append("Tidak ada transaksi minggu ini.")
            await send_message("\n".join(lines))
            return

        lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Pengeluaran per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Top 3 pengeluaran terbesar
        top = sorted(
            [t for t in report["transactions"] if t.get("type") == "expense"],
            key=lambda x: float(x.get("amount", 0)),
            reverse=True
        )[:3]

        if top:
            lines.append("\n*Top 3 Pengeluaran:*")
            for i, t in enumerate(top, 1):
                lines.append(
                    f"  {i}. {t.get('description', '-')} — "
                    f"*{format_rupiah(float(t.get('amount', 0)))}*"
                )

        await send_message("\n".join(lines))

    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan mingguan: {str(e)}")


async def job_monthly_summary():
    """Kirim laporan bulanan setiap tanggal 1 jam 07:00."""
    try:
        # Laporan bulan LALU (karena dijalankan tanggal 1 bulan baru)
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1

        report = get_monthly_report(year, month)
        month_name = datetime(year, month, 1).strftime("%B %Y")

        lines = [f"📆 *Laporan Bulanan — {month_name}*\n"]

        if report["count"] == 0:
            lines.append("Tidak ada transaksi bulan ini.")
            await send_message("\n".join(lines))
            return

        lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
        lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
        lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
        lines.append(f"📝 Transaksi : {report['count']} item\n")

        if report["by_category"]:
            lines.append("*Pengeluaran per Kategori:*")
            for cat, amount in report["by_category"].items():
                lines.append(f"  • {cat}: {format_rupiah(amount)}")

        # Budget vs realisasi bulan lalu
        budget_summary = get_budget_summary(f"{year}-{month:02d}")
        if budget_summary:
            lines.append("\n*Budget vs Realisasi:*")
            for item in budget_summary:
                bar = build_progress_bar(item["pct_used"])
                lines.append(
                    f"{item['emoji']} {item['category']}\n"
                    f"  {bar} {item['pct_used']}% — "
                    f"Sisa {format_rupiah(item['remaining'])}"
                )

        await send_message("\n".join(lines))

    except Exception as e:
        await send_message(f"⚠️ Gagal generate laporan bulanan: {str(e)}")


async def job_debt_reminder():
    """
    Cek hutang yang mendekati jatuh tempo.
    Kirim reminder H-3 setiap hari jam 08:00.
    """
    try:
        active_debts = get_active_debts(debt_type="payable")
        today = datetime.now().date()
        reminders = []

        for debt in active_debts:
            due_date_str = debt.get("due_date", "")
            if not due_date_str:
                continue

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
            except ValueError:
                continue

        if not reminders:
            return  # Tidak ada yang perlu diingatkan

        lines = ["🔔 *Reminder Hutang*\n"]
        for r in reminders:
            if r["days_left"] == 0:
                label = "⚠️ *HARI INI!*"
            elif r["days_left"] == 1:
                label = "⚠️ Besok"
            else:
                label = f"📅 {r['days_left']} hari lagi"

            lines.append(
                f"{label}\n"
                f"  👤 Kepada : {r['person']}\n"
                f"  💰 Sisa   : {format_rupiah(r['remaining'])}\n"
                f"  📅 Jatuh tempo: {r['due_date']}\n"
            )

        await send_message("\n".join(lines))

    except Exception as e:
        await send_message(f"⚠️ Gagal cek debt reminder: {str(e)}")


# ── Scheduler setup ───────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    """
    Buat dan konfigurasi scheduler.
    Timezone Asia/Jakarta (WIB).
    """
    scheduler = AsyncIOScheduler(timezone="Asia/Jakarta")

    # Ringkasan harian — setiap hari jam 21:00 WIB
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

    # Laporan bulanan — tanggal 1 tiap bulan jam 07:00 WIB
    scheduler.add_job(
        job_monthly_summary,
        CronTrigger(day=1, hour=7, minute=0),
        id="monthly_summary",
        name="Monthly Summary",
        replace_existing=True,
    )

    # Debt reminder — setiap hari jam 08:00 WIB
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