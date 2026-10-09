"""Editable Markdown/TXT + reflow PDF (NOT a pixel-exact original PDF clone)."""
import html
import json
import re
from pathlib import Path

from .schema import Page


def _escape_cell(s):
    return (s or "").replace("|", "\\|").replace("\n", "<br>")


def table_md(rows):
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [[_escape_cell(x) for x in row] + [""] * (width - len(row)) for row in rows]
    return "\n".join(["| " + " | ".join(normalized[0]) + " |",
                        "| " + " | ".join(["---"] * width) + " |"] +
                       ["| " + " | ".join(row) + " |" for row in normalized[1:]])


def table_html(rows, spans):
    import html
    span_map={(r,c):(rs,cs) for r,c,rs,cs in spans}
    skip=set()
    result=['<table>']
    for r,row in enumerate(rows):
        result.append('  <tr>')
        for c,cell in enumerate(row):
            if (r,c) in skip:
                continue
            rs,cs=span_map.get((r,c),(1,1))
            rs=max(1,rs);cs=max(1,cs)
            for rr in range(r,r+rs):
                for cc in range(c,c+cs):
                    if (rr,cc)!=(r,c):
                        skip.add((rr,cc))
            tag='th' if r==0 else 'td'
            attributes=(f' rowspan="{rs}"' if rs>1 else '')+(f' colspan="{cs}"' if cs>1 else '')
            result.append(f'    <{tag}{attributes}>{html.escape(cell or "")}</{tag}>')
        result.append('  </tr>')
    result.append('</table>')
    return '\n'.join(result)


def block_md(block, mode="zh", use_translated=True):
    text = (block.translation if (use_translated and block.translation) else block.text)
    if block.kind == "image":
        suffix = (f" <!-- vector-source: {block.vector_svg} -->" if block.vector_svg else "")
        return f"![PDF figure]({block.image})" + suffix
    if block.kind == "table":
        rows = block.rows
        if use_translated and block.translation:
            try:
                rows = json.loads(block.translation)
            except json.JSONDecodeError:
                pass
        if block.spans:
            return table_html(rows, block.spans)
        return table_md(rows)
    if block.kind == "markdown":
        return text.strip()
    if block.kind in {"title", "heading"}:
        return "#" * min(6, max(1, block.level)) + " " + text
    if block.kind == "list":
        return text if re.match(r"^\s*(?:[-*•]|\d+[.)])", text) else "- " + text
    if block.kind == "quote":
        return "> " + text
    if block.kind == "equation":
        if block.latex:
            return "$$\n" + block.latex + "\n$$"
        # If LaTeX is already present, do not attempt an unsafe conversion.
        if text.lstrip().startswith("$$"):
            return text
        if re.search(r"\\(?:frac|sqrt|sum|int|begin)\b", text):
            return "$$\n" + text + "\n$$"
        return text  # A PDF glyph expression is NOT necessarily valid LaTeX.
    if block.kind == "footnote":
        m = re.match(r"^([*†\d]+)[\s.)]+(.+)", text)
        return f"[^{m.group(1)}]: {m.group(2)}" if m else text
    return text


def render_markdown(pages, mode="zh", engine="ollama"):
    out = []
    if engine == "none":
        out += ["<!-- UNTRANSLATED: --engine none keeps the original language. -->"]
    for page in pages:
        out.append(f"<!-- source-page: {page.number} -->")
        for block in page.blocks:
            chinese = block_md(block, use_translated=True)
            original = block_md(block, use_translated=False)
            out.append(chinese)
            if mode == "bilingual" and chinese != original and block.kind not in {"image", "equation"}:
                # blockquote avoids editor-dependent HTML wrappers; every block stays editable.
                source_lines = original.splitlines()
                if block.kind in {"table", "markdown"}:
                    out += ["**Original / 原文：**", original]
                else:
                    out.append("\n".join("> " + s for s in source_lines))
    return "\n\n".join(x for x in out if x.strip()) + "\n"


def render_txt(pages, mode="zh"):
    sections = []
    for page in pages:
        for b in page.blocks:
            if b.kind == "image":
                continue
            if b.kind == "table":
                translated = b.rows
                if b.translation:
                    try:
                        translated = json.loads(b.translation)
                    except json.JSONDecodeError:
                        pass
                sections.append("\n".join("\t".join(row) for row in translated))
                if mode == "bilingual" and translated != b.rows:
                    sections.append("\n".join("\t".join(row) for row in b.rows))
                continue
            src = b.text
            txt = b.translation or src
            sections.append(txt)
            if mode == "bilingual" and txt != src:
                sections.append(src)
    return "\n\n".join(s for s in sections if s.strip()) + "\n"


def _find_cjk_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from pathlib import Path
    common = [
        Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simsun.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    ]
    for path in common:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("PaperCJK", str(path), subfontIndex=0))
                return "PaperCJK"
            except Exception:
                pass
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def render_pdf(pages, path, mode="zh", assets_root=None):
    """Reflowed CJK-capable reading copy; formula strings are not TeX typeset."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
                                    KeepTogether, PageBreak, HRFlowable)
    font = _find_cjk_font()
    styles = {"p": ParagraphStyle("p", fontName=font, fontSize=10, leading=16, spaceAfter=7,
                                   wordWrap="CJK", alignment=TA_LEFT)}
    for n in range(1, 7):
        styles[f"h{n}"] = ParagraphStyle(f"h{n}", parent=styles["p"],
             fontName=font, fontSize=max(11, 21 - 2*n), leading=max(17, 25-2*n),
             spaceBefore=max(6, 16 - n), spaceAfter=9, keepWithNext=True)
    styles["source"] = ParagraphStyle("source", parent=styles["p"], fontSize=8,
                                       leading=12, textColor=colors.grey, leftIndent=10)
    styles["formula"] = ParagraphStyle("formula", parent=styles["p"],
                                        fontSize=9, leading=14, leftIndent=15)
    story = []
    output = Path(path)
    assets_root = Path(assets_root or output.parent)
    def para(s, style):
        # Preserve LaTeX as literal text; PDF typesetting of arbitrary TeX needs a TeX engine.
        safe = html.escape(s or "").replace("\n", "<br/>")
        safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)
        return Paragraph(safe, style)
    for pg in pages:
        for b in pg.blocks:
            if b.kind == "image":
                fp = assets_root / b.image
                if fp.exists():
                    try:
                        from PIL import Image as PILImage
                        with PILImage.open(fp) as im:
                            w, h = im.size
                        scale = min(1.0, 480 / max(w, 1), 580 / max(h, 1))
                        story.append(Image(str(fp), width=w*scale, height=h*scale))
                        story.append(Spacer(1, 8))
                    except Exception:
                        story.append(para("[Image: " + b.image + "]", styles["source"]))
                continue
            if b.kind == "table":
                try:
                    rows = json.loads(b.translation) if b.translation else b.rows
                except (ValueError, TypeError):
                    rows = b.rows
                if not rows:
                    continue
                width = max(map(len, rows))
                if width > 8:
                    story.append(para("[Wide table: see Markdown]", styles["p"]))
                    continue
                rows = [row + [""] * (width - len(row)) for row in rows]
                cells = [[para(s, styles["source"] if i else styles["p"]) for s in row] for i,row in enumerate(rows)]
                tbl = Table(cells, repeatRows=1, hAlign="LEFT", colWidths=[470/width]*width)
                tbl.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .3, colors.grey),
                    ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
                    ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 3),
                    ("RIGHTPADDING", (0,0), (-1,-1), 3)]))
                story.append(tbl)
                story.append(Spacer(1,10))
                continue
            val = b.translation or b.text
            style = (styles[f"h{max(1,min(6,b.level))}"] if b.kind in ("heading","title")
                     else styles["formula"] if b.kind == "equation" else styles["p"])
            story.append(para(val, style))
            if mode == "bilingual" and val != b.text and b.kind not in {"equation"}:
                story.append(para(b.text, styles["source"]))
    # Default A4 reading copy, not original fixed layout.
    doc = SimpleDocTemplate(str(output), pagesize=(595.28, 841.89),
        rightMargin=53, leftMargin=53, topMargin=53, bottomMargin=53,
        title=output.stem, author="AcademicPDF Studio")
    doc.build(story)
    return output
