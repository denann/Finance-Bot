"""Execute validated command mutations only after immutable confirmation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.net_worth_service import create_net_worth_snapshot, deactivate_asset, update_asset
from app.services.pending_expense_service import cancel_pending_expense, mark_pending_paid
from app.services.recurring_service import disable_recurring_rule, edit_recurring_rule, mark_recurring_rule_paid, process_due_recurring_rules


def _rupiah(value: Any) -> str:
    """Format a numeric value without importing Telegram handler utilities."""

    return "Rp{:,.0f}".format(float(value or 0)).replace(",", ".")


def execute_command_mutation(operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one allow-listed financial command mutation.

    Args:
        operation: Stable operation name produced by the preview handler.
        arguments: Immutable validated arguments displayed in that preview.

    Returns:
        Result with ``success`` and a concise user-facing ``display_text``.

    Side effects:
        Calls exactly one allow-listed service flow. Callers must wrap this
        function in the existing Sheets transaction boundary.
    """

    if operation == "pending_paid":
        result = mark_pending_paid(arguments["pending_id"], account=arguments.get("account"))
        if not result.get("success"):
            return {"success": False, "display_text": f"❌ {result.get('message', 'Gagal menandai pending sebagai paid.')}"}
        return {
            "success": True,
            "display_text": (
                "✅ *Pending expense sudah dicatat sebagai transaksi aktual.*\n\n"
                f"🔖 Pending ID: `{result.get('pending_id')}`\n"
                f"🔖 Transaction ID: `{result.get('transaction_id')}`\n"
                f"💳 Rekening: *{result.get('account') or '-'}*\n"
                f"💰 Nominal keluar: *-{_rupiah(result.get('amount'))}*"
            ),
            "result": result,
        }

    if operation == "pending_cancel":
        result = cancel_pending_expense(arguments["pending_id"])
        return {
            "success": bool(result.get("success")),
            "display_text": (
                f"✅ Pending expense dibatalkan.\n🔖 `{arguments['pending_id']}`"
                if result.get("success")
                else f"❌ {result.get('message', 'Gagal membatalkan pending expense.')}"
            ),
            "result": result,
        }

    if operation == "recurring_run":
        result = process_due_recurring_rules()
        failed = result.get("failed") or []
        success = result.get("success") or []
        return {
            "success": not failed,
            "display_text": (
                "✅ *Recurring run selesai.*\n\n"
                f"📌 Jatuh tempo: *{result.get('count_due', 0)}*\n"
                f"✅ Berhasil/idempotent: *{len(success)}*\n"
                f"❌ Gagal: *{len(failed)}*"
            ) if not failed else "❌ Recurring run gagal dan operasi tidak dinyatakan berhasil.",
            "result": result,
        }

    if operation == "recurring_occurrence_paid":
        scheduled = datetime.strptime(arguments["scheduled_run_date"], "%Y-%m-%d").date()
        result = mark_recurring_rule_paid(arguments["rule_id"], scheduled_run_date=scheduled)
        if result.get("success") and result.get("duplicate"):
            text = "✅ Occurrence recurring ini sudah pernah diproses. Tidak ada transaksi atau saldo yang ditambahkan lagi."
        elif result.get("success"):
            text = (
                "✅ *Recurring ditandai sudah bayar.*\n\n"
                f"📝 Transaksi tersimpan: {result.get('transaction_id')}\n"
                f"🔕 Notifikasi berikutnya: {result.get('next_run_date')}"
            )
        else:
            text = f"❌ Gagal menandai recurring sudah bayar.\n\n{result.get('message') or '-'}"
        return {"success": bool(result.get("success")), "display_text": text, "result": result}

    if operation == "recurring_edit":
        result = edit_recurring_rule(arguments["rule_id"], arguments["updates"])
        return {
            "success": bool(result.get("success")),
            "display_text": (
                f"✅ Recurring rule `{arguments['rule_id']}` berhasil diupdate."
                if result.get("success")
                else f"❌ {result.get('message', 'Gagal edit recurring rule.')}"
            ),
            "result": result,
        }

    if operation == "recurring_off":
        success = disable_recurring_rule(arguments["rule_id"])
        return {
            "success": bool(success),
            "display_text": (
                f"✅ Recurring rule berhasil dinonaktifkan:\n`{arguments['rule_id']}`"
                if success else "❌ Recurring rule tidak ditemukan."
            ),
        }

    if operation == "asset_update":
        result = update_asset(arguments["asset_id"], arguments["updates"])
        return {
            "success": bool(result.get("success")),
            "display_text": (
                f"✅ Aset `{arguments['asset_id']}` berhasil diupdate."
                if result.get("success")
                else f"❌ {result.get('message', 'Gagal update aset.')}"
            ),
            "result": result,
        }

    if operation == "asset_off":
        success = deactivate_asset(arguments["asset_id"])
        return {
            "success": bool(success),
            "display_text": (
                f"✅ Asset berhasil dinonaktifkan:\n`{arguments['asset_id']}`"
                if success else "❌ Asset tidak ditemukan."
            ),
        }

    if operation == "networth_snapshot":
        snapshot = create_net_worth_snapshot(summary=arguments["summary"])
        return {
            "success": True,
            "display_text": (
                "✅ *Snapshot Net Worth berhasil disimpan!*\n\n"
                f"📅 Tanggal: `{snapshot.get('snapshot_date')}`\n"
                f"💰 Rekening: *{_rupiah(snapshot.get('total_accounts'))}*\n"
                f"📦 Aset: *{_rupiah(snapshot.get('total_assets'))}*\n"
                f"🏁 Net Worth: *{_rupiah(snapshot.get('net_worth'))}*"
            ),
            "result": snapshot,
        }

    return {"success": False, "display_text": "❌ Jenis mutasi tidak dikenali. Tidak ada data yang diubah."}
