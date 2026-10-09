"""Extract likely vector figures without mistaking table grid lines for figures.

Raster clips are stable and portable in Markdown; optional clipped SVG is
retained as a separate asset for high-fidelity reuse and inspection.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf as fitz

from .schema import Block
from .pdf_health import guarded_pdf_call, risky_graphics


def _intersection_fraction(a, b):
    overlap = (fitz.Rect(a) & fitz.Rect(b)).get_area()
    return overlap / max(1., fitz.Rect(a).get_area())


def extract_vector_figures(page, index, assets, table_areas, occupied_images=(), min_atoms=6, diagnostics=None):
    """Geometry-based candidates, never assert semantic chart recognition.

    Suppress clusters that look like tiny rules, page frames, table borders or
    near-full-page background. Deterministic extraction enables regression tests.
    """
    diagnostics = diagnostics if diagnostics is not None else []
    drawings = guarded_pdf_call('vector paths', index+1, diagnostics, lambda: page.get_drawings(), fallback=[])
    if not drawings or risky_graphics(diagnostics):
        return []
    clusters = guarded_pdf_call('vector clusters', index+1, diagnostics, lambda: page.cluster_drawings(), fallback=[])
    if not drawings or not clusters:
        return []
    output = []
    for ix, raw_rect in enumerate(clusters):
        rect = fitz.Rect(raw_rect) & page.rect
        w, h = rect.width, rect.height
        if w < 65 or h < 35 or rect.get_area() < 3300:
            continue
        if w > page.rect.width * .94 or h > page.rect.height * .72:
            continue
        if any(_intersection_fraction(rect, other) > .25 for other in [*table_areas, *occupied_images]):
            continue
        atoms = sum(1 for d in drawings if fitz.Rect(d['rect']).intersects(rect))
        if atoms < min_atoms:
            continue
        # Avoid duplicate/overlapping crops.
        if any(_intersection_fraction(rect, b.bbox) > .5 for b in output):
            continue
        assets.mkdir(parents=True, exist_ok=True)
        png = assets / f"page{index+1:04d}_vector{ix:03d}.png"
        clip = (rect + (-3, -3, 3, 3)) & page.rect
        if not png.exists():
            guarded_pdf_call('vector raster crop', index+1, diagnostics,
                lambda: page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=clip, alpha=False).save(str(png)))
        if not png.exists():
            continue
        svg_rel = ""
        try:
            svg = guarded_pdf_call('vector svg', index+1, diagnostics,
                lambda: page.get_svg_image(text_as_path=False), fallback='')
            if not svg:
                raise ValueError('SVG generation returned no content')
            # get_svg_image produces a full-page SVG: restrict its viewport to
            # this region; all underlying vector commands remain as actual paths.
            root = ET.fromstring(svg)
            root.set('viewBox', f'{clip.x0} {clip.y0} {clip.width} {clip.height}')
            root.set('width', str(clip.width))
            root.set('height', str(clip.height))
            svg = ET.tostring(root, encoding='unicode')
            svg_path = assets / f"page{index+1:04d}_vector{ix:03d}.svg"
            # SVG contains vector geometry. Source PDF remains authoritative.
            if not svg_path.exists():
                svg_path.write_text(svg, encoding='utf-8')
            svg_rel = 'assets/' + svg_path.name
        except (AttributeError, RuntimeError, ValueError):
            pass
        output.append(Block('image', image='assets/' + png.name,
                            bbox=list(rect), vector_svg=svg_rel,
                            review=['Vector illustration captured by geometry; verify clip and caption']))
    return output
