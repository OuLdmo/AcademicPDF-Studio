"""Page-by-page extraction, persistent caches, translation and exports."""
import json
import logging
import re
from pathlib import Path

import pymupdf as fitz

from .cache import digest_text, file_digest, read_json, write_json
from .export import render_markdown, render_txt, render_pdf
from .parser import parse_fitz_page, parse_docling_page, recurrent_margins
from .schema import Page
from .translate import Translator, translate_pages
from .pdf_health import configure_mupdf, guarded_pdf_call, concise_diagnostics

log = logging.getLogger(__name__)
CACHE_FORMAT = "paperstudio-v0.4.1-resilient-parsing-20261009"


def discover(path):
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ValueError("Input file must be .pdf")
        return [path]
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def process_pdf(input_file, output_root, *, backend="fitz", engine="ollama",
                model="qwen2.5:7b", url=None, api_key=None, mode="zh", formats=("md","txt","pdf"),
                glossary=None, progress=print, force=False, snapshots=False,
                equation_ocr="off", vector_figures=True, stitch_tables=True,
                pdf_layout="reflow"):
    if pdf_layout not in {'reflow','overlay'}:
        raise ValueError('pdf_layout must be reflow or overlay')
    input_file = Path(input_file).resolve()
    if backend not in {"fitz", "docling"}:
        raise ValueError("--backend must be fitz or docling")
    if mode not in {"zh", "bilingual"}:
        raise ValueError("--mode must be zh or bilingual")
    invalid_formats = set(formats) - {"md", "txt", "pdf"}
    if invalid_formats:
        raise ValueError(f"Invalid formats: {invalid_formats}")
    content_hash = file_digest(input_file)
    # Stable per-input directory; identical titles from different folders have distinct hashes.
    safe_stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", input_file.stem)[:90]
    dest = Path(output_root).expanduser().resolve() / (safe_stem + "_" + content_hash[:8])
    assets = dest / "assets"
    page_cache = dest / ".cache" / "pages"
    dest.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    page_cache.mkdir(parents=True, exist_ok=True)
    pages = []
    eq_recognizer = None
    if equation_ocr != 'off':
        from .equations import EquationOCR
        eq_recognizer = EquationOCR(equation_ocr)
    progress(f"开始解析: {input_file.name} (backend={backend})")
    configure_mupdf()
    diagnostics = []
    pdf = guarded_pdf_call('open PDF', 0, diagnostics,
                           lambda: fitz.open(str(input_file)), required=True)
    with pdf:
        if pdf.needs_pass:
            raise ValueError('PDF is password-protected. Unlock it before translation.')
        common = recurrent_margins(pdf, diagnostics=diagnostics) if backend == "fitz" else set()
        for i in range(pdf.page_count):
            key = digest_text(CACHE_FORMAT, content_hash, backend, i, snapshots, equation_ocr, vector_figures)
            cache_file = page_cache / f"{i+1:04d}_{key[:10]}.json"
            data = None if force else read_json(cache_file)
            if data:
                pg = Page.from_dict(data)
                # If assets are deleted, don't trust the cache.
                if any(b.image and not (dest / b.image).exists() for b in pg.blocks):
                    data = None
            if not data:
                try:
                    if backend == "docling":
                        pg = guarded_pdf_call('docling page', i+1, diagnostics,
                            lambda: parse_docling_page(pdf, i, assets, snapshots=snapshots),
                            fallback=None)
                        if pg is None:
                            diagnostics.append(dict(stage='docling fallback', page=i+1,
                                severity='fallback', message='Docling failed: native parser used instead', count=1))
                            pg = parse_fitz_page(pdf, i, assets, common, snapshots=snapshots,
                                vector_figures=vector_figures, equation_recognizer=eq_recognizer,
                                diagnostics=diagnostics)
                    else:
                        pg = parse_fitz_page(pdf, i, assets, common, snapshots=snapshots,
                            vector_figures=vector_figures, equation_recognizer=eq_recognizer,
                            diagnostics=diagnostics)
                    state = "parsed"
                    # Do not cache page-level failures or partial fallback pages as verified extracts.
                    if not any(d['page'] == i+1 and d['severity'] in
                               {'exception', 'fallback', 'mupdf', 'skipped'} for d in diagnostics):
                        write_json(cache_file, pg.as_dict())
                except Exception as exc:
                    diagnostics.append(dict(stage='page processing', page=i+1,
                        severity='exception', message=f'{type(exc).__name__}: {exc}'[:450], count=1))
                    pg = Page(i+1, 595, 842, [])
                    state = "failed; retained page marker for review"
            else:
                state = "cached"
            pages.append(pg)
            progress(f"[PAGE {i+1}/{pdf.page_count}] {state}")
    table_stitches = []
    if stitch_tables:
        from .tables import stitch_across_pages
        table_stitches = stitch_across_pages(pages)
    coverage_warnings = []
    for pg in pages:
        if not any(b.kind in {"paragraph", "heading", "title", "markdown", "table"}
                   and (b.text.strip() or b.rows) for b in pg.blocks):
            coverage_warnings.append(f"Page {pg.number}: no recoverable text; retry with --backend docling (OCR)")
    translator = Translator(engine=engine, model=model, url=url, api_key=api_key, glossary=glossary,
                            cache_path=dest / ".cache" / "translations.json")
    translate_pages(pages, translator, progress=progress)
    base = dest / safe_stem
    files = {}
    overlay_issues = []
    if "md" in formats:
        path = base.with_suffix(".md")
        path.write_text(render_markdown(pages, mode, engine), encoding="utf-8")
        files["md"] = str(path)
    if "txt" in formats:
        path = base.with_suffix(".txt")
        path.write_text(render_txt(pages, mode), encoding="utf-8")
        files["txt"] = str(path)
    if "pdf" in formats:
        path = base.with_suffix(".pdf")
        if pdf_layout == 'overlay':
            from .overlay import render_overlay
            problems = guarded_pdf_call('PDF overlay export', 0, diagnostics,
                lambda: render_overlay(input_file, pages, path), fallback=None)
            if problems is None:
                render_pdf(pages, path, mode, dest)
                overlay_issues = ['Overlay failed; generated reflow PDF instead']
            else:
                overlay_issues = problems
        else:
            render_pdf(pages, path, mode, dest)
            overlay_issues = []
        files["pdf"] = str(path)
    diagnostic_warnings = concise_diagnostics(diagnostics)
    report = {"source": str(input_file), "sha256": content_hash,
              "pages": len(pages), "backend": backend, "engine": engine,
              "model": model, "mode": mode, "outputs": files,
              "pdf_layout": pdf_layout, "equation_ocr": equation_ocr,
              "vector_figures": vector_figures, "table_stitches": table_stitches,
              "overlay_issues": overlay_issues if "pdf" in formats else [],
              "diagnostics": diagnostics, "needs_review": bool(diagnostics or coverage_warnings or translator.warnings or overlay_issues),
              "warnings": coverage_warnings + translator.warnings + diagnostic_warnings +
                         [f"PDF overlay: {w}" for w in (overlay_issues if "pdf" in formats else [])],
              "limits": ["Markdown is flow layout; no pixel-exact preservation",
                         "No automatic pixel-exact LaTeX recovery or merged-cell Markdown",
                         "Check vector drawings and footnotes against source"]}
    write_json(dest / "manifest.json", report)
    progress(f"完成: {dest}")
    for warning in report["warnings"]:
        progress("警告: " + warning)
    return report
