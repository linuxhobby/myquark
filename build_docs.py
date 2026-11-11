#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the myquark README.md (resource list) into HTML/PDF and DOCX."""
import re
import html as _html

SRC = "/Users/marco.chan/Documents/GitHub/myquark/README.md"
OUT_HTML = "/Users/marco.chan/Documents/GitHub/myquark/README.html"
OUT_PDF = "/Users/marco.chan/Documents/GitHub/myquark/README.pdf"
OUT_DOCX = "/Users/marco.chan/Documents/GitHub/myquark/README.docx"

with open(SRC, encoding="utf-8") as f:
    lines = f.read().split("\n")

# ---------------------------------------------------------------------------
# 1. Parse markdown into blocks
# ---------------------------------------------------------------------------
# block types:
#   ("title", text)
#   ("subtitle", text)   -> first bold line used as subtitle-ish
#   ("p", text)
#   ("ul", [items])
#   ("h2", text)
#   ("table", [header_cells], [row_cells_list])
# ---------------------------------------------------------------------------
LINK_RE = re.compile(r"\[([^\]]+)\]\(<?([^)>]+)>?\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")

blocks = []
i = 0
n = len(lines)
while i < n:
    line = lines[i].rstrip()
    if line == "":
        i += 1
        continue
    if line.startswith("# "):
        blocks.append(("title", line[2:].strip()))
        i += 1
        continue
    if line.startswith("## "):
        blocks.append(("h2", line[3:].strip()))
        i += 1
        continue
    if line.startswith("|"):
        # start of a table
        header = [c.strip() for c in line.strip().strip("|").split("|")]
        i += 1
        # skip separator row
        if i < n and re.match(r"^\s*\|?\s*:?-{2,}.*\|\s*$", lines[i]):
            i += 1
        rows = []
        while i < n and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows.append(cells)
            i += 1
        blocks.append(("table", header, rows))
        continue
    if line.startswith("- "):
        items = []
        while i < n and lines[i].strip().startswith("- "):
            items.append(lines[i].strip()[2:].strip())
            i += 1
        blocks.append(("ul", items))
        continue
    # plain paragraph
    blocks.append(("p", line.strip()))
    i += 1

# ---------------------------------------------------------------------------
# 2. Inline tokeniser (links + bold) -> iterate tokens
# ---------------------------------------------------------------------------
def iter_inline(text):
    """Yield tokens: ('text', s) | ('link', text, url) | ('bold', s).

    Handles three inline forms found in the source:
      - raw HTML anchors  <a href="URL" ...>TEXT</a>  (already present in source)
      - markdown links    [TEXT](URL)
      - bold              **TEXT**
    """
    text = text.replace("`", "")  # drop inline-code backticks
    pos = 0
    combined = re.compile(
        r"<a\s+[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>"
        r"|\[([^\]]+)\]\(<?([^)>]+)>?\)"
        r"|\*\*(.+?)\*\*",
        re.S | re.I,
    )
    for m in combined.finditer(text):
        if m.start() > pos:
            yield ("text", text[pos:m.start()])
        if m.group(1) is not None:          # raw <a> anchor
            yield ("link", m.group(2), m.group(1))
        elif m.group(3) is not None:        # markdown link
            yield ("link", m.group(3), m.group(4))
        else:                               # bold
            yield ("bold", m.group(5))
        pos = m.end()
    if pos < len(text):
        yield ("text", text[pos:])

def inline_html(text):
    out = []
    for kind, *rest in iter_inline(text):
        if kind == "text":
            out.append(_html.escape(rest[0]))
        elif kind == "bold":
            out.append("<strong>" + _html.escape(rest[0]) + "</strong>")
        elif kind == "link":
            t, url = rest
            out.append('<a href="%s">%s</a>' % (_html.escape(url, quote=True), _html.escape(t)))
    return "".join(out)

# ---------------------------------------------------------------------------
# 3. Build HTML
# ---------------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Songti SC","STSong","SimSun",serif; color:#1a1a1a; font-size:10.5pt; line-height:1.5; }
h1 { font-size:22pt; text-align:center; margin:0 0 4mm; font-weight:700; }
h2 { font-size:14pt; margin:8mm 0 2mm; padding:3px 8px; background:#f2efe6; border-left:5px solid #b8860b; font-weight:700; }
.intro { background:#fafafa; border:1px solid #e3e3e3; padding:6px 10px; margin-bottom:4mm; border-radius:4px; }
.intro p { margin:2px 0; }
ul { margin:2px 0 2mm 0; padding-left:18px; }
li { margin:1px 0; }
table { border-collapse:collapse; width:100%; margin:2mm 0 4mm; font-size:9.5pt; }
th, td { border:1px solid #cfcfcf; padding:2px 5px; vertical-align:top; }
th { background:#f7f4ec; font-weight:700; text-align:center; }
td.col-num { text-align:right; white-space:nowrap; color:#666; width:5%; }
td.col-name { width:42%; }
td.col-link { width:53%; }
a { color:#0b57d0; text-decoration:none; }
a:hover { text-decoration:underline; }
tr:nth-child(even) td { background:#fbfbf9; }
"""

html_parts = ["<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>",
              "<title>夸克网盘资源清单</title><style>%s</style></head><body>" % CSS]

in_intro = False
for b in blocks:
    if b[0] == "title":
        html_parts.append("<h1>%s</h1>" % inline_html(b[1]))
    elif b[0] == "h2":
        html_parts.append("</div>" if in_intro else "")
        in_intro = False
        html_parts.append("<h2>%s</h2>" % inline_html(b[1]))
    elif b[0] == "p":
        if not in_intro:
            html_parts.append("<div class='intro'>")
            in_intro = True
        html_parts.append("<p>%s</p>" % inline_html(b[1]))
    elif b[0] == "ul":
        if not in_intro:
            html_parts.append("<div class='intro'>")
            in_intro = True
        items = "".join("<li>%s</li>" % inline_html(it) for it in b[1])
        html_parts.append("<ul>%s</ul>" % items)
    elif b[0] == "table":
        if in_intro:
            html_parts.append("</div>")
            in_intro = False
        header, rows = b[1], b[2]
        thead = "<tr>%s</tr>" % "".join("<th>%s</th>" % inline_html(c) for c in header)
        body_rows = []
        for r in rows:
            tds = []
            for idx, c in enumerate(r):
                cls = "col-num" if idx == 0 else ("col-name" if idx == 1 else "col-link")
                tds.append("<td class='%s'>%s</td>" % (cls, inline_html(c)))
            body_rows.append("<tr>%s</tr>" % "".join(tds))
        html_parts.append("<table><thead>%s</thead><tbody>%s</tbody></table>"
                          % (thead, "".join(body_rows)))
if in_intro:
    html_parts.append("</div>")
html_parts.append("</body></html>")

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))
print("HTML written:", OUT_HTML)

# ---------------------------------------------------------------------------
# 4. Build DOCX
# ---------------------------------------------------------------------------
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

# Base font: 仿宋 (FangSong) for body, per user convention
def set_run_font(run, name="FangSong", size=None, bold=False, color=None):
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)
    run.font.bold = bold
    if size is not None:
        run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color

normal = doc.styles["Normal"]
normal.font.name = "FangSong"
normal.font.size = Pt(10.5)
# set eastAsia for normal style
nrPr = normal.element.get_or_add_rPr()
nrFonts = nrPr.find(qn("w:rFonts"))
if nrFonts is None:
    nrFonts = OxmlElement("w:rFonts")
    nrPr.append(nrFonts)
nrFonts.set(qn("w:eastAsia"), "FangSong")
nrFonts.set(qn("w:ascii"), "FangSong")
nrFonts.set(qn("w:hAnsi"), "FangSong")

def shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)

def add_hyperlink(paragraph, url, text, bold=False, color=RGBColor(0x0b, 0x57, 0xd0)):
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rStyle = OxmlElement("w:rStyle")
    rStyle.set(qn("w:val"), "Hyperlink")
    rPr.append(rStyle)
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:eastAsia"), "FangSong")
    rFonts.set(qn("w:ascii"), "FangSong")
    rFonts.set(qn("w:hAnsi"), "FangSong")
    rPr.append(rFonts)
    if bold:
        b = OxmlElement("w:b"); rPr.append(b)
    colorEl = OxmlElement("w:color")
    colorEl.set(qn("w:val"), "%02X%02X%02X" % (color[0], color[1], color[2]))
    rPr.append(colorEl)
    t = OxmlElement("w:t")
    t.text = text
    run.append(rPr)
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return hyperlink

def append_inline(paragraph, text):
    """Append text/links/bold runs to a paragraph, return list of runs."""
    for kind, *rest in iter_inline(text):
        if kind == "text":
            r = paragraph.add_run(rest[0])
            set_run_font(r, size=9.5)
        elif kind == "bold":
            r = paragraph.add_run(rest[0])
            set_run_font(r, size=9.5, bold=True)
        elif kind == "link":
            add_hyperlink(paragraph, rest[1], rest[0])

in_intro = False
for b in blocks:
    if b[0] == "title":
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(b[1])
        set_run_font(r, name="FangSong", size=20, bold=True)
    elif b[0] == "h2":
        if in_intro:
            in_intro = False
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(b[1])
        set_run_font(r, name="FangSong", size=13, bold=True)
        # bottom border-ish shading via paragraph border would be heavy; keep bold
    elif b[0] == "p":
        if not in_intro:
            in_intro = True
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        append_inline(p, b[1])
    elif b[0] == "ul":
        if not in_intro:
            in_intro = True
        for it in b[1]:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(1)
            append_inline(p, it)
    elif b[0] == "table":
        if in_intro:
            in_intro = False
        header, rows = b[1], b[2]
        table = doc.add_table(rows=1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        # header
        hdr = table.rows[0].cells
        for idx, c in enumerate(header):
            hdr[idx].text = ""
            cp = hdr[idx].paragraphs[0]
            r = cp.add_run(c)
            set_run_font(r, size=9.5, bold=True)
            shade_cell(hdr[idx], "F2EFE6")
        # data
        for ri, r in enumerate(rows):
            cells = table.add_row().cells
            for idx, c in enumerate(r):
                cells[idx].text = ""
                cp = cells[idx].paragraphs[0]
                cp.paragraph_format.space_after = Pt(0)
                cp.paragraph_format.space_before = Pt(0)
                if idx == 0:
                    cp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                append_inline(cp, c)
                if ri % 2 == 1:
                    shade_cell(cells[idx], "FBFBF9")
        # column widths
        widths = [Inches(0.5), Inches(2.7), Inches(3.4)]
        for row in table.rows:
            for idx, c in enumerate(row.cells):
                if idx < len(widths):
                    c.width = widths[idx]

doc.save(OUT_DOCX)
print("DOCX written:", OUT_DOCX)
print("Blocks:", [(b[0], (len(b[2]) if b[0]=='table' else b[1]) if b[0] in ('title','h2','p') else b[0]) for b in blocks][:0] or "")
print("Total tables:", sum(1 for b in blocks if b[0]=='table'))
print("Total rows:", sum(len(b[2]) for b in blocks if b[0]=='table'))
