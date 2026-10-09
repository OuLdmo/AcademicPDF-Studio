"""Born-digital PDF layout parser; optional Docling OCR-rich mode.

There is no claim that PDF glyphs can be reverse-engineered into perfect LaTeX.
Images contain bitmap blocks only; vector figures may require Docling/manual QA.
"""
import io
import re
import statistics
from collections import Counter
from pathlib import Path

import pymupdf as fitz
from PIL import Image

from .schema import Block, Page
from .pdf_health import guarded_pdf_call, risky_graphics

HEAD_PATTERN = re.compile(r"^\s*(?:\d+(?:\.\d+){0,5}[.、]?\s+|(?:[IVX]+\.)\s+|(?:Abstract|Introduction|Conclusions?|References|Methods|Results|Discussion|Acknowledgm?ents)\s*$)", re.I)
LIST_PATTERN = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+")
PAGE_NO = re.compile(r"^(?:\d{1,4}|[ivxlcdm]{1,7})$", re.I)
EQ_PATTERN = re.compile(r"(?:\\(?:frac|sum|int|sqrt|begin|alpha|beta|gamma)\b|\$\$.+\$\$|[=∑∫√∂]{1,})")
CAPTION_PATTERN = re.compile(r"^(?:Fig(?:ure)?\.?|Table|Scheme)\s*\d+\b", re.I)


def compact(text):
    text = text.replace("\u00ad", "")
    return re.sub(r"\s+", " ", text).strip()


def join_lines(lines):
    """Join PDF visual lines while fixing common hyphenated line ends."""
    parts = []
    for s in lines:
        s = compact(s)
        if not s:
            continue
        if parts and parts[-1].endswith("-") and s[:1].islower():
            parts[-1] = parts[-1][:-1] + s
        else:
            parts.append(s)
    return " ".join(parts)


def _get_spanlines(raw):
    lines = []
    sizes = []
    bold = 0
    for line in raw.get("lines", []):
        pieces = []
        for span in line.get("spans", []):
            s = span.get("text", "")
            pieces.append(s)
            if s.strip():
                sizes.append(float(span.get("size", 0)))
                if span.get("flags", 0) & 16 or "Bold" in span.get("font", ""):
                    bold += 1
        if "".join(pieces).strip():
            lines.append("".join(pieces))
    return lines, (max(sizes) if sizes else 0), bold


def _read_order(blocks, width):
    """Group by vertical bands. In each band read left column then right.

    Wide heading/image blocks divide bands. This beats naive y,x sorting for
    common two-column IEEE PDFs, but not arbitrary magazine layouts.
    """
    if not blocks:
        return []
    middle = width / 2
    narrow = [b for b in blocks if b.bbox and (b.bbox[2] - b.bbox[0]) < width * .62]
    left = [b for b in narrow if (b.bbox[0] + b.bbox[2]) / 2 < middle]
    right = [b for b in narrow if (b.bbox[0] + b.bbox[2]) / 2 >= middle]
    two_cols = bool(left and right and len(narrow) >= 4)
    if not two_cols:
        return sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
    separators = sorted([b for b in blocks if (b.bbox[2] - b.bbox[0]) >= width * .68], key=lambda b: b.bbox[1])
    result, remaining = [], list(blocks)
    cuts = [-1.] + [((s.bbox[1] + s.bbox[3]) / 2) for s in separators] + [float("inf")]
    # Keep separators in their appropriate vertical position.
    for i in range(len(cuts) - 1):
        lo, hi = cuts[i:i+2]
        group = [b for b in remaining if lo <= (b.bbox[1] + b.bbox[3]) / 2 < hi and b not in separators]
        result += sorted((b for b in group if (b.bbox[0] + b.bbox[2]) / 2 < middle), key=lambda b: b.bbox[1])
        result += sorted((b for b in group if (b.bbox[0] + b.bbox[2]) / 2 >= middle), key=lambda b: b.bbox[1])
        if i < len(separators):
            result.append(separators[i])
    return result


def recurrent_margins(doc, diagnostics=None):
    """Only suppress near-identical strings repeated in margins on >=2 pages."""
    counts = Counter()
    diagnostics = diagnostics if diagnostics is not None else []
    for page in doc:
        if len(doc) < 2:
            break
        data = guarded_pdf_call('margin scan', page.number+1, diagnostics,
                                lambda: page.get_text('dict'), fallback={'blocks': []})
        for raw in data.get("blocks", []):
            if raw.get("type") != 0:
                continue
            rect = fitz.Rect(raw["bbox"])
            if rect.y0 > page.rect.height * .12 and rect.y1 < page.rect.height * .88:
                continue
            s = compact(join_lines(_get_spanlines(raw)[0]))
            if s and len(s) <= 130:
                counts[s] += 1
    return {s for s, n in counts.items() if n >= 2}


def _save_image(raw, clip, page, assets, prefix):
    assets.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}.png"
    path = assets / name
    if not path.exists():
        try:
            with Image.open(io.BytesIO(raw.get("image", b""))) as im:
                im.convert("RGB").save(path)
        except Exception:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=fitz.Rect(clip), alpha=False)
            pix.save(path)
    return "assets/" + name


def parse_fitz_page(doc, index, assets, recurrent=None, dpi=144, snapshots=False,
                    vector_figures=True, equation_recognizer=None, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else []
    page = doc.load_page(index)
    raw_data = guarded_pdf_call('structured text', index+1, diagnostics,
                                lambda: page.get_text('dict', flags=fitz.TEXTFLAGS_DICT),
                                fallback=None)
    if raw_data is None:
        # A fallback page must not masquerade as full-quality structured OCR.
        text = guarded_pdf_call('plain-text fallback', index+1, diagnostics,
                                lambda: page.get_text('text'), fallback='')
        diagnostics.append(dict(stage='structured text', page=index+1, severity='fallback',
                                message='Structured extraction failed; only plain text retained', count=1))
        blocks = [Block('paragraph', text, bbox=[], review=['Fallback text has no reliable layout coordinates'])] if text.strip() else []
        return Page(index+1, float(page.rect.width), float(page.rect.height), blocks)
    raw_blocks = raw_data.get('blocks', [])
    spans = []
    for raw in raw_blocks:
        if raw.get("type") == 0:
            _, size, _ = _get_spanlines(raw)
            if size:
                spans.append(size)
    body_size = statistics.median(spans) if spans else 10.0
    blocks = []
    table_areas = []
    found_tables = None if risky_graphics(diagnostics) else guarded_pdf_call(
        'table detection', index+1, diagnostics, lambda: page.find_tables(), fallback=None)
    try:
        for tid, tbl in enumerate(found_tables.tables if found_tables else []):
            rows = [[compact(cell or "") for cell in row] for row in (tbl.extract() or [])]
            if not rows:
                continue
            rect = fitz.Rect(tbl.bbox)
            table_areas.append(rect)
            # Geometry-informed merged cells: Markdown GFM cannot express spans.
            # A downstream renderer can use minimal HTML only when necessary.
            spans = []
            try:
                rectangles = [c for row in tbl.rows for c in row.cells if c]
                x_edges = sorted({round(v, 2) for c in rectangles for v in (c[0],c[2])})
                y_edges = sorted({round(v, 2) for c in rectangles for v in (c[1],c[3])})
                for ri, row in enumerate(tbl.rows):
                    for ci, cell in enumerate(row.cells):
                        if cell is None:
                            continue
                        c = fitz.Rect(cell)
                        # Use the row/column index as the anchor; its geometric
                        # extent gives the number of spanned unit cells.
                        cs = sum(c.x0 + .5 < e <= c.x1 + .5 for e in x_edges)
                        rs = sum(c.y0 + .5 < e <= c.y1 + .5 for e in y_edges)
                        if cs > 1 or rs > 1:
                            spans.append([ri,ci,rs,cs])
            except (AttributeError, ValueError, TypeError):
                pass
            blocks.append(Block("table", bbox=list(rect), rows=rows, spans=spans,
                                table_pages=[index+1]))
    except (AttributeError, ValueError, RuntimeError):
        pass
    for number, raw in enumerate(raw_blocks):
        rect = fitz.Rect(raw["bbox"])
        if rect.is_empty:
            continue
        # Never duplicate content extracted as a structured table.
        if any((rect & area).get_area() > rect.get_area() * .65 for area in table_areas):
            continue
        if raw.get("type") == 1:
            path = guarded_pdf_call('embedded image', index+1, diagnostics,
                lambda: _save_image(raw, rect, page, assets, f"page{index+1:04d}_img{number:03d}"), fallback='')
            if path:
                blocks.append(Block("image", bbox=list(rect), image=path))
            continue
        if raw.get("type") != 0:
            continue
        lines, size, bold = _get_spanlines(raw)
        content = join_lines(lines)
        if not content:
            continue
        # Page numbers and repeating headers/footers: do not drop nonrecurrent academic footnotes.
        at_edge = rect.y1 <= page.rect.height * .10 or rect.y0 >= page.rect.height * .90
        if at_edge and (content in (recurrent or set()) or PAGE_NO.fullmatch(content)):
            continue
        kind, level = "paragraph", 0
        is_numbered_heading = bool(re.match(r'^\s*(?:\d+(?:\.\d+)*\.?|[IVX]+\.)\s+[A-Z][A-Za-z\s]{2,110}$', content)) and bold > 0
        if is_numbered_heading:
            kind = "heading"
            numbered = re.match(r'^\s*(\d+(?:\.\d+)*)', content)
            level = min(6, 2 + numbered.group(1).count('.')) if numbered else 2
        elif LIST_PATTERN.match(content):
            kind = "list"
        elif content.startswith(("“", '"', "❝")) and content.endswith(("”", '"', "❞")):
            kind = "quote"
        elif EQ_PATTERN.search(content) and len(content) < 130 and (content.startswith("$") or "=" in content):
            kind = "equation"
        elif index == 0 and rect.y0 < page.rect.height * .33 and size >= body_size * 1.35:
            kind, level = "title", 1
        elif (HEAD_PATTERN.match(content) or (size > body_size * 1.18 and len(content) < 115)) and not CAPTION_PATTERN.match(content):
            kind = "heading"
            numbered = re.match(r"^\s*(\d+(?:\.\d+)*)[.)]?\s+", content)
            level = min(6, 2 + numbered.group(1).count(".")) if numbered else (2 if size > body_size * 1.25 else 3)
        elif at_edge and rect.y0 > page.rect.height * .75 and size <= body_size * .85:
            kind = "footnote"
        blocks.append(Block(kind, content, level=level, bbox=list(rect), size=size))
    if vector_figures:
        if risky_graphics(diagnostics):
            diagnostics.append(dict(stage='vector extraction', page=index+1, severity='skipped',
                message='Complex PDF function errors; skipped costly vector replay; preserve source for review', count=1))
        else:
            from .figures import extract_vector_figures
            vector_blocks = guarded_pdf_call('vector extraction', index+1, diagnostics,
                lambda: extract_vector_figures(page, index, assets, table_areas,
                    [b.bbox for b in blocks if b.kind == 'image'], diagnostics=diagnostics), fallback=[])
            blocks.extend(vector_blocks)
    if equation_recognizer is not None:
        from .equations import math_equation_candidate
        for b_index, block in enumerate(blocks):
            if math_equation_candidate(block):
                recognized = guarded_pdf_call('equation OCR', index+1, diagnostics,
                    lambda: equation_recognizer.recognize(page, block.bbox, assets,
                            f'page{index+1:04d}_eq{b_index:03d}'), fallback=None)
                if recognized:
                    latex, crop = recognized
                    block.latex = latex
                    block.equation_crop = crop
                    block.review.append('OCR-derived LaTeX: verify against source PDF')
    ordered = _read_order(blocks, page.rect.width)
    if snapshots:
        # Full-page facsimile (clearly marked visual backup, not editable text).
        # Useful for unusual vector graphs, figures, watermarks and equations.
        path = assets / f"page{index+1:04d}_facsimile.png"
        if not path.exists():
            if not risky_graphics(diagnostics):
                guarded_pdf_call('page snapshot', index+1, diagnostics,
                    lambda: page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72), alpha=False).save(path))
            else:
                diagnostics.append(dict(stage='page snapshot', page=index+1, severity='skipped',
                    message='Skipped snapshot on PDF page with malformed function diagnostics', count=1))
        if path.exists():
            ordered += [Block("paragraph", "Original page visual reference / 原页视觉备份："),
                        Block("image", image="assets/" + path.name,
                              bbox=[0, 0, page.rect.width, page.rect.height])]
    return Page(index + 1, float(page.rect.width), float(page.rect.height), ordered)


def parse_docling_page(doc, index, assets, snapshots=False):
    """Docling processes a 1-page temporary PDF, enabling per-page caching.

    Docling's exported Markdown is treated as a structured page fragment;
    native raster images are preserved separately. Pages with cross-page
    content can require extra manual adjustment.
    """
    import tempfile
    from docling.document_converter import DocumentConverter
    page = doc.load_page(index)
    with tempfile.TemporaryDirectory() as tmp:
        subset = fitz.open()
        subset.insert_pdf(doc, from_page=index, to_page=index)
        name = Path(tmp) / "page.pdf"
        subset.save(str(name))
        subset.close()
        result = DocumentConverter().convert(str(name))
        md = result.document.export_to_markdown()
    blocks = [Block("markdown", md, bbox=[0, 0, page.rect.width, page.rect.height])]
    # Assets from native image blocks; layout placement may be approximate.
    for n, b in enumerate(page.get_text("dict")["blocks"]):
        if b.get("type") == 1:
            path = _save_image(b, b["bbox"], page, assets, f"page{index+1:04d}_img{n:03d}")
            blocks.append(Block("image", image=path, bbox=list(b["bbox"])))
    if snapshots:
        path = assets / f"page{index+1:04d}_facsimile.png"
        if not path.exists():
            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(path)
        blocks.extend([Block("paragraph", "Original page visual reference / 原页视觉备份："),
                       Block("image", image="assets/" + path.name)])
    return Page(index + 1, page.rect.width, page.rect.height, blocks)
