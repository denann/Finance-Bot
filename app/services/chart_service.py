"""Chart generation for monthly finance reports without external plotting dependencies."""


from __future__ import annotations

from calendar import monthrange
from math import atan2, pi
from pathlib import Path
import struct
import tempfile
import zlib

from app.services.report_service import get_effective_expense_amount, safe_float


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


PNG_WIDTH = 980
PNG_HEIGHT = 520
PNG_BACKGROUND = (255, 255, 255)
PNG_TEXT = (17, 24, 39)
PNG_MUTED = (107, 114, 128)
PNG_GRID = (229, 231, 235)
PNG_AXIS = (31, 41, 55)
PNG_COLORS = [
    (37, 99, 235),
    (220, 38, 38),
    (22, 163, 74),
    (245, 158, 11),
    (124, 58, 237),
    (8, 145, 178),
    (219, 39, 119),
    (75, 85, 99),
]


# Minimal 5x7 bitmap font for chart labels. This keeps PNG output dependency-free.
FONT_5X7 = {
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    "!": ["010", "010", "010", "010", "010", "000", "010"],
    "?": ["11110", "00001", "00001", "00110", "00100", "00000", "00100"],
    ".": ["000", "000", "000", "000", "000", "000", "010"],
    ",": ["000", "000", "000", "000", "000", "010", "100"],
    ":": ["000", "010", "000", "000", "010", "000", "000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
    "%": ["11001", "11010", "00100", "01000", "10110", "00110", "00000"],
    "(": ["001", "010", "100", "100", "100", "010", "001"],
    ")": ["100", "010", "001", "001", "001", "010", "100"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "11100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


class PngCanvas:
    """Tiny RGB canvas used to draw finance charts into PNG bytes.

    Args:
        width: Pixel width of the output image.
        height: Pixel height of the output image.
        background: RGB tuple used to initialize every pixel.

    Methods accept integer coordinates in image pixels. Drawing outside the
    canvas is clipped, so chart generation can keep simple coordinate math.
    """

    def __init__(self, width: int = PNG_WIDTH, height: int = PNG_HEIGHT, background: tuple[int, int, int] = PNG_BACKGROUND):
        self.width = int(width)
        self.height = int(height)
        self.pixels = bytearray(background * (self.width * self.height))

    def set_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        """Set one pixel when the coordinate is inside the canvas."""
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        offset = (int(y) * self.width + int(x)) * 3
        self.pixels[offset:offset + 3] = bytes(color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        """Draw a filled rectangle clipped to the image boundary."""
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.width, int(x + width))
        y1 = min(self.height, int(y + height))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            offset = (yy * self.width + x0) * 3
            self.pixels[offset:offset + len(row)] = row

    def draw_line(self, x0: float, y0: float, x1: float, y1: float, color: tuple[int, int, int], *, width: int = 1) -> None:
        """Draw a line with Bresenham-style integer stepping."""
        x0_i, y0_i, x1_i, y1_i = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1_i - x0_i)
        sx = 1 if x0_i < x1_i else -1
        dy = -abs(y1_i - y0_i)
        sy = 1 if y0_i < y1_i else -1
        err = dx + dy
        radius = max(0, int(width) // 2)
        while True:
            for yy in range(y0_i - radius, y0_i + radius + 1):
                for xx in range(x0_i - radius, x0_i + radius + 1):
                    self.set_pixel(xx, yy, color)
            if x0_i == x1_i and y0_i == y1_i:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0_i += sx
            if e2 <= dx:
                err += dx
                y0_i += sy

    def fill_circle(self, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        """Draw a filled circle for points or pie center labels."""
        r2 = int(radius) * int(radius)
        for y in range(int(cy) - int(radius), int(cy) + int(radius) + 1):
            for x in range(int(cx) - int(radius), int(cx) + int(radius) + 1):
                if (x - int(cx)) ** 2 + (y - int(cy)) ** 2 <= r2:
                    self.set_pixel(x, y, color)

    def draw_text(self, x: float, y: float, text: str, *, scale: int = 2, color: tuple[int, int, int] = PNG_TEXT, anchor: str = "start") -> None:
        """Draw uppercase bitmap text with optional start/middle/end anchoring."""
        clean = str(text or "").upper()
        scale = max(1, int(scale or 1))
        width = text_pixel_width(clean, scale=scale)
        x_pos = int(round(x))
        if anchor == "middle":
            x_pos -= width // 2
        elif anchor == "end":
            x_pos -= width
        for char in clean:
            glyph = FONT_5X7.get(char, FONT_5X7["?"])
            glyph_w = max(len(row) for row in glyph)
            for row_index, row in enumerate(glyph):
                for col_index, bit in enumerate(row):
                    if bit != "1":
                        continue
                    self.fill_rect(
                        x_pos + col_index * scale,
                        int(round(y)) + row_index * scale,
                        scale,
                        scale,
                        color,
                    )
            x_pos += (glyph_w + 1) * scale

    def to_png_bytes(self) -> bytes:
        """Encode the canvas as PNG bytes using the standard PNG scanline format."""
        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)
            start = y * stride
            raw.extend(self.pixels[start:start + stride])
        return b"".join([
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)),
            png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            png_chunk(b"IEND", b""),
        ])


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build one PNG chunk with CRC.

    Args:
        chunk_type: Four-byte PNG chunk name, for example `b"IHDR"`.
        data: Raw chunk payload bytes.

    Returns:
        Serialized PNG chunk bytes.
    """
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def text_pixel_width(text: str, *, scale: int = 2) -> int:
    """Return bitmap text width in pixels for the built-in chart font."""
    total = 0
    for char in str(text or "").upper():
        glyph = FONT_5X7.get(char, FONT_5X7["?"])
        total += (max(len(row) for row in glyph) + 1) * int(scale or 1)
    return max(0, total - int(scale or 1))


def truncate_label(value: str, max_chars: int) -> str:
    """Shorten chart labels without breaking chart layout."""
    text = str(value or "-").strip() or "-"
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 3)].rstrip() + "..."


def draw_chart_header(canvas: PngCanvas, title: str, subtitle: str = "") -> None:
    """Draw a consistent chart title and subtitle."""
    canvas.draw_text(40, 38, title, scale=3, color=PNG_TEXT)
    if subtitle:
        canvas.draw_text(40, 72, subtitle, scale=2, color=PNG_MUTED)


def build_empty_chart_png_bytes(title: str, message: str) -> bytes:
    """Build a PNG chart placeholder when no plottable data exists.

    Args:
        title: Chart title shown at the top of the PNG.
        message: Empty-state text shown below the title.

    Returns:
        Complete PNG file bytes.
    """
    canvas = PngCanvas()
    draw_chart_header(canvas, title)
    canvas.draw_text(40, 100, message, scale=2, color=PNG_MUTED)
    return canvas.to_png_bytes()


def build_monthly_timeseries_png_bytes(report: dict) -> bytes:
    """Build a monthly PNG line chart of daily net expense.

    Args:
        report: Monthly report dict from `get_monthly_report`.

    Returns:
        PNG bytes showing daily net expense across the month.
    """
    month_label = (report or {}).get("month", "-")
    values = daily_net_expense_series(report)
    max_value = max(values or [0])
    title = f"Time Series Pengeluaran Net - {month_label}"
    if max_value <= 0:
        return build_empty_chart_png_bytes(title, "Belum ada pengeluaran net untuk periode ini.")

    canvas = PngCanvas()
    left, right, top, bottom = 80, 40, 96, 76
    plot_w = PNG_WIDTH - left - right
    plot_h = PNG_HEIGHT - top - bottom
    max_axis = max_value * 1.15

    def x_pos(index: int) -> float:
        """Map day index to x coordinate."""
        if len(values) <= 1:
            return float(left)
        return left + (index / (len(values) - 1)) * plot_w

    def y_pos(value: float) -> float:
        """Map rupiah amount to y coordinate."""
        return top + plot_h - (float(value or 0) / max_axis) * plot_h

    draw_chart_header(canvas, title, "Basis: pengeluaran net setelah piutang split bill/talangan")
    for step in range(5):
        value = max_axis * step / 4
        y = y_pos(value)
        canvas.draw_line(left, y, PNG_WIDTH - right, y, PNG_GRID)
        canvas.draw_text(left - 12, y - 7, compact_rupiah(value), scale=1, color=PNG_MUTED, anchor="end")

    canvas.draw_line(left, PNG_HEIGHT - bottom, PNG_WIDTH - right, PNG_HEIGHT - bottom, PNG_AXIS, width=2)
    canvas.draw_line(left, top, left, PNG_HEIGHT - bottom, PNG_AXIS, width=2)

    last_point = None
    for index, value in enumerate(values):
        point = (x_pos(index), y_pos(value))
        if last_point is not None:
            canvas.draw_line(last_point[0], last_point[1], point[0], point[1], PNG_COLORS[0], width=3)
        if value > 0:
            canvas.fill_circle(int(round(point[0])), int(round(point[1])), 4, PNG_COLORS[0])
        last_point = point

    days = len(values)
    for day in sorted({1, 7, 14, 21, 28, days}):
        if 1 <= day <= days:
            x = x_pos(day - 1)
            canvas.draw_line(x, PNG_HEIGHT - bottom, x, PNG_HEIGHT - bottom + 5, PNG_MUTED)
            canvas.draw_text(x, PNG_HEIGHT - bottom + 14, str(day), scale=1, color=PNG_MUTED, anchor="middle")

    canvas.draw_text(PNG_WIDTH / 2, PNG_HEIGHT - 30, "Tanggal", scale=2, color=PNG_MUTED, anchor="middle")
    canvas.draw_text(40, PNG_HEIGHT - 30, f"Total net: {compact_rupiah(sum(values))}", scale=2, color=PNG_MUTED)
    return canvas.to_png_bytes()


def build_monthly_bar_png_bytes(report: dict) -> bytes:
    """Build a monthly PNG bar chart by net expense category.

    Args:
        report: Monthly report dict with `by_category` and `by_category_gross`.

    Returns:
        PNG bytes. Bars are sorted by net expense, with gross shown in
        parentheses when it differs from net.
    """
    month_label = (report or {}).get("month", "-")
    rows = category_net_expense_items(report, limit=8)
    title = f"Bar Chart Pengeluaran Net - {month_label}"
    if not rows:
        return build_empty_chart_png_bytes(title, "Belum ada kategori pengeluaran net untuk periode ini.")

    canvas = PngCanvas()
    draw_chart_header(canvas, title, "Basis: kategori diurutkan berdasarkan pengeluaran net")

    left, right, top = 250, 70, 108
    bar_h, gap = 28, 19
    chart_w = PNG_WIDTH - left - right
    max_value = max(row[1] for row in rows)
    for index, (category, net, gross) in enumerate(rows):
        y = top + index * (bar_h + gap)
        color = PNG_COLORS[index % len(PNG_COLORS)]
        bar_w = int(round((net / max_value) * chart_w)) if max_value else 0
        amount = compact_rupiah(net)
        if abs(net - gross) > 0.0001:
            amount = f"{amount} ({compact_rupiah(gross)})"
        canvas.draw_text(left - 14, y + 7, truncate_label(category, 24), scale=2, color=PNG_TEXT, anchor="end")
        canvas.fill_rect(left, y, max(1, bar_w), bar_h, color)
        canvas.draw_text(left + bar_w + 10, y + 7, amount, scale=2, color=PNG_TEXT)

    return canvas.to_png_bytes()


def build_monthly_pie_png_bytes(report: dict) -> bytes:
    """Build a monthly PNG pie chart by net expense category.

    Args:
        report: Monthly report dict with net category totals.

    Returns:
        PNG bytes showing category share from total net expense.
    """
    month_label = (report or {}).get("month", "-")
    rows = category_net_expense_items(report, limit=7)
    title = f"Pie Chart Kategori Net - {month_label}"
    total = sum(row[1] for row in rows)
    if total <= 0:
        return build_empty_chart_png_bytes(title, "Belum ada kategori pengeluaran net untuk periode ini.")

    canvas = PngCanvas()
    draw_chart_header(canvas, title, "Basis: share kategori dari total pengeluaran net")
    cx, cy, radius = 300, 290, 155
    cumulative = []
    cursor = -pi / 2
    for row in rows:
        angle = (row[1] / total) * 2 * pi
        cumulative.append(cursor + angle)
        cursor += angle

    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy > radius * radius:
                continue
            angle = atan2(dy, dx)
            while angle < -pi / 2:
                angle += 2 * pi
            segment_index = 0
            for idx, end_angle in enumerate(cumulative):
                if angle <= end_angle:
                    segment_index = idx
                    break
            canvas.set_pixel(x, y, PNG_COLORS[segment_index % len(PNG_COLORS)])

    canvas.fill_circle(cx, cy, 62, PNG_BACKGROUND)
    canvas.draw_text(cx, cy - 10, compact_rupiah(total), scale=3, color=PNG_TEXT, anchor="middle")
    canvas.draw_text(cx, cy + 22, "total net", scale=2, color=PNG_MUTED, anchor="middle")

    for index, (category, net, _) in enumerate(rows):
        legend_y = 145 + index * 40
        color = PNG_COLORS[index % len(PNG_COLORS)]
        pct = (net / total) * 100 if total else 0
        canvas.fill_rect(560, legend_y - 14, 18, 18, color)
        canvas.draw_text(
            590,
            legend_y - 11,
            f"{truncate_label(category, 24)} - {compact_rupiah(net)} ({pct:.1f}%)",
            scale=2,
            color=PNG_TEXT,
        )

    return canvas.to_png_bytes()


def build_monthly_chart_png_bytes(report: dict, chart_type: str = "timeseries") -> bytes:
    """Build a monthly chart PNG for the requested chart type.

    Args:
        report: Monthly report dict from `get_monthly_report`.
        chart_type: One of `timeseries`, `bar`, or `pie`.

    Returns:
        Complete PNG file bytes.
    """
    normalized = str(chart_type or "timeseries").strip().lower()
    if normalized in {"bar", "barchart", "pengeluaran"}:
        return build_monthly_bar_png_bytes(report)
    if normalized in {"pie", "piechart", "kategori"}:
        return build_monthly_pie_png_bytes(report)
    return build_monthly_timeseries_png_bytes(report)


def write_monthly_chart_png(report: dict, chart_type: str = "timeseries") -> str:
    """Write a monthly PNG chart to a temporary file.

    Args:
        report: Monthly report dict from `get_monthly_report`.
        chart_type: One of `timeseries`, `bar`, or `pie`.

    Returns:
        Absolute path to the generated `.png` file. Caller owns cleanup.
    """
    month_label = str((report or {}).get("month") or "month").replace("/", "-")
    normalized = str(chart_type or "timeseries").strip().lower()
    png_bytes = build_monthly_chart_png_bytes(report, normalized)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=f"-{month_label}-{normalized}.png",
        prefix="finance-chart-",
        delete=False,
    )
    with handle:
        handle.write(png_bytes)
    return str(Path(handle.name).resolve())
