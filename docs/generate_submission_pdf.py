#!/usr/bin/env python3
"""Render docs/INKSHIELD-Round2-Submission.md to a polished PDF.

Single source of truth: the Markdown file next to this script. The PDF
cover page is built from the constants below (same facts as the Markdown
intro block); the document body starts at the first "## " heading.

Supported Markdown subset (deliberately small):
  ## section / ### subsection / - bullet / N. ordered item / > quote /
  --- rule / ``` code fence / pipe tables / **bold** / `code` / autolinks

Usage:  python docs/generate_submission_pdf.py
Requires: reportlab
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)

# --- Cover metadata (verified 2026-10-29 against the repository) -----------
TITLE = "INKSHIELD"
SUBTITLE = "Evidence-first brand governance - verify before you publish."
DOC_LABEL = "ROUND 2 SUBMISSION"
BASELINE = "22a05ef on main (verified 2026-10-29)"
FRONTEND_URL = "https://inkshield-rho.vercel.app"
API_URL = "https://inkshield-api.onrender.com"
REPO_URL = "https://github.com/Akash-Selvaraj-R/INKSHIELD"
SOURCE_MD = "docs/INKSHIELD-Round2-Submission.md"
SUMMARY = (
    "INKSHIELD checks draft content against approved brand knowledge, returns "
    "findings that always cite the knowledge record behind them, and records "
    "every scan and human decision in an audit trail."
)

INK = colors.HexColor("#111111")
PAPER = colors.HexColor("#f5f1e8")
YELLOW = colors.HexColor("#ffd400")
DEEP_YELLOW = colors.HexColor("#e6b800")
GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#cccccc")

PAGE_W, PAGE_H = A4
MARGIN_X = 20 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 20 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

# Characters reportlab's standard fonts cannot draw, mapped to safe ASCII.
_SANITIZE = str.maketrans({"\u2192": "->", "\u2190": "<-", "\u2191": "^", "\u2193": "v", "\u2713": "[ok]"})


def sanitize(text: str) -> str:
    return text.translate(_SANITIZE)


def escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Convert the supported inline Markdown to reportlab Paragraph markup."""
    spans: list[str] = []

    def keep_code(match: re.Match[str]) -> str:
        spans.append(f'<font face="Courier">{escape_xml(match.group(1))}</font>')
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)            # 1. code spans out
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)        # 2. autolink brackets
    text = escape_xml(text)                                  # 3. XML-escape rest
    text = re.sub(                                           # 4. bare URLs
        r"(https?://[^\s]+)",
        r'<link href="\1" color="#1a4f8b">\1</link>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)    # 5. bold
    text = re.sub(r"(?<![\w])\*([^*\s][^*]*)\*", r"<i>\1</i>", text)  # 6. italic
    for idx, code in enumerate(spans):                       # 7. restore code
        text = text.replace(f"\x00{idx}\x00", code)
    return sanitize(text)


# --- Styles -----------------------------------------------------------------
BODY = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=9.8, leading=14.2,
    textColor=INK, alignment=TA_LEFT, spaceAfter=7,
)
H1 = ParagraphStyle(
    "H1", fontName="Helvetica-Bold", fontSize=17, leading=21,
    textColor=INK, spaceBefore=20, spaceAfter=3, keepWithNext=True,
)
H2 = ParagraphStyle(
    "H2", fontName="Helvetica-Bold", fontSize=12, leading=15.5,
    textColor=INK, spaceBefore=13, spaceAfter=4, keepWithNext=True,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=15, bulletIndent=3, spaceAfter=4,
    bulletFontName="Helvetica-Bold", bulletFontSize=9.5,
)
ORDERED = ParagraphStyle(
    "Ordered", parent=BODY, leftIndent=18, bulletIndent=2, spaceAfter=5,
    bulletFontName="Helvetica-Bold", bulletFontSize=9.5,
)
QUOTE = ParagraphStyle(
    "Quote", fontName="Helvetica-BoldOblique", fontSize=11, leading=16,
    textColor=INK, spaceAfter=4,
)
CELL = ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.4, leading=11.4, textColor=INK)
CELL_HEAD = ParagraphStyle(
    "CellHead", fontName="Helvetica-Bold", fontSize=8.4, leading=11.4, textColor=colors.white,
)
CODE_STYLE = ParagraphStyle(
    "Code", fontName="Courier", fontSize=8.0, leading=10.6, textColor=INK,
)


def wrap_code(line: str, max_chars: int = 95) -> str:
    """Greedy-wrap an over-long code line so it never leaves the page."""
    if len(line) <= max_chars:
        return line
    indent = " " * (len(line) - len(line.lstrip()))
    words, out, cur = line.split(), [], indent
    for word in words:
        if cur.strip() and len(cur) + 1 + len(word) > max_chars:
            out.append(cur)
            cur = indent + word
        else:
            cur = word if not cur.strip() else f"{cur} {word}"
    if cur.strip():
        out.append(cur)
    return "\n".join(out)


def code_block(lines: list[str]) -> KeepTogether:
    text = sanitize("\n".join(wrap_code(line) for line in lines))
    block = XPreformatted(escape_xml(text), CODE_STYLE)
    table = Table([[block]], colWidths=[CONTENT_W])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("BOX", (0, 0), (-1, -1), 0.6, LIGHT_GRAY),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 4), table, Spacer(1, 8)])


def make_table(rows: list[list[str]]) -> Table:
    n_cols = max(len(row) for row in rows)
    rows = [row + [""] * (n_cols - len(row)) for row in rows]

    # Column widths proportional to content length; a floor keeps short
    # columns (e.g. "Method", "PATCH") from wrapping mid-word.
    weights = []
    for col in range(n_cols):
        longest = max(len(inline(c)) for c in (row[col] for row in rows))
        weights.append(min(max(longest, 12), 60))
    total = sum(weights)
    widths = [CONTENT_W * w / total for w in weights]

    data = []
    for r, row in enumerate(rows):
        style = CELL_HEAD if r == 0 else CELL
        data.append([Paragraph(inline(cell) or "&nbsp;", style) for cell in row])

    table = Table(data, colWidths=widths, repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.9, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for r in range(2, len(rows), 2):
        table_style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#faf7f0")))
    table.setStyle(TableStyle(table_style))
    return table


def quote_box(text: str) -> Table:
    para = Paragraph(inline(text), QUOTE)
    box = Table([[para]], colWidths=[CONTENT_W])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("LINEBEFORE", (0, 0), (0, -1), 4, YELLOW),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return KeepTogether([Spacer(1, 3), box, Spacer(1, 8)])


_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_ORDERED = re.compile(r"^(\d+)\.\s+(.*)$")
_FENCE = re.compile(r"^```")


def is_special(line: str) -> bool:
    s = line.strip()
    return (
        not s
        or bool(_FENCE.match(s))
        or s.startswith("|")
        or bool(_HEADING.match(s))
        or s.startswith("- ")
        or bool(_ORDERED.match(s))
        or s.startswith("> ")
        or s == "---"
    )


def parse_markdown(text: str) -> list:
    """Parse the supported subset into reportlab flowables."""
    lines = text.splitlines()
    story: list = []
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        if _FENCE.match(s):
            i += 1
            block: list[str] = []
            while i < len(lines) and not _FENCE.match(lines[i].strip()):
                block.append(lines[i].rstrip())
                i += 1
            i += 1  # closing fence
            story.append(code_block(block))
            continue

        if s.startswith("|"):
            block_rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block_rows.append(lines[i].strip())
                i += 1
            rows = [
                [c.strip() for c in row.strip("|").split("|")]
                for row in block_rows
            ]
            if len(rows) > 1 and all(
                re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in rows[1]
            ):
                del rows[1]
            story.append(Spacer(1, 4))
            story.append(make_table(rows))
            story.append(Spacer(1, 10))
            continue

        heading = _HEADING.match(s)
        if heading:
            level, content = len(heading.group(1)), heading.group(2)
            if level == 1:
                story.append(Paragraph(inline(content), H1))
                story.append(HRFlowable(width="100%", thickness=2.5, color=DEEP_YELLOW,
                                        spaceBefore=4, spaceAfter=10))
            else:
                style = H1 if level == 2 else H2
                story.append(Paragraph(inline(content), style))
                if level == 2:
                    story.append(HRFlowable(width="100%", thickness=1.6, color=DEEP_YELLOW,
                                            spaceBefore=3, spaceAfter=9))
            i += 1
            continue

        if s.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            story.append(quote_box(" ".join(quote_lines)))
            continue

        if s.startswith("- "):
            item = [s[2:]]
            i += 1
            while i < len(lines) and lines[i].strip() and not is_special(lines[i]):
                item.append(lines[i].strip())
                i += 1
            story.append(Paragraph(inline(" ".join(item)), BULLET, bulletText="\u2022"))
            continue

        ordered = _ORDERED.match(s)
        if ordered:
            item = [ordered.group(2)]
            i += 1
            while i < len(lines) and lines[i].strip() and not is_special(lines[i]):
                item.append(lines[i].strip())
                i += 1
            story.append(Paragraph(inline(" ".join(item)), ORDERED,
                                   bulletText=f"{ordered.group(1)}."))
            continue

        if s == "---":
            story.append(Spacer(1, 6))
            i += 1
            continue

        paragraph = [s]
        i += 1
        while i < len(lines) and not is_special(lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(" ".join(paragraph)), BODY))

    return story


# --- Page furniture ---------------------------------------------------------
class NumberedCanvas(pdfcanvas.Canvas):
    """Two-pass canvas so every page can show 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict] = []

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_states)
        for index, state in enumerate(self._saved_states):
            self.__dict__.update(state)
            if index > 0:  # cover page (index 0) stays clean
                self._draw_furniture(index + 1, total)
            super().showPage()
        super().save()

    def _draw_furniture(self, page: int, total: int) -> None:
        self.saveState()
        # Header
        self.setStrokeColor(INK)
        self.setLineWidth(1.2)
        self.line(MARGIN_X, PAGE_H - MARGIN_TOP + 6, PAGE_W - MARGIN_X, PAGE_H - MARGIN_TOP + 6)
        self.setFillColor(YELLOW)
        self.rect(MARGIN_X, PAGE_H - MARGIN_TOP + 6, 60, 2.6, stroke=0, fill=1)
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(GRAY)
        self.drawString(MARGIN_X, PAGE_H - MARGIN_TOP + 12, "INKSHIELD  /  ROUND 2 SUBMISSION")
        self.drawRightString(PAGE_W - MARGIN_X, PAGE_H - MARGIN_TOP + 12,
                             "EVIDENCE-FIRST BRAND GOVERNANCE")
        # Footer
        self.setStrokeColor(LIGHT_GRAY)
        self.setLineWidth(0.6)
        self.line(MARGIN_X, MARGIN_BOTTOM - 8, PAGE_W - MARGIN_X, MARGIN_BOTTOM - 8)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRAY)
        self.drawString(MARGIN_X, MARGIN_BOTTOM - 18, SOURCE_MD)
        self.drawRightString(PAGE_W - MARGIN_X, MARGIN_BOTTOM - 18,
                             f"Page {page} of {total}")
        self.restoreState()


def draw_cover(cnv: pdfcanvas.Canvas, _doc) -> None:
    # Header block
    block_h = 330
    cnv.setFillColor(INK)
    cnv.rect(0, PAGE_H - block_h, PAGE_W, block_h, stroke=0, fill=1)
    cnv.setFillColor(YELLOW)
    cnv.rect(0, PAGE_H - block_h - 7, PAGE_W, 7, stroke=0, fill=1)

    x = MARGIN_X
    cnv.setFillColor(YELLOW)
    cnv.setFont("Helvetica-Bold", 11)
    label = f"{DOC_LABEL}   /   BASELINE {BASELINE.split()[0]}"
    cnv.drawString(x, PAGE_H - 62, label)

    # Title: INK (yellow) + SHIELD (white)
    cnv.setFont("Helvetica-Bold", 62)
    ink_w = cnv.stringWidth("INK", "Helvetica-Bold", 62)
    cnv.setFillColor(YELLOW)
    cnv.drawString(x, PAGE_H - 130, "INK")
    cnv.setFillColor(colors.white)
    cnv.drawString(x + ink_w, PAGE_H - 130, "SHIELD")

    cnv.setFillColor(colors.white)
    cnv.setFont("Helvetica", 15)
    cnv.drawString(x, PAGE_H - 162, SUBTITLE)

    cnv.setFillColor(YELLOW)
    cnv.setFont("Courier-Bold", 10)
    cnv.drawString(x, PAGE_H - 196, "CHECK  /  FIND EVIDENCE  /  EXPLAIN  /  APPROVE")

    cnv.setFillColor(colors.HexColor("#bbbbbb"))
    cnv.setFont("Helvetica", 10)
    cnv.drawString(x, PAGE_H - 230, "A pre-publication governance step between draft and publish:")
    cnv.drawString(x, PAGE_H - 246, "deterministic scanning, evidence-backed findings, human decisions, audit trail.")

    cnv.setFont("Helvetica-Bold", 9)
    cnv.setFillColor(colors.white)
    cnv.drawString(x, PAGE_H - 300, "NEXT.JS 16 + FASTAPI  /  VERCEL + RENDER  /  48 FRONTEND + 52 BACKEND TESTS PASSING")

    # Summary paragraph
    summary = Paragraph(f"<b>What it is.</b> {SUMMARY}", BODY)
    _, h = summary.wrap(PAGE_W - 2 * MARGIN_X, 200)
    summary.drawOn(cnv, x, PAGE_H - block_h - 34 - h)

    # Metadata rows
    rows = [
        ("LIVE FRONTEND", FRONTEND_URL),
        ("LIVE API", API_URL),
        ("REPOSITORY", REPO_URL),
        ("BASELINE", BASELINE),
        ("SOURCE OF THIS PDF", SOURCE_MD),
    ]
    y = PAGE_H - block_h - 64 - h
    for key, value in rows:
        cnv.setFont("Helvetica-Bold", 8)
        cnv.setFillColor(GRAY)
        cnv.drawString(x, y, key)
        cnv.setFont("Helvetica", 11)
        cnv.setFillColor(INK)
        cnv.drawString(x + 130, y, value)
        cnv.setStrokeColor(LIGHT_GRAY)
        cnv.setLineWidth(0.5)
        cnv.line(x, y - 7, PAGE_W - MARGIN_X, y - 7)
        y -= 30

    # Contents
    contents = [
        "Problem and target users",
        "Solution and end-to-end workflow",
        "Architecture and technology choices",
        "Completed features and testing evidence",
        "Progress and changes since Round 1",
        "Known limitations",
        "Three concrete Round 3 improvements",
        "How to verify this submission",
    ]
    y -= 26
    cnv.setFont("Helvetica-Bold", 8)
    cnv.setFillColor(GRAY)
    cnv.drawString(x, y, "IN THIS DOCUMENT")
    y -= 20
    for number, entry in enumerate(contents, start=1):
        cnv.setFont("Helvetica-Bold", 10)
        cnv.setFillColor(DEEP_YELLOW)
        cnv.drawString(x, y, f"{number:02d}")
        cnv.setFont("Helvetica", 10.5)
        cnv.setFillColor(INK)
        cnv.drawString(x + 26, y, entry)
        y -= 19

    # Footer
    cnv.setStrokeColor(INK)
    cnv.setLineWidth(1)
    cnv.line(x, 58, PAGE_W - MARGIN_X, 58)
    cnv.setFont("Helvetica", 8)
    cnv.setFillColor(GRAY)
    cnv.drawString(x, 44, "Generated from " + SOURCE_MD)
    cnv.drawRightString(PAGE_W - MARGIN_X, 44,
                        "Regenerate: python docs/generate_submission_pdf.py")


def main() -> int:
    docs_dir = Path(__file__).resolve().parent
    md_path = docs_dir / "INKSHIELD-Round2-Submission.md"
    pdf_path = docs_dir / "INKSHIELD-Round2-Submission.pdf"

    if not md_path.exists():
        print(f"error: missing {md_path}", file=sys.stderr)
        return 1

    text = md_path.read_text(encoding="utf-8")

    # The cover carries the document title/metadata; the body starts at the
    # first level-2 heading.
    body_start = text.find("\n## ")
    body = text[body_start:] if body_start != -1 else text

    story = parse_markdown(body)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="INKSHIELD - Round 2 Submission",
        author="INKSHIELD",
        subject="Submission and architecture overview (Round 2)",
    )
    full_story = [Spacer(1, 1), PageBreak()] + story
    doc.build(full_story, onFirstPage=draw_cover, canvasmaker=NumberedCanvas)

    size_kb = pdf_path.stat().st_size // 1024
    print(f"wrote {pdf_path} ({size_kb} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
