"""Matplotlib-based PNG chart generation for monthly finance reports."""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import calendar so this module can use its helpers.
from calendar import monthrange
# Import io so this module can use its helpers.
from io import BytesIO
# Import pathlib so this module can use its helpers.
from pathlib import Path
# Import tempfile for this module's local operations.
import tempfile


# Prepare CHART DPI for the next step.
CHART_DPI = 140
# Prepare CHART FIGSIZE for the next step.
CHART_FIGSIZE = (9.6, 5.4)
CHART_FONT_FAMILY = ["DejaVu Sans", "Segoe UI", "Arial", "sans-serif"]
CHART_TEXT = "#111827"
CHART_MUTED = "#6b7280"
CHART_GRID = "#e5e7eb"
# Open a multi-line structure for the values below.
CHART_COLORS = [
    "#2563eb",
    "#16a34a",
    "#dc2626",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#be185d",
    "#4b5563",
# Close the structure that was opened above.
]


# Define safe float for callers in this flow.
def safe_float(value, default: float = 0.0) -> float:
    """Convert chart input values into float safely.

    Args:
        value: Raw numeric value from report or transaction dictionaries. This
            may be an int, float, numeric string, empty value, or `None`.
        default: Fallback float returned when conversion fails.

    Returns:
        Float representation of `value`, or `default` when the value cannot be
        converted.

    Side effects:
        None.

    Flow constraints:
        This helper is local to chart rendering and must not normalize values
        back into report data or Google Sheets.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return float(value) to the caller.
        return float(value)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return float(default) to the caller.
        return float(default)


# Define get chart effective expense amount for callers in this flow.
def get_chart_effective_expense_amount(txn: dict) -> float:
    """Return the net expense amount used by chart calculations.

    Args:
        txn: Transaction dict from an enriched monthly report. Expense rows may
            include `net_expense_after_receivable`; otherwise the helper falls
            back to `amount - debt_receivable_original/debt_receivable_remaining`.

    Returns:
        Float net expense amount. Non-expense rows return their raw amount so
        mixed-row callers do not fail.

    Side effects:
        None. This helper only reads the transaction dict.

    Flow constraints:
        Keep this logic aligned with `report_service.get_effective_expense_amount`
        without importing `report_service`, because that module loads Google
        Sheets dependencies that are unnecessary for chart rendering.
    """
    amount = safe_float((txn or {}).get("amount", 0))
    if str((txn or {}).get("type", "") or "").strip().lower() != "expense":
        # Return amount to the caller.
        return amount
    if "net_expense_after_receivable" in (txn or {}):
        return max(safe_float((txn or {}).get("net_expense_after_receivable", amount)), 0.0)
    # Open a multi-line structure for the values below.
    receivable = safe_float(
        (txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0))
    # Close the structure that was opened above.
    )
    # Return max(amount - receivable, 0.0) to the caller.
    return max(amount - receivable, 0.0)


# Define compact rupiah for callers in this flow.
def compact_rupiah(amount: float) -> str:
    """Format a rupiah amount into a short chart-safe label.

    Args:
        amount: Numeric rupiah value. `None`, empty, or falsey values are
            treated as `0`.

    Returns:
        Short display string such as `500k`, `1.2jt`, `-250k`, or `0`.

    Side effects:
        None. This helper only formats numeric input.

    Flow constraints:
        Used only for chart labels; it must not change the underlying report
        totals used by `/bulanan` or `/grafik`.
    """
    # Prepare value for the next step.
    value = float(amount or 0)
    # Prepare abs value for the next step.
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    # Handle the case where abs_value >= 1_000_000.
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.1f}jt".replace(".0jt", "jt")
    # Handle the case where abs_value >= 1_000.
    if abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.0f}k"
    return f"{sign}{abs_value:.0f}"


# Define transaction day for callers in this flow.
def transaction_day(txn: dict) -> int | None:
    """Extract the day-of-month from a transaction row.

    Args:
        txn: Transaction-like dict containing a `date` field in `YYYY-MM-DD`
            format.

    Returns:
        Day number from `1` to `31`, or `None` when the date is missing or
        invalid.

    Side effects:
        None. Invalid input is ignored instead of raising so chart generation
        can continue.

    Flow constraints:
        This helper is read-only and must not normalize or write transaction
        dates back to Google Sheets.
    """
    raw = str((txn or {}).get("date", "") or "").strip()
    # Run this operation in a guarded block so failures can be handled.
    try:
        return int(raw.split("-")[2])
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None


# Define monthly day count for callers in this flow.
def monthly_day_count(month_label: str) -> int:
    """Return the number of days represented by a `YYYY-MM` month label.

    Args:
        month_label: Month string such as `2026-06`.

    Returns:
        Integer day count for the requested month. Invalid input falls back to
        `31` so a chart can still render a safe placeholder.

    Side effects:
        None.

    Flow constraints:
        The fallback is only for rendering tolerance; command handlers still own
        user-facing month validation.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        year, month = [int(x) for x in str(month_label or "").split("-", 1)]
        # Return monthrange(year, month)[1] to the caller.
        return monthrange(year, month)[1]
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return 31 to the caller.
        return 31


# Define daily net expense series for callers in this flow.
def daily_net_expense_series(report: dict) -> list[float]:
    """Build daily net expense values from a monthly report.

    Args:
        report: Monthly report dict from `get_monthly_report`, expected to
            contain `month` and an iterable `transactions` list.

    Returns:
        List of daily net expense totals. The list length follows the target
        month and each item is a float rupiah amount for that day.

    Side effects:
        None. This helper only reads report data.

    Flow constraints:
        Expense values use `get_chart_effective_expense_amount` so charts stay
        consistent with net-expense monthly summaries.
    """
    days = monthly_day_count((report or {}).get("month", ""))
    # Prepare values for the next step.
    values = [0.0 for _ in range(days)]
    for txn in (report or {}).get("transactions", []) or []:
        if str((txn or {}).get("type", "")).strip().lower() != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare day for the next step.
        day = transaction_day(txn)
        # Handle the case where day is None or day < 1 or day > days.
        if day is None or day < 1 or day > days:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Run this statement as part of the current workflow.
        values[day - 1] += get_chart_effective_expense_amount(txn)
    # Return values to the caller.
    return values


# Define transaction net expense series for callers in this flow.
def transaction_net_expense_series(transactions: list[dict]) -> list[tuple[str, float]]:
    """Build daily net expense points from an arbitrary transaction list.

    Args:
        transactions: Transaction dictionaries from `/transaksi`, `/last`, or
            another read-only list command. Each row may contain `date`, `type`,
            `amount`, and receivable adjustment fields.

    Returns:
        A list of `(date_label, net_expense)` tuples sorted by date ascending.
        Only expense rows contribute to the value; income and transfers stay out
        of the expense time series.

    Side effects:
        None. This helper only reads transaction dictionaries and does not write
        to Google Sheets or mutate bot state.

    Flow constraints:
        The net expense amount must use `get_chart_effective_expense_amount` so
        automatic `/transaksi` and `/last` charts stay aligned with report
        summaries that use net expense.
    """
    # Collect daily totals before sorting so repeated dates become one point.
    daily_totals: dict[str, float] = {}
    # Process each transaction row from the displayed list.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        # Ignore non-expense rows because this chart answers spending over time.
        if txn_type != "expense":
            continue
        date_label = str((txn or {}).get("date", "") or "Tanpa tanggal").strip() or "Tanpa tanggal"
        # Add net expense for the date so split bill receivables do not inflate the chart.
        daily_totals[date_label] = daily_totals.get(date_label, 0.0) + get_chart_effective_expense_amount(txn)

    # Return points sorted chronologically by the ISO-like date label.
    return [(date_label, daily_totals[date_label]) for date_label in sorted(daily_totals)]


# Define build transaction timeseries png bytes for callers in this flow.
def build_transaction_timeseries_png_bytes(transactions: list[dict], title: str = "Time Series Transaksi") -> bytes:
    """Build a PNG time-series chart from displayed transaction rows.

    Args:
        transactions: Transaction dictionaries that were already selected for
            a user-facing list such as `/transaksi` or `/last`.
        title: Human-readable chart title shown at the top of the figure.

    Returns:
        PNG image bytes containing a date-based net expense time series.

    Side effects:
        Imports matplotlib lazily and renders one in-memory figure.

    Flow constraints:
        This helper is read-only and must represent exactly the passed rows, so
        filtered transaction lists produce filtered charts.
    """
    # Build the exact series that should match the transaction list output.
    points = transaction_net_expense_series(transactions)
    # Show a clean placeholder instead of failing when the list has no expenses.
    if not points or max(value for _date_label, value in points) <= 0:
        return build_empty_chart_png_bytes(title, "Belum ada pengeluaran net pada transaksi yang ditampilkan.")

    # Prepare matplotlib only after confirming that a real chart is needed.
    plt = _load_matplotlib_pyplot()
    # Apply the shared finance chart style before creating axes.
    _configure_matplotlib_style(plt)
    # Create a wide figure that remains readable in Telegram preview.
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    # Split labels and values so matplotlib can plot them directly.
    labels = [date_label for date_label, _value in points]
    values = [value for _date_label, value in points]
    # Use numeric x positions so long dates can be rotated safely.
    x_positions = list(range(1, len(points) + 1))

    # Draw the time series with markers so sparse transaction days remain visible.
    ax.plot(x_positions, values, color=CHART_COLORS[0], linewidth=2.4, marker="o", markersize=4.0)
    # Add a subtle fill to make the spending trend easier to read on mobile.
    ax.fill_between(x_positions, values, color=CHART_COLORS[0], alpha=0.08)
    ax.set_title(title, loc="left", fontsize=15, weight="semibold", pad=14)
    ax.text(
        0,
        1.01,
        "Basis: pengeluaran net dari transaksi yang ditampilkan",
        fontsize=9,
        color=CHART_MUTED,
        transform=ax.transAxes,
    )
    ax.set_xlabel("Tanggal transaksi")
    ax.set_ylabel("Pengeluaran net")
    ax.yaxis.set_major_formatter(_format_axis_rupiah)
    ax.grid(axis="y", color=CHART_GRID, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(bottom=0)
    ax.set_xticks(x_positions)
    # Rotate date labels to prevent overlap on longer `/last` outputs.
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.text(
        0,
        -0.26,
        f"Total net: {compact_rupiah(sum(values))}",
        fontsize=10,
        color=CHART_MUTED,
        transform=ax.transAxes,
    )
    fig.tight_layout()
    # Return PNG bytes and close the figure to avoid accumulating resources.
    return _finalize_figure_to_png_bytes(fig, plt)


# Define write transaction timeseries png for callers in this flow.
def write_transaction_timeseries_png(transactions: list[dict], title: str = "Time Series Transaksi") -> str:
    """Write a transaction-list time series chart PNG to a temporary file.

    Args:
        transactions: Transaction dictionaries that were shown to the user.
        title: Human-readable chart title used inside the PNG.

    Returns:
        Absolute path to the generated `.png` file. The caller must delete it
        after sending it to Telegram.

    Side effects:
        Creates one temporary PNG file on local disk. It does not write to
        Google Sheets or mutate finance records.

    Flow constraints:
        This file output exists only for Telegram document sending in read-only
        list commands such as `/transaksi` and `/last`.
    """
    # Render the chart into bytes before opening a temporary file.
    png_bytes = build_transaction_timeseries_png_bytes(transactions, title)
    # Create a temporary PNG path that Telegram can read as a document.
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix="-transactions-timeseries.png",
        prefix="finance-chart-",
        delete=False,
    )
    # Use a managed file handle so the file is flushed and closed before sending.
    with handle:
        handle.write(png_bytes)
    # Return the absolute path so callers can send and clean up the file.
    return str(Path(handle.name).resolve())


# Define category net expense items for callers in this flow.
def category_net_expense_items(report: dict, limit: int = 8) -> list[tuple[str, float, float]]:
    """Return category totals sorted by net expense.

    Args:
        report: Monthly report dict containing `by_category` for net totals and
            optional `by_category_gross` for gross comparison labels.
        limit: Maximum number of category rows to return.

    Returns:
        List of `(category, net_amount, gross_amount)` tuples sorted descending
        by `net_amount`.

    Side effects:
        None.

    Flow constraints:
        Sorting must use net expense so `/bulanan` and `/grafik` do not mix net
        and gross ranking behavior.
    """
    by_category = (report or {}).get("by_category") or {}
    by_category_gross = (report or {}).get("by_category_gross") or {}
    # Open a multi-line structure for the values below.
    rows = [
        # Run this statement as part of the current workflow.
        (str(category), float(net or 0), float(by_category_gross.get(category, net) or 0))
        # Process each category, net in the current collection.
        for category, net in by_category.items()
        # Handle the case where float(net or 0) > 0.
        if float(net or 0) > 0
    # Close the structure that was opened above.
    ]
    # Return sorted(rows, key=lambda row: row[1], reverse=True)[:limit] to the caller.
    return sorted(rows, key=lambda row: row[1], reverse=True)[:limit]


# Define load matplotlib pyplot for callers in this flow.
def _load_matplotlib_pyplot():
    """Load matplotlib with the non-interactive PNG backend.

    Args:
        None.

    Returns:
        Imported `matplotlib.pyplot` module configured to use the `Agg`
        backend.

    Side effects:
        Imports matplotlib and sets its backend before importing pyplot.

    Flow constraints:
        This helper is lazy so importing bot modules does not require a display
        server and does not initialize plotting unless a chart is requested.
    """
    # Import matplotlib for this module's local operations.
    import matplotlib

    # The Telegram bot runs headless, so force a file-rendering backend.
    matplotlib.use("Agg")
    # Import matplotlib so this module can use its helpers.
    from matplotlib import pyplot as plt

    # Return plt to the caller.
    return plt


# Define configure matplotlib style for callers in this flow.
def _configure_matplotlib_style(plt) -> None:
    """Apply the shared visual style for finance chart figures.

    Args:
        plt: Imported `matplotlib.pyplot` module.

    Returns:
        None.

    Side effects:
        Updates matplotlib runtime style parameters for charts generated in the
        current process.

    Flow constraints:
        The font stack intentionally uses common professional sans-serif fonts
        and avoids decorative fonts so chart output stays readable in Telegram.
    """
    # Open a multi-line structure for the values below.
    plt.rcParams.update(
        # Open a multi-line structure for the values below.
        {
            "font.family": "sans-serif",
            "font.sans-serif": CHART_FONT_FAMILY,
            "axes.edgecolor": CHART_GRID,
            "axes.labelcolor": CHART_MUTED,
            "axes.titlecolor": CHART_TEXT,
            "xtick.color": CHART_MUTED,
            "ytick.color": CHART_MUTED,
            "text.color": CHART_TEXT,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        # Close the structure that was opened above.
        }
    # Close the structure that was opened above.
    )


# Define format axis rupiah for callers in this flow.
def _format_axis_rupiah(value: float, _position: int | None = None) -> str:
    """Format matplotlib axis tick values as compact rupiah labels.

    Args:
        value: Numeric tick value supplied by matplotlib.
        _position: Optional tick index supplied by matplotlib and ignored by
            this formatter.

    Returns:
        Compact rupiah string suitable for y-axis ticks.

    Side effects:
        None.

    Flow constraints:
        This formatter only affects chart display; it must not alter report
        calculations.
    """
    # Return compact_rupiah(float(value or 0)) to the caller.
    return compact_rupiah(float(value or 0))


# Define finalize figure to png bytes for callers in this flow.
def _finalize_figure_to_png_bytes(fig, plt) -> bytes:
    """Serialize a matplotlib figure into PNG bytes and close it.

    Args:
        fig: Matplotlib figure object to serialize.
        plt: Imported `matplotlib.pyplot` module used to close the figure.

    Returns:
        PNG image bytes ready to send as a Telegram document or write to disk.

    Side effects:
        Renders the figure into memory and closes the matplotlib figure to avoid
        accumulating open figures in the bot process.

    Flow constraints:
        The function writes only to an in-memory buffer; file output is handled
        separately by `write_monthly_chart_png`.
    """
    # Prepare buffer for the next step.
    buffer = BytesIO()
    # Run this statement as part of the current workflow.
    fig.tight_layout(pad=1.2)
    fig.savefig(buffer, format="png", dpi=CHART_DPI, bbox_inches="tight", facecolor="white")
    # Run this statement as part of the current workflow.
    plt.close(fig)
    # Return buffer.getvalue() to the caller.
    return buffer.getvalue()


# Define truncate label for callers in this flow.
def truncate_label(value: str, max_chars: int) -> str:
    """Shorten chart labels while keeping category names recognizable.

    Args:
        value: Raw label text, usually a category name.
        max_chars: Maximum label length before adding an ellipsis.

    Returns:
        Original label when it fits, otherwise a shortened label ending in
        `...`.

    Side effects:
        None.

    Flow constraints:
        This only changes chart display text. It must not change category names
        stored in reports or Google Sheets.
    """
    text = str(value or "-").strip() or "-"
    # Handle the case where len(text) <= max_chars.
    if len(text) <= max_chars:
        # Return text to the caller.
        return text
    return text[: max(1, max_chars - 3)].rstrip() + "..."


# Define build empty chart png bytes for callers in this flow.
def build_empty_chart_png_bytes(title: str, message: str) -> bytes:
    """Build a PNG placeholder when a chart has no plottable data.

    Args:
        title: Chart title shown at the top of the placeholder.
        message: User-facing empty-state message.

    Returns:
        PNG bytes generated by matplotlib.

    Side effects:
        Imports matplotlib lazily and renders a figure in memory.

    Flow constraints:
        This function is read-only and must not write Google Sheets data or
        create transactions.
    """
    # Prepare plt for the next step.
    plt = _load_matplotlib_pyplot()
    # Run this statement as part of the current workflow.
    _configure_matplotlib_style(plt)
    # Run this statement as part of the current workflow.
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)

    # Keep empty-state charts clean and readable inside Telegram preview.
    ax.axis("off")
    ax.text(0.02, 0.88, title, fontsize=17, weight="semibold", transform=ax.transAxes)
    # Run this statement as part of the current workflow.
    ax.text(0.02, 0.76, message, fontsize=11, color=CHART_MUTED, transform=ax.transAxes)
    # Return _finalize_figure_to_png_bytes(fig, plt) to the caller.
    return _finalize_figure_to_png_bytes(fig, plt)


# Define build monthly timeseries png bytes for callers in this flow.
def build_monthly_timeseries_png_bytes(report: dict) -> bytes:
    """Build a monthly PNG line chart of daily net expense.

    Args:
        report: Monthly report dict from `get_monthly_report`.

    Returns:
        PNG bytes containing a daily time-series chart.

    Side effects:
        Imports matplotlib lazily and renders a figure in memory.

    Flow constraints:
        Values are net expenses, not gross expenses, so this chart must remain
        consistent with `/bulanan` net-expense totals.
    """
    month_label = (report or {}).get("month", "-")
    # Prepare values for the next step.
    values = daily_net_expense_series(report)
    title = f"Time Series Pengeluaran Net - {month_label}"
    # Handle the case where max(values or [0]) <= 0.
    if max(values or [0]) <= 0:
        return build_empty_chart_png_bytes(title, "Belum ada pengeluaran net untuk periode ini.")

    # Prepare plt for the next step.
    plt = _load_matplotlib_pyplot()
    # Run this statement as part of the current workflow.
    _configure_matplotlib_style(plt)
    # Run this statement as part of the current workflow.
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    # Prepare days for the next step.
    days = list(range(1, len(values) + 1))

    # Draw both a line and a subtle fill so the trend is visible on mobile.
    ax.plot(days, values, color=CHART_COLORS[0], linewidth=2.4, marker="o", markersize=3.6)
    # Run this statement as part of the current workflow.
    ax.fill_between(days, values, color=CHART_COLORS[0], alpha=0.08)
    ax.set_title(title, loc="left", fontsize=15, weight="semibold", pad=14)
    # Open a multi-line structure for the values below.
    ax.text(
        # Include this value in the surrounding collection or call.
        0,
        # Include this value in the surrounding collection or call.
        1.01,
        "Basis: pengeluaran net setelah piutang split bill/talangan",
        # Prepare fontsize for the next step.
        fontsize=9,
        # Prepare color for the next step.
        color=CHART_MUTED,
        # Prepare transform for the next step.
        transform=ax.transAxes,
    # Close the structure that was opened above.
    )
    ax.set_xlabel("Tanggal")
    ax.set_ylabel("Pengeluaran net")
    # Run this statement as part of the current workflow.
    ax.yaxis.set_major_formatter(_format_axis_rupiah)
    ax.grid(axis="y", color=CHART_GRID, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    # Run this statement as part of the current workflow.
    ax.set_xlim(1, max(days))
    # Run this statement as part of the current workflow.
    ax.set_ylim(bottom=0)
    # Open a multi-line structure for the values below.
    ax.text(
        # Include this value in the surrounding collection or call.
        0,
        # Include this value in the surrounding collection or call.
        -0.18,
        f"Total net: {compact_rupiah(sum(values))}",
        # Prepare fontsize for the next step.
        fontsize=9,
        # Prepare color for the next step.
        color=CHART_MUTED,
        # Prepare transform for the next step.
        transform=ax.transAxes,
    # Close the structure that was opened above.
    )
    # Return _finalize_figure_to_png_bytes(fig, plt) to the caller.
    return _finalize_figure_to_png_bytes(fig, plt)


# Define build monthly bar png bytes for callers in this flow.
def build_monthly_bar_png_bytes(report: dict) -> bytes:
    """Build a monthly PNG horizontal bar chart by net expense category.

    Args:
        report: Monthly report dict containing net category totals and optional
            gross category totals.

    Returns:
        PNG bytes containing category bars sorted by net expense.

    Side effects:
        Imports matplotlib lazily and renders a figure in memory.

    Flow constraints:
        Category order is based on net expense. Gross values are shown only as
        context in labels when they differ from net values.
    """
    month_label = (report or {}).get("month", "-")
    # Prepare rows for the next step.
    rows = category_net_expense_items(report, limit=8)
    title = f"Bar Chart Pengeluaran Net - {month_label}"
    # Handle the missing or empty rows case.
    if not rows:
        return build_empty_chart_png_bytes(title, "Belum ada kategori pengeluaran net untuk periode ini.")

    # Prepare plt for the next step.
    plt = _load_matplotlib_pyplot()
    # Run this statement as part of the current workflow.
    _configure_matplotlib_style(plt)
    # Run this statement as part of the current workflow.
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    # Prepare categories for the next step.
    categories = [truncate_label(row[0], 28) for row in rows]
    # Prepare net values for the next step.
    net_values = [row[1] for row in rows]
    # Prepare colors for the next step.
    colors = [CHART_COLORS[index % len(CHART_COLORS)] for index, _row in enumerate(rows)]

    # Reverse for horizontal bar display so the largest item appears at the top.
    bar_positions = list(range(len(rows)))
    # Run this statement as part of the current workflow.
    ax.barh(bar_positions, list(reversed(net_values)), color=list(reversed(colors)), height=0.58)
    # Run this statement as part of the current workflow.
    ax.set_yticks(bar_positions, list(reversed(categories)))
    ax.set_title(title, loc="left", fontsize=15, weight="semibold", pad=14)
    # Open a multi-line structure for the values below.
    ax.text(
        # Include this value in the surrounding collection or call.
        0,
        # Include this value in the surrounding collection or call.
        1.01,
        "Basis: kategori diurutkan berdasarkan pengeluaran net",
        # Prepare fontsize for the next step.
        fontsize=9,
        # Prepare color for the next step.
        color=CHART_MUTED,
        # Prepare transform for the next step.
        transform=ax.transAxes,
    # Close the structure that was opened above.
    )
    # Run this statement as part of the current workflow.
    ax.xaxis.set_major_formatter(_format_axis_rupiah)
    ax.grid(axis="x", color=CHART_GRID, linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    # Process each position, row in the current collection.
    for position, row in zip(bar_positions, reversed(rows)):
        # Prepare net for the next step.
        net = row[1]
        # Prepare gross for the next step.
        gross = row[2]
        # Prepare amount for the next step.
        amount = compact_rupiah(net)
        # Handle the case where abs(net - gross) > 0.0001.
        if abs(net - gross) > 0.0001:
            amount = f"{amount} ({compact_rupiah(gross)})"
        ax.text(net, position, f"  {amount}", va="center", fontsize=9, color=CHART_TEXT)

    # Run this statement as part of the current workflow.
    ax.set_xlim(right=max(net_values) * 1.18)
    # Return _finalize_figure_to_png_bytes(fig, plt) to the caller.
    return _finalize_figure_to_png_bytes(fig, plt)


# Define build monthly pie png bytes for callers in this flow.
def build_monthly_pie_png_bytes(report: dict) -> bytes:
    """Build a monthly PNG donut chart by net expense category.

    Args:
        report: Monthly report dict containing net category totals.

    Returns:
        PNG bytes showing each category share from total net expense.

    Side effects:
        Imports matplotlib lazily and renders a figure in memory.

    Flow constraints:
        Shares are calculated from net expense totals only. The chart is
        read-only and must not modify category or transaction data.
    """
    month_label = (report or {}).get("month", "-")
    # Prepare rows for the next step.
    rows = category_net_expense_items(report, limit=7)
    title = f"Pie Chart Kategori Net - {month_label}"
    # Prepare total for the next step.
    total = sum(row[1] for row in rows)
    # Handle the case where total <= 0.
    if total <= 0:
        return build_empty_chart_png_bytes(title, "Belum ada kategori pengeluaran net untuk periode ini.")

    # Prepare plt for the next step.
    plt = _load_matplotlib_pyplot()
    # Run this statement as part of the current workflow.
    _configure_matplotlib_style(plt)
    # Run this statement as part of the current workflow.
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    # Prepare labels for the next step.
    labels = [truncate_label(row[0], 24) for row in rows]
    # Prepare values for the next step.
    values = [row[1] for row in rows]
    # Prepare colors for the next step.
    colors = [CHART_COLORS[index % len(CHART_COLORS)] for index, _row in enumerate(rows)]

    # Donut layout keeps the total visible without crowding category labels.
    wedges, _texts, autotexts = ax.pie(
        # Include this value in the surrounding collection or call.
        values,
        # Prepare labels for the next step.
        labels=None,
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 4 else "",
        # Prepare colors for the next step.
        colors=colors,
        # Prepare startangle for the next step.
        startangle=90,
        # Prepare counterclock for the next step.
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 1.4},
        textprops={"fontsize": 8.5, "color": CHART_TEXT},
    # Close the structure that was opened above.
    )
    # Process each autotext in the current collection.
    for autotext in autotexts:
        autotext.set_weight("semibold")
    ax.text(0, 0.04, compact_rupiah(total), ha="center", va="center", fontsize=15, weight="semibold")
    ax.text(0, -0.12, "total net", ha="center", va="center", fontsize=9, color=CHART_MUTED)
    ax.set_title(title, loc="left", fontsize=15, weight="semibold", pad=14)
    # Open a multi-line structure for the values below.
    ax.text(
        # Include this value in the surrounding collection or call.
        -1.18,
        # Include this value in the surrounding collection or call.
        1.1,
        "Basis: share kategori dari total pengeluaran net",
        # Prepare fontsize for the next step.
        fontsize=9,
        # Prepare color for the next step.
        color=CHART_MUTED,
    # Close the structure that was opened above.
    )
    legend_labels = [f"{label} - {compact_rupiah(value)}" for label, value in zip(labels, values)]
    # Open a multi-line structure for the values below.
    ax.legend(
        # Include this value in the surrounding collection or call.
        wedges,
        # Include this value in the surrounding collection or call.
        legend_labels,
        loc="center left",
        # Prepare bbox to anchor for the next step.
        bbox_to_anchor=(1.0, 0.5),
        # Prepare frameon for the next step.
        frameon=False,
        # Prepare fontsize for the next step.
        fontsize=9,
    # Close the structure that was opened above.
    )
    # Return _finalize_figure_to_png_bytes(fig, plt) to the caller.
    return _finalize_figure_to_png_bytes(fig, plt)


def build_monthly_chart_png_bytes(report: dict, chart_type: str = "timeseries") -> bytes:
    """Build a monthly chart PNG for the requested chart type.

    Args:
        report: Monthly report dict from `get_monthly_report`.
        chart_type: Chart selector string. Supported values are `timeseries`,
            `line`, `bar`, `barchart`, `pengeluaran`, `pie`, `piechart`, and
            `kategori`.

    Returns:
        Complete PNG file bytes for the requested chart. Unknown chart types
        fall back to the time-series chart.

    Side effects:
        Imports matplotlib lazily through the selected chart builder.

    Flow constraints:
        This function is read-only and must never write transactions, balances,
        debt data, or category data.
    """
    normalized = str(chart_type or "timeseries").strip().lower()
    if normalized in {"bar", "barchart", "pengeluaran"}:
        # Return build_monthly_bar_png_bytes(report) to the caller.
        return build_monthly_bar_png_bytes(report)
    if normalized in {"pie", "piechart", "kategori"}:
        # Return build_monthly_pie_png_bytes(report) to the caller.
        return build_monthly_pie_png_bytes(report)
    # Return build_monthly_timeseries_png_bytes(report) to the caller.
    return build_monthly_timeseries_png_bytes(report)


def write_monthly_chart_png(report: dict, chart_type: str = "timeseries") -> str:
    """Write a monthly chart PNG to a temporary file.

    Args:
        report: Monthly report dict from `get_monthly_report`.
        chart_type: Chart selector string accepted by
            `build_monthly_chart_png_bytes`.

    Returns:
        Absolute path to the generated `.png` file. The caller is responsible
        for deleting the temporary file after sending it.

    Side effects:
        Creates one temporary `.png` file on local disk. It does not write to
        Google Sheets or mutate bot state.

    Flow constraints:
        File output exists only to satisfy Telegram document sending. All report
        calculations must already be complete before this function is called.
    """
    month_label = str((report or {}).get("month") or "month").replace("/", "-")
    normalized = str(chart_type or "timeseries").strip().lower()
    # Prepare png bytes for the next step.
    png_bytes = build_monthly_chart_png_bytes(report, normalized)
    # Open a multi-line structure for the values below.
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=f"-{month_label}-{normalized}.png",
        prefix="finance-chart-",
        # Prepare delete for the next step.
        delete=False,
    # Close the structure that was opened above.
    )
    # Use a managed resource so it is closed after this operation.
    with handle:
        # Run this statement as part of the current workflow.
        handle.write(png_bytes)
    # Return str(Path(handle.name).resolve()) to the caller.
    return str(Path(handle.name).resolve())
