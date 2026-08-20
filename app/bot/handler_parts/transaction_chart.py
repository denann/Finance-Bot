"""Shared read-only delivery for transaction time-series charts."""

from __future__ import annotations

from telegram import InputFile

from app.services.chart_service import build_transaction_timeseries_png_bytes


async def send_transaction_timeseries_chart_message(
    bot,
    chat_id: int,
    transactions: list[dict],
    title: str,
) -> tuple[bool, str]:
    """Render exact rows and require Telegram to acknowledge a photo message.

    Delivery is bot/chat scoped instead of relying on a callback-message reply
    shortcut. The generated PNG stays in memory so callback-message
    accessibility and temporary-file lifetime cannot decide whether the image is
    uploaded. A successful return requires the Telegram response to actually
    contain photo media.
    """

    try:
        png_bytes = build_transaction_timeseries_png_bytes(
            list(transactions or []),
            f"Time Series - {title}",
        )
        if not png_bytes or not bytes(png_bytes).startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Chart renderer tidak menghasilkan PNG yang valid."

        filename = "grafik-transaksi-timeseries.png"
        caption = (
            f"📈 Grafik time series: {title}\n"
            "Basis angka: pengeluaran net dari transaksi yang ditampilkan."
        )
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(bytes(png_bytes), filename=filename),
            caption=caption,
        )
        if not getattr(sent, "photo", None):
            return False, "Telegram tidak mengembalikan pesan foto untuk grafik."
        return True, ""
    except Exception as exc:
        return False, str(exc)
