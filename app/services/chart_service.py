"""SVG chart generation for monthly finance reports without external plotting dependencies."""


from __future__ import annotations

from calendar import monthrange
from html import escape
from math import cos, pi, sin
from pathlib import Path
import tempfile

from app.services.report_service import get_effective_expense_amount, safe_float


CHART_COLORS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#f59e0b",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#4b5563",
]


def compact_rupiah(amount: float) -> str:
    """Format a rupiah amount compactly for chart labels.

    Args:
        amount: Numeric rupiah value.

    Returns:
        Short label such as `500k`, `1.2jt`, or `0`.
    """
    value = float(amount or 0)
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.1f}jt".replace(".0jt", "jt")
    if abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.0f}k"
    return f"{sign}{abs_value:.0f}"


def transaction_day(txn: dict) -> int | None:
    """Extract the day number from a transaction date.

    Args:
        txn: Transaction row with a `date` value in `YYYY-MM-DD` format.

    Returns:
        Day of month as an integer, or `None` when the date is invalid.
    """
    raw = str((txn or {}).get("date", "") or "").strip()
    try:
        return int(raw.split("-")[2])
    except Exception:
        return None


def monthly_day_count(month_label: str) -> int:
    """Return the number of days in a `YYYY-MM` month label.

    Args:
        month_label: Month string such as `2026-06`.

    Returns:
        Integer day count for the month. Invalid input falls back to `31` so
        chart generation can still return a safe placeholder or rough series.
    """
    try:
        year, month = [int(x) for x in str(month_label or "").split("-", 1)]
        return monthrange(year, month)[1]
    except Exception:
        return 31


def daily_net_expense_series(report: dict) -> list[float]:
    """Build daily net expense values for a monthly report.

    Args:
        report: Monthly report dict containing enriched `transactions`.

    Returns:
        List of daily net expense totals, one value per day in the month.
    """
    days = monthly_day_count((report or {}).get("month", ""))
    values = [0.0 for _ in range(days)]
    for txn in (report or {}).get("transactions", []) or []:
        if str((txn or {}).get("type", "")).strip().lower() != "expense":
            continue
        day = transaction_day(txn)
        if day is None or day < 1 or day > days:
            continue
        values[day - 1] += get_effective_expense_amount(txn)
    return values


def category_net_expense_items(report: dict, limit: int = 8) -> list[tuple[str, float, float]]:
    """Return category rows as `(category, net, gross)` tuples.

    Args:
        report: Monthly report dict with `by_category` and `by_category_gross`.
        limit: Maximum number of categories to return.

    Returns:
        Sorted category rows using net expense as the sort key.
    """
    by_category = (report or {}).get("by_category") or {}
    by_category_gross = (report or {}).get("by_category_gross") or {}
    rows = [
        (str(category), float(net or 0), float(by_category_gross.get(category, net) or 0))
        for category, net in by_category.items()
        if float(net or 0) > 0
    ]
    return sorted(rows, key=lambda row: row[1], reverse=True)[:limit]


def svg_text(x: float, y: float, text: str, *, size: int = 13, anchor: str = "start", weight: str = "400") -> str:
    """Build an escaped SVG text element.

    Args:
        x: Horizontal coordinate in the SVG viewport.
        y: Vertical coordinate in the SVG viewport.
        text: Label text. It is HTML-escaped before rendering.
        size: Font size in pixels.
        anchor: SVG text anchor, usually `start`, `middle`, or `end`.
        weight: CSS font weight.

    Returns:
        SVG `<text>` element string.
    """
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'font-family="Arial, sans-serif" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="#111827">{escape(str(text))}</text>'
    )


def build_empty_chart_svg(title: str, message: str) -> str:
    """Build an SVG chart placeholder when no plottable data exists.

    Args:
        title: Chart title shown at the top.
        message: Empty-state message shown below the title.

    Returns:
        Complete SVG document string.
    """
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="520" viewBox="0 0 980 520">',
        '<rect width="980" height="520" fill="#ffffff"/>',
        svg_text(40, 56, title, size=24, weight="700"),
        svg_text(40, 100, message, size=16),
        '</svg>',
    ])


def build_monthly_timeseries_svg(report: dict) -> str:
    """Build a monthly line chart of daily net expense.

    Args:
        report: Monthly report dict from `get_monthly_report`.

    Returns:
        SVG string for daily net expense time series.
    """
    month_label = (report or {}).get("month", "-")
    values = daily_net_expense_series(report)
    max_value = max(values or [0])
    title = f"Time Series Pengeluaran Net - {month_label}"
    if max_value <= 0:
        return build_empty_chart_svg(title, "Belum ada pengeluaran net untuk periode ini.")

    width, height = 980, 520
    left, right, top, bottom = 72, 36, 82, 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_axis = max_value * 1.15

    def x_pos(index: int) -> float:
        """Map day index into chart x coordinate."""
        if len(values) <= 1:
            return left
        return left + (index / (len(values) - 1)) * plot_w

    def y_pos(value: float) -> float:
        """Map rupiah value into chart y coordinate."""
        return top + plot_h - (float(value or 0) / max_axis) * plot_h

    grid = []
    for step in range(5):
        value = max_axis * step / 4
        y = y_pos(value)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        grid.append(svg_text(left - 10, y + 4, compact_rupiah(value), size=11, anchor="end"))

    points = " ".join(f"{x_pos(i):.1f},{y_pos(value):.1f}" for i, value in enumerate(values))
    circles = [
        f'<circle cx="{x_pos(i):.1f}" cy="{y_pos(value):.1f}" r="3.2" fill="#2563eb"/>'
        for i, value in enumerate(values)
        if value > 0
    ]

    x_labels = []
    days = len(values)
    for day in sorted({1, 7, 14, 21, 28, days}):
        if 1 <= day <= days:
            x = x_pos(day - 1)
            x_labels.append(f'<line x1="{x:.1f}" y1="{height-bottom}" x2="{x:.1f}" y2="{height-bottom+5}" stroke="#9ca3af"/>')
            x_labels.append(svg_text(x, height - bottom + 24, str(day), size=11, anchor="middle"))

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(40, 48, title, size=24, weight="700"),
        svg_text(40, 74, "Basis: pengeluaran net setelah piutang split bill/talangan", size=13),
        *grid,
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>',
        *x_labels,
        f'<polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="3"/>',
        *circles,
        svg_text(width / 2, height - 20, "Tanggal", size=12, anchor="middle"),
        svg_text(40, height - 20, f"Total net: {compact_rupiah(sum(values))}", size=12),
        '</svg>',
    ])


def build_monthly_bar_svg(report: dict) -> str:
    """Build a monthly horizontal bar chart by net expense category.

    Args:
        report: Monthly report dict with `month`, `by_category`, and optional
            `by_category_gross`.

    Returns:
        Complete SVG document string. Bars are sorted by net expense, with
        gross shown in parentheses when it differs from net.
    """
    month_label = (report or {}).get("month", "-")
    rows = category_net_expense_items(report, limit=8)
    title = f"Bar Chart Pengeluaran Net - {month_label}"
    if not rows:
        return build_empty_chart_svg(title, "Belum ada kategori pengeluaran net untuk periode ini.")

    width, height = 980, 520
    left, right, top = 230, 52, 92
    bar_h, gap = 28, 18
    max_value = max(row[1] for row in rows)
    chart_w = width - left - right
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(40, 48, title, size=24, weight="700"),
        svg_text(40, 74, "Basis: kategori diurutkan berdasarkan pengeluaran net", size=13),
    ]

    for i, (category, net, gross) in enumerate(rows):
        y = top + i * (bar_h + gap)
        bar_w = (net / max_value) * chart_w if max_value else 0
        color = CHART_COLORS[i % len(CHART_COLORS)]
        amount = compact_rupiah(net)
        if abs(net - gross) > 0.0001:
            amount = f"{amount} ({compact_rupiah(gross)})"
        elements.extend([
            svg_text(left - 12, y + 20, category[:24], size=13, anchor="end"),
            f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="4" fill="{color}"/>',
            svg_text(left + bar_w + 8, y + 20, amount, size=12),
        ])

    elements.append('</svg>')
    return "\n".join(elements)


def build_monthly_pie_svg(report: dict) -> str:
    """Build a monthly pie chart by net expense category.

    Args:
        report: Monthly report dict with category totals on a net basis.

    Returns:
        Complete SVG document string showing category share from total net
        expense.
    """
    month_label = (report or {}).get("month", "-")
    rows = category_net_expense_items(report, limit=7)
    title = f"Pie Chart Kategori Net - {month_label}"
    total = sum(row[1] for row in rows)
    if total <= 0:
        return build_empty_chart_svg(title, "Belum ada kategori pengeluaran net untuk periode ini.")

    width, height = 980, 520
    cx, cy, radius = 300, 285, 155
    start_angle = -pi / 2
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(40, 48, title, size=24, weight="700"),
        svg_text(40, 74, "Basis: share kategori dari total pengeluaran net", size=13),
    ]

    for i, (category, net, _) in enumerate(rows):
        angle = (net / total) * 2 * pi
        end_angle = start_angle + angle
        x1, y1 = cx + radius * cos(start_angle), cy + radius * sin(start_angle)
        x2, y2 = cx + radius * cos(end_angle), cy + radius * sin(end_angle)
        large_arc = 1 if angle > pi else 0
        color = CHART_COLORS[i % len(CHART_COLORS)]
        path = (
            f'M {cx:.1f},{cy:.1f} L {x1:.1f},{y1:.1f} '
            f'A {radius},{radius} 0 {large_arc},1 {x2:.1f},{y2:.1f} Z'
        )
        pct = (net / total) * 100 if total else 0
        legend_y = 150 + i * 38
        elements.extend([
            f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="2"/>',
            f'<rect x="560" y="{legend_y - 14}" width="18" height="18" rx="3" fill="{color}"/>',
            svg_text(590, legend_y, f"{category[:28]} - {compact_rupiah(net)} ({pct:.1f}%)", size=13),
        ])
        start_angle = end_angle

    elements.extend([
        svg_text(cx, cy + 5, compact_rupiah(total), size=22, anchor="middle", weight="700"),
        svg_text(cx, cy + 28, "total net", size=12, anchor="middle"),
        '</svg>',
    ])
    return "\n".join(elements)


def build_monthly_chart_svg(report: dict, chart_type: str = "timeseries") -> str:
    """Build a monthly chart SVG for the requested chart type.

    Args:
        report: Monthly report dict from `get_monthly_report`.
        chart_type: One of `timeseries`, `bar`, or `pie`.

    Returns:
        SVG chart as a string.
    """
    normalized = str(chart_type or "timeseries").strip().lower()
    if normalized in {"bar", "barchart", "pengeluaran"}:
        return build_monthly_bar_svg(report)
    if normalized in {"pie", "piechart", "kategori"}:
        return build_monthly_pie_svg(report)
    return build_monthly_timeseries_svg(report)


def write_monthly_chart_svg(report: dict, chart_type: str = "timeseries") -> str:
    """Write a monthly SVG chart to a temporary file.

    Args:
        report: Monthly report dict from `get_monthly_report`.
        chart_type: One of `timeseries`, `bar`, or `pie`.

    Returns:
        Absolute path to the generated `.svg` file. Caller owns cleanup.
    """
    month_label = str((report or {}).get("month") or "month").replace("/", "-")
    normalized = str(chart_type or "timeseries").strip().lower()
    svg = build_monthly_chart_svg(report, normalized)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{month_label}-{normalized}.svg",
        prefix="finance-chart-",
        delete=False,
        encoding="utf-8",
    )
    with handle:
        handle.write(svg)
    return str(Path(handle.name).resolve())
