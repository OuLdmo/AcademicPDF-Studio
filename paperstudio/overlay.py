"""Fixed-page translation overlay, preserving original illustrations/geometry.

Not pixel-identical, not a redaction/security sanitization feature. Text outside
available PDF regions is logged instead of silently omitted.
"""
from pathlib import Path
import re

import pymupdf as fitz


def render_overlay(source, pages, target, min_font=5.3):
    """Translate text within original coordinates. Returns human-review issues.

    We remove text from successfully translated rectangles and replace it with
    Chinese text, leaving vector drawings and raster graphics untouched.
    This is still not certified confidential redaction of an entire document.
    """
    problems = []
    src = fitz.open(str(source))
    try:
        for p in pages:
            page = src[p.number - 1]
            pending=[]
            for bi,b in enumerate(p.blocks):
                if not b.translation or b.translation == b.text:
                    continue
                if b.kind not in {'paragraph','title','heading','list','quote','footnote'}:
                    continue
                if not b.bbox:
                    problems.append({'page': p.number, 'block': bi,
                                     'issue': 'overlay_missing_geometry; source left unchanged'})
                    continue
                r = fitz.Rect(b.bbox) & page.rect
                if r.width < 18 or r.height < 5:
                    continue
                text = re.sub(r'\s+', ' ', b.translation).strip()
                if not text:
                    continue
                # Retain original text on overflow: no false claim of full output.
                # A temporary shape lets us test insert_textbox placement without
                # mutating the PDF before a valid size is selected.
                choice = None
                font = min(max(b.size or 10, 7.8), 20.)
                while font >= min_font:
                    shape = page.new_shape()
                    spare = shape.insert_textbox(r, text, fontsize=font,
                                                fontname='china-s', lineheight=1.12)
                    if spare >= -0.01:
                        choice = (shape, font)
                        break
                    font -= .5
                if choice is None:
                    problems.append({'page':p.number,'block':bi,'issue':'overlay_text_overflow',
                                     'text':text[:130]})
                    continue
                pending.append((r,text,choice[1]))
            # Redact only rectangles with viable translations. Preserve all
            # line art and images so charts remain visually unchanged.
            for r,text,font in pending:
                page.add_redact_annot(r, fill=(1,1,1), cross_out=False)
            if pending:
                page.apply_redactions(images=0, graphics=0, text=0)
            for r,text,font in pending:
                spare=page.insert_textbox(r,text,fontname='china-s',fontsize=font,
                                          lineheight=1.12, overlay=True)
                if spare < -0.01:
                    problems.append({'page':p.number,'issue':'post_redaction_text_fit_failed',
                                     'text':text[:130]})
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        src.save(str(target), garbage=3, deflate=True)
    finally:
        src.close()
    return problems
