"""Generate the Finance Bot help manual PDF from docs/help_manual.md."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT_DIR / "docs" / "help_manual.md"
OUTPUT_PATH = ROOT_DIR / "docs" / "help_manual.pdf"
FONT_DIR = ROOT_DIR / "assets" / "fonts"
PAGE_SIZE = (595.44, 841.68)
PAGE_MARGIN_X = 42
PAGE_MARGIN_TOP = 54
PAGE_MARGIN_BOTTOM = 42


def _slugify_heading(text: str) -> str:
    """Convert a Markdown heading into a stable internal PDF anchor.

    Args:
        text: Heading title from `docs/help_manual.md`.

    Returns:
        Lowercase slug matching the anchor style used by Markdown links in the
        manual table of contents.

    Side effects:
        None.

    Flow constraints:
        Keep the slug deterministic so table-of-contents links and PDF outline
        entries continue to point at the same sections after regeneration.
    """
    clean = str(text or "").strip().lower()
    clean = re.sub(r"[^\w\s-]", "", clean, flags=re.UNICODE)
    clean = re.sub(r"\s+", "-", clean)
    clean = re.sub(r"-+", "-", clean)
    return clean.strip("-")


def _parse_toc_link(line: str) -> tuple[str, str] | None:
    """Parse a Markdown table-of-contents link.

    Args:
        line: Raw Markdown line, expected in the shape `- [Title](#anchor)`.

    Returns:
        `(title, anchor)` when the line is a local Markdown link, otherwise
        `None`.

    Side effects:
        None.

    Flow constraints:
        Only local `#anchor` links are converted to internal PDF links.
        External links are not expected in this manual.
    """
    match = re.match(r"^\s*-\s+\[(?P<title>[^\]]+)\]\(#(?P<anchor>[^)]+)\)\s*$", line)
    if not match:
        return None
    return match.group("title").strip(), match.group("anchor").strip()


def _register_fonts() -> tuple[str, str]:
    """Register Poppins fonts for ReportLab when bundled font files exist.

    Args:
        None.

    Returns:
        `(regular_font_name, bold_font_name)` for paragraph styles.

    Side effects:
        Registers local TTF fonts with ReportLab.

    Flow constraints:
        Do not download fonts. Fall back to Helvetica when Poppins is missing so
        manual generation still works offline.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_path = FONT_DIR / "Poppins-Regular.ttf"
    bold_path = FONT_DIR / "Poppins-SemiBold.ttf"

    if regular_path.exists() and bold_path.exists():
        pdfmetrics.registerFont(TTFont("Poppins", str(regular_path)))
        pdfmetrics.registerFont(TTFont("Poppins-SemiBold", str(bold_path)))
        return "Poppins", "Poppins-SemiBold"

    return "Helvetica", "Helvetica-Bold"


def _inline_markdown_to_reportlab(text: str) -> str:
    """Convert small inline Markdown syntax into ReportLab paragraph markup.

    Args:
        text: Inline Markdown text from the manual.

    Returns:
        ReportLab-safe paragraph markup with inline code and bold fragments.

    Side effects:
        None.

    Flow constraints:
        Keep conversion intentionally small. The manual only needs backtick code,
        simple bold text, and escaped plain text.
    """
    parts = re.split(r"(`[^`]+`)", str(text or ""))
    converted: list[str] = []

    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            code = html.escape(part[1:-1])
            converted.append(f'<font name="Courier">{code}</font>')
            continue

        escaped = html.escape(part)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        converted.append(escaped)

    return "".join(converted)


def _build_styles(regular_font: str, bold_font: str):
    """Build ReportLab paragraph styles for the manual.

    Args:
        regular_font: Font name used for normal text.
        bold_font: Font name used for headings and strong labels.

    Returns:
        Dict of paragraph styles keyed by local style name.

    Side effects:
        None.

    Flow constraints:
        Keep all headings bold and preserve a compact manual layout.
    """
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    base = {
        "fontName": regular_font,
        "fontSize": 9.6,
        "leading": 14,
        "textColor": colors.HexColor("#222222"),
        "spaceAfter": 6,
    }

    return {
        "body": ParagraphStyle("body", **base),
        "bullet": ParagraphStyle("bullet", **base, leftIndent=14, firstLineIndent=-9),
        "number": ParagraphStyle("number", **base, leftIndent=16, firstLineIndent=-12),
        "code": ParagraphStyle(
            "code",
            fontName="Courier",
            fontSize=8.8,
            leading=12,
            textColor=colors.HexColor("#111111"),
            leftIndent=12,
            rightIndent=12,
            spaceBefore=3,
            spaceAfter=5,
        ),
        "title": ParagraphStyle(
            "title",
            fontName=bold_font,
            fontSize=20,
            leading=25,
            textColor=colors.HexColor("#111111"),
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName=bold_font,
            fontSize=15,
            leading=20,
            textColor=colors.HexColor("#111111"),
            spaceBefore=10,
            spaceAfter=7,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName=bold_font,
            fontSize=12.2,
            leading=16,
            textColor=colors.HexColor("#111111"),
            spaceBefore=7,
            spaceAfter=5,
        ),
        "toc": ParagraphStyle(
            "toc",
            fontName=bold_font,
            fontSize=9.7,
            leading=15,
            textColor=colors.HexColor("#174EA6"),
            leftIndent=14,
            firstLineIndent=-9,
            spaceAfter=2,
        ),
    }


class ManualDocTemplate:
    """Small wrapper around ReportLab document creation for the manual."""

    def __init__(self, output_path: Path, styles: dict):
        """Prepare the PDF document template.

        Args:
            output_path: Destination PDF path.
            styles: Paragraph styles from `_build_styles`.

        Returns:
            None.

        Side effects:
            None until `build` is called.

        Flow constraints:
            Store heading metadata on flowables so ReportLab can create sidebar
            outline/bookmark entries while the final pages are being rendered.
        """
        from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

        self.output_path = output_path
        self.styles = styles

        frame = Frame(
            PAGE_MARGIN_X,
            PAGE_MARGIN_BOTTOM,
            PAGE_SIZE[0] - (PAGE_MARGIN_X * 2),
            PAGE_SIZE[1] - PAGE_MARGIN_TOP - PAGE_MARGIN_BOTTOM,
            id="main",
            showBoundary=0,
        )

        class _DocTemplate(BaseDocTemplate):
            def afterFlowable(doc_self, flowable):
                anchor = getattr(flowable, "_manual_anchor", None)
                title = getattr(flowable, "_manual_title", None)
                level = int(getattr(flowable, "_manual_level", 0) or 0)
                if not anchor or not title:
                    return
                doc_self.canv.bookmarkPage(anchor)
                doc_self.canv.addOutlineEntry(title, anchor, level=max(level - 1, 0), closed=False)

        self.doc = _DocTemplate(
            str(output_path),
            pagesize=PAGE_SIZE,
            leftMargin=PAGE_MARGIN_X,
            rightMargin=PAGE_MARGIN_X,
            topMargin=PAGE_MARGIN_TOP,
            bottomMargin=PAGE_MARGIN_BOTTOM,
        )
        self.doc.addPageTemplates([PageTemplate(id="manual", frames=[frame], onPage=self._draw_page_chrome)])

    def _draw_page_chrome(self, canvas, doc):
        """Draw fixed header and footer on every page."""
        canvas.saveState()
        canvas.setFont(self.styles["body"].fontName, 7.5)
        canvas.setFillColorRGB(0.40, 0.40, 0.40)
        canvas.drawString(PAGE_MARGIN_X, PAGE_SIZE[1] - 26, "Finance Bot Manual")
        canvas.drawRightString(PAGE_SIZE[0] - PAGE_MARGIN_X, 25, str(doc.page))
        canvas.restoreState()

    def build(self, story: list) -> None:
        """Write the final PDF file.

        Args:
            story: ReportLab flowables created from the Markdown manual.

        Returns:
            None.

        Side effects:
            Writes `self.output_path`.

        Flow constraints:
            Let ReportLab create internal links and outline entries during a
            single build pass.
        """
        self.doc.build(story)


def _heading_paragraph(text: str, level: int, styles: dict):
    """Create a bold heading paragraph with a bookmark anchor."""
    from reportlab.platypus import Paragraph

    anchor = _slugify_heading(text)
    style = styles["title"] if level == 1 else styles["h2"] if level == 2 else styles["h3"]
    paragraph = Paragraph(_inline_markdown_to_reportlab(text), style)
    paragraph._manual_anchor = anchor
    paragraph._manual_title = text
    paragraph._manual_level = level
    return paragraph


def _toc_paragraph(title: str, anchor: str, styles: dict):
    """Create one clickable table-of-contents entry."""
    from reportlab.platypus import Paragraph

    clean_title = _inline_markdown_to_reportlab(title)
    clean_anchor = html.escape(anchor, quote=True)
    return Paragraph(f'- <a href="#{clean_anchor}"><b>{clean_title}</b></a>', styles["toc"])


def _markdown_to_story(markdown_text: str, styles: dict) -> list:
    """Convert Markdown manual content into ReportLab flowables.

    Args:
        markdown_text: Full `docs/help_manual.md` content.
        styles: Paragraph styles from `_build_styles`.

    Returns:
        List of ReportLab flowables ready to build into a PDF.

    Side effects:
        None.

    Flow constraints:
        Preserve user-facing examples and convert table-of-contents Markdown
        links into internal PDF links instead of printing raw `[text](#anchor)`.
    """
    from reportlab.platypus import PageBreak, Paragraph, Spacer

    story: list = []
    in_code_block = False
    in_toc = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            story.append(Paragraph(html.escape(line) or " ", styles["code"]))
            continue

        if not line.strip():
            story.append(Spacer(1, 4))
            continue

        if line.startswith("# "):
            story.append(_heading_paragraph(line[2:].strip(), 1, styles))
            continue

        if line.startswith("## "):
            heading_text = line[3:].strip()
            if in_toc and heading_text != "Daftar Isi":
                # Keep table of contents as a dedicated navigation page.
                story.append(PageBreak())
                in_toc = False
            if heading_text == "Daftar Isi":
                in_toc = True
            story.append(_heading_paragraph(heading_text, 2, styles))
            continue

        if line.startswith("### "):
            story.append(_heading_paragraph(line[4:].strip(), 3, styles))
            continue

        toc_link = _parse_toc_link(line)
        if toc_link:
            title, anchor = toc_link
            story.append(_toc_paragraph(title, anchor, styles))
            continue

        if line.startswith("- "):
            text = _inline_markdown_to_reportlab(line[2:].strip())
            story.append(Paragraph(f"- {text}", styles["bullet"]))
            continue

        if re.match(r"^\d+\. ", line):
            story.append(Paragraph(_inline_markdown_to_reportlab(line), styles["number"]))
            continue

        story.append(Paragraph(_inline_markdown_to_reportlab(line), styles["body"]))

    return story


def generate_pdf(source_path: Path = SOURCE_PATH, output_path: Path = OUTPUT_PATH) -> Path:
    """Generate `help_manual.pdf` from the Markdown manual.

    Args:
        source_path: Markdown source path. The default is `docs/help_manual.md`.
        output_path: PDF output path. The default is `docs/help_manual.pdf`.

    Returns:
        Path to the generated PDF.

    Side effects:
        Reads the Markdown source and writes a PDF file with clickable internal
        table-of-contents links and PDF sidebar outline/bookmarks.

    Flow constraints:
        Do not read Google Sheets, call Telegram, or modify bot runtime data.
        Keep page size fixed so every generated page has consistent resolution.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    regular_font, bold_font = _register_fonts()
    styles = _build_styles(regular_font, bold_font)
    markdown_text = source_path.read_text(encoding="utf-8")
    story = _markdown_to_story(markdown_text, styles)
    ManualDocTemplate(output_path, styles).build(story)
    print(f"Font used: {regular_font}")
    print("PDF internal links and outline written.")
    return output_path


if __name__ == "__main__":
    generated_path = generate_pdf()
    print(f"Generated {generated_path}")
