"""
Order export to Word (.docx).

Converts the rendered order HTML — headings, paragraphs, lists, tables, bold/italic —
into a DOCX the Commission's staff can edit in Word.
"""

from html.parser import HTMLParser
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

_HEADINGS = {"h1": 0, "h2": 1, "h3": 2, "h4": 3, "h5": 4, "h6": 4}
_SKIP = {"style", "script", "head", "title"}


class _OrderHTML(HTMLParser):
    def __init__(self, doc: Document):
        super().__init__(convert_charrefs=True)
        self.doc = doc
        self.para = None
        self.bold = self.italic = 0
        self.skip = 0
        self.table_rows = None  # list of rows (list of cell strings) while inside <table>
        self.row = None
        self.cell = None
        self.list_style = None

    # ── structure ─────────────────────────────────────────────────────
    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag == "table":
            self.table_rows = []
        elif tag == "tr" and self.table_rows is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif self.table_rows is not None:
            return
        elif tag in _HEADINGS:
            self.para = self.doc.add_heading("", level=_HEADINGS[tag])
        elif tag == "p" or (tag == "div" and self.para is None):
            self.para = self.doc.add_paragraph()
            if dict(attrs).get("align") == "center" or "center" in (dict(attrs).get("class") or ""):
                self.para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif tag in ("ul", "ol"):
            self.list_style = "List Number" if tag == "ol" else "List Bullet"
        elif tag == "li":
            self.para = self.doc.add_paragraph(style=self.list_style or "List Bullet")
        elif tag == "br" and self.para is not None:
            self.para.add_run().add_break()
        elif tag in ("b", "strong"):
            self.bold += 1
        elif tag in ("i", "em"):
            self.italic += 1

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.table_rows.append(self.row)
            self.row = None
        elif tag == "table" and self.table_rows is not None:
            self._emit_table(self.table_rows)
            self.table_rows = None
        elif self.table_rows is not None:
            return
        elif tag in _HEADINGS or tag in ("p", "li", "div"):
            self.para = None
        elif tag in ("ul", "ol"):
            self.list_style = None
        elif tag in ("b", "strong"):
            self.bold = max(0, self.bold - 1)
        elif tag in ("i", "em"):
            self.italic = max(0, self.italic - 1)

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
            return
        if self.table_rows is not None or not data.strip():
            return
        if self.para is None:
            self.para = self.doc.add_paragraph()
        run = self.para.add_run(" ".join(data.split()) + (" " if data.endswith(" ") else ""))
        run.bold = bool(self.bold)
        run.italic = bool(self.italic)

    # ── tables ────────────────────────────────────────────────────────
    def _emit_table(self, rows):
        width = max(len(r) for r in rows) if rows else 0
        if not width:
            return
        table = self.doc.add_table(rows=len(rows), cols=width)
        table.style = "Table Grid"
        for i, r in enumerate(rows):
            for j in range(width):
                table.cell(i, j).text = r[j] if j < len(r) else ""
        for cell in table.rows[0].cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
        self.para = None


def html_to_docx(html: str) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    _OrderHTML(doc).feed(html)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
