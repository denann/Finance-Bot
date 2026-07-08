"""Generate the Finance Bot help manual PDF from docs/help_manual.md."""

from __future__ import annotations

<<<<<<< HEAD
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

=======
import re
import textwrap
from pathlib import Path

>>>>>>> codex/jelaskan-proyek-ini

ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT_DIR / "docs" / "help_manual.md"
OUTPUT_PATH = ROOT_DIR / "docs" / "help_manual.pdf"
<<<<<<< HEAD


def _format_markdown_line(line: str) -> tuple[str, int, str]:
=======
FONT_DIR = ROOT_DIR / "assets" / "fonts"
A4_SIZE = (8.27, 11.69)
PAGE_LEFT = 0.08
PAGE_TOP = 0.93
PAGE_BOTTOM = 0.07
LINE_HEIGHTS = {
    18: 0.040,
    15: 0.034,
    13: 0.029,
    10: 0.023,
    9: 0.021,
}


def _format_markdown_line(line: str) -> tuple[str, int, str, int]:
>>>>>>> codex/jelaskan-proyek-ini
    """Convert one Markdown line into plain text plus lightweight style hints.

    Args:
        line: One raw line from `docs/help_manual.md`.

    Returns:
<<<<<<< HEAD
        Tuple of `(text, font_size, font_weight)` for rendering with matplotlib.
=======
        Tuple of `(text, font_size, font_weight, heading_level)`. The
        `heading_level` is `0` for normal text, `1` for `#`, `2` for `##`, and
        `3` for `###`.
>>>>>>> codex/jelaskan-proyek-ini

    Side effects:
        None.

    Flow constraints:
        Keep the generator dependency-light and stable. This function does not
        implement full Markdown; it only formats headings and bullets needed by
        the user-facing manual.
    """
    clean = line.rstrip()
    if clean.startswith("# "):
<<<<<<< HEAD
        return clean[2:].strip(), 18, "bold"
    if clean.startswith("## "):
        return clean[3:].strip(), 14, "bold"
    if clean.startswith("### "):
        return clean[4:].strip(), 12, "bold"
    if clean.startswith("- "):
        return f"• {clean[2:].strip()}", 9, "normal"
    return clean, 9, "normal"


def _iter_render_lines(markdown_text: str) -> list[tuple[str, int, str]]:
=======
        return clean[2:].strip(), 18, "bold", 1
    if clean.startswith("## "):
        return clean[3:].strip(), 15, "bold", 2
    if clean.startswith("### "):
        return clean[4:].strip(), 13, "bold", 3
    if clean.startswith("- "):
        return f"• {clean[2:].strip()}", 9, "normal", 0
    if re.match(r"^\d+\. ", clean):
        return clean, 9, "normal", 0
    return clean, 10, "normal", 0


def _iter_render_lines(markdown_text: str) -> list[tuple[str, int, str, int]]:
>>>>>>> codex/jelaskan-proyek-ini
    """Prepare wrapped lines for PDF rendering.

    Args:
        markdown_text: Full Markdown document text.

    Returns:
<<<<<<< HEAD
        List of `(text, font_size, font_weight)` tuples. Long text is wrapped to
        fit a portrait PDF page.
=======
        List of `(text, font_size, font_weight, heading_level)` tuples. Long
        text is wrapped to fit a portrait PDF page.
>>>>>>> codex/jelaskan-proyek-ini

    Side effects:
        None.

    Flow constraints:
        Preserve command examples literally enough to remain readable in the PDF.
    """
<<<<<<< HEAD
    rendered: list[tuple[str, int, str]] = []
    for raw_line in markdown_text.splitlines():
        text, font_size, weight = _format_markdown_line(raw_line)
        if not text:
            rendered.append(("", font_size, weight))
            continue

        # Wrap normal paragraphs and long command lines inside the page margin.
        width = 86 if font_size <= 9 else 70
        wrapped_lines = textwrap.wrap(text, width=width, replace_whitespace=False) or [text]
        for wrapped in wrapped_lines:
            rendered.append((wrapped, font_size, weight))
    return rendered


=======
    rendered: list[tuple[str, int, str, int]] = []
    for raw_line in markdown_text.splitlines():
        text, font_size, weight, heading_level = _format_markdown_line(raw_line)
        if not text:
            rendered.append(("", font_size, weight, heading_level))
            continue

        # Wrap body lines while keeping headings wider and less fragmented.
        width = 84 if font_size <= 10 else 68
        wrapped_lines = textwrap.wrap(text, width=width, replace_whitespace=False) or [text]
        for index, wrapped in enumerate(wrapped_lines):
            level = heading_level if index == 0 else 0
            rendered.append((wrapped, font_size, weight, level))
    return rendered


def _paginate_lines(
    lines: list[tuple[str, int, str, int]]
) -> tuple[list[list[tuple[str, int, str, int]]], list[tuple[str, int]]]:
    """Split rendered lines into fixed-size PDF pages and outline targets.

    Args:
        lines: Wrapped render lines from `_iter_render_lines`.

    Returns:
        Tuple of `(pages, outline_entries)`. `pages` contains fixed page chunks.
        `outline_entries` contains `(title, zero_based_page_index)` entries for
        Markdown level-1 and level-2 headings.

    Side effects:
        None.

    Flow constraints:
        Keep page breaks deterministic so the PDF page size and outline links
        remain stable between runs.
    """
    pages: list[list[tuple[str, int, str, int]]] = []
    current_page: list[tuple[str, int, str, int]] = []
    outline_entries: list[tuple[str, int]] = []
    y = PAGE_TOP

    for text, font_size, weight, heading_level in lines:
        line_height = LINE_HEIGHTS.get(font_size, 0.023)
        if current_page and y - line_height < PAGE_BOTTOM:
            pages.append(current_page)
            current_page = []
            y = PAGE_TOP

        # Store the heading page after the potential page break is resolved.
        if heading_level in {1, 2} and text:
            outline_entries.append((text, len(pages)))

        current_page.append((text, font_size, weight, heading_level))
        y -= line_height if text else 0.014

    if current_page:
        pages.append(current_page)

    return pages, outline_entries


def _resolve_font_family() -> str:
    """Return the preferred matplotlib font family for the manual.

    Args:
        None.

    Returns:
        `Poppins` when a Poppins font file exists on the machine; otherwise
        `DejaVu Sans`, which ships with matplotlib and keeps the PDF readable.

    Side effects:
        Registers the discovered Poppins font with matplotlib when available.

    Flow constraints:
        Do not download fonts during manual generation. The script must run
        offline in the bot project environment.
    """
    from matplotlib import font_manager

    for font_path in sorted(FONT_DIR.glob("Poppins-*.ttf")):
        font_manager.fontManager.addfont(str(font_path))
        return "Poppins"

    for font_path in font_manager.findSystemFonts():
        if "poppins" in Path(font_path).name.lower():
            font_manager.fontManager.addfont(font_path)
            return "Poppins"
    return "DejaVu Sans"


def _add_pdf_outline(output_path: Path, outline_entries: list[tuple[str, int]]) -> bool:
    """Embed clickable PDF outline/bookmark entries when `pypdf` is available.

    Args:
        output_path: Path to the generated PDF.
        outline_entries: `(title, zero_based_page_index)` entries generated from
            the Markdown headings.

    Returns:
        `True` when outline entries were written, otherwise `False`.

    Side effects:
        Rewrites the generated PDF in place when `pypdf` is installed.

    Flow constraints:
        Treat outline generation as an enhancement. If `pypdf` is missing, keep
        the PDF generation successful and report that the outline was skipped.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return False

    reader = PdfReader(str(output_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # Add one clickable bookmark per manual section.
    for title, page_index in outline_entries:
        safe_page = min(max(page_index, 0), len(writer.pages) - 1)
        writer.add_outline_item(title, safe_page)

    with output_path.open("wb") as output_file:
        writer.write(output_file)
    return True


>>>>>>> codex/jelaskan-proyek-ini
def generate_pdf(source_path: Path = SOURCE_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    """Generate `help_manual.pdf` from the Markdown manual.

    Args:
        source_path: Markdown source path. The default is `docs/help_manual.md`
            relative to the project root.
        output_path: PDF output path. The default is `docs/help_manual.pdf`
            relative to the project root.

    Returns:
        Path to the generated PDF.

    Side effects:
<<<<<<< HEAD
        Reads the Markdown source and writes a PDF file.

    Flow constraints:
        Do not read Google Sheets, call Telegram, or require new dependencies.
    """
    markdown_text = source_path.read_text(encoding="utf-8")
    lines = _iter_render_lines(markdown_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(output_path) as pdf:
        page = None
        y = 0.95

        # Render each prepared line, opening a new page when the margin is full.
        for text, font_size, weight in lines:
            line_height = 0.032 if font_size >= 14 else 0.023
            if page is None or y < 0.07:
                if page is not None:
                    pdf.savefig(page, bbox_inches="tight")
                    plt.close(page)
                page = plt.figure(figsize=(8.27, 11.69))
                y = 0.95
                page.text(0.08, 0.985, "Finance Bot Manual", fontsize=8, color="#666666")

            page.text(
                0.08,
                y,
                text,
                fontsize=font_size,
                fontweight=weight,
                family="DejaVu Sans",
                va="top",
            )
            y -= line_height if text else 0.014

        if page is not None:
            pdf.savefig(page, bbox_inches="tight")
            plt.close(page)

=======
        Reads the Markdown source and writes a PDF file. If `pypdf` is available,
        the function also rewrites the PDF with clickable outline entries.

    Flow constraints:
        Do not read Google Sheets, call Telegram, or modify bot runtime data.
        Keep page size fixed so every generated page has consistent resolution.
    """
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    markdown_text = source_path.read_text(encoding="utf-8")
    lines = _iter_render_lines(markdown_text)
    pages, outline_entries = _paginate_lines(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_family = _resolve_font_family()

    with PdfPages(output_path) as pdf:
        for page_number, page_lines in enumerate(pages, start=1):
            fig = plt.figure(figsize=A4_SIZE)
            fig.patch.set_facecolor("white")
            y = PAGE_TOP

            # Keep a consistent header/footer across every page.
            fig.text(PAGE_LEFT, 0.975, "Finance Bot Manual", fontsize=8, color="#666666", family=font_family)
            fig.text(0.90, 0.035, str(page_number), fontsize=8, color="#666666", family=font_family)

            for text, font_size, weight, _heading_level in page_lines:
                line_height = LINE_HEIGHTS.get(font_size, 0.023)
                color = "#111111" if weight == "bold" else "#222222"
                fig.text(
                    PAGE_LEFT,
                    y,
                    text,
                    fontsize=font_size,
                    fontweight=weight,
                    family=font_family,
                    color=color,
                    va="top",
                )
                y -= line_height if text else 0.014

            pdf.savefig(fig)
            plt.close(fig)

    outline_written = _add_pdf_outline(output_path, outline_entries)
    if not outline_written:
        print("PDF outline skipped: install pypdf to embed clickable bookmarks.")
    print(f"Font used: {font_family}")
>>>>>>> codex/jelaskan-proyek-ini
    return output_path


if __name__ == "__main__":
    generated_path = generate_pdf()
    print(f"Generated {generated_path}")
