"""Generate the Finance Bot help manual PDF from docs/help_manual.md."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT_DIR / "docs" / "help_manual.md"
OUTPUT_PATH = ROOT_DIR / "docs" / "help_manual.pdf"


def _format_markdown_line(line: str) -> tuple[str, int, str]:
    """Convert one Markdown line into plain text plus lightweight style hints.

    Args:
        line: One raw line from `docs/help_manual.md`.

    Returns:
        Tuple of `(text, font_size, font_weight)` for rendering with matplotlib.

    Side effects:
        None.

    Flow constraints:
        Keep the generator dependency-light and stable. This function does not
        implement full Markdown; it only formats headings and bullets needed by
        the user-facing manual.
    """
    clean = line.rstrip()
    if clean.startswith("# "):
        return clean[2:].strip(), 18, "bold"
    if clean.startswith("## "):
        return clean[3:].strip(), 14, "bold"
    if clean.startswith("### "):
        return clean[4:].strip(), 12, "bold"
    if clean.startswith("- "):
        return f"• {clean[2:].strip()}", 9, "normal"
    return clean, 9, "normal"


def _iter_render_lines(markdown_text: str) -> list[tuple[str, int, str]]:
    """Prepare wrapped lines for PDF rendering.

    Args:
        markdown_text: Full Markdown document text.

    Returns:
        List of `(text, font_size, font_weight)` tuples. Long text is wrapped to
        fit a portrait PDF page.

    Side effects:
        None.

    Flow constraints:
        Preserve command examples literally enough to remain readable in the PDF.
    """
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

    return output_path


if __name__ == "__main__":
    generated_path = generate_pdf()
    print(f"Generated {generated_path}")
