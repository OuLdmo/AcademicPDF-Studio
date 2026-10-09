"""MuPDF diagnostics, safe optional extraction and human-readable QA reports.

Do NOT discard MuPDF errors. MuPDF internally stores diagnostic messages even
when its default printing is disabled; we attach them to the corresponding
operation/page and write them to the final manifest. A PDF parsing failure is
not treated as proof the returned page is complete or visually correct.

PyMuPDF diagnostics are process-global. A lock prevents simultaneous operations
in the Web service from attributing another job's messages to this page.
"""
from __future__ import annotations

import logging
import threading
from collections import Counter

import pymupdf

logger = logging.getLogger(__name__)
PDF_LOCK = threading.RLock()


def configure_mupdf():
    """Keep recoverable diagnostics from endlessly flooding CMD/PowerShell.

    MuPDF *still accumulates* messages via TOOLS.mupdf_warnings(), and they are
    surfaced as structured warnings in manifest.json and progress callbacks.
    """
    with PDF_LOCK:
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)
        pymupdf.TOOLS.reset_mupdf_warnings()


def _collect(stage, page, diagnostics):
    raw = pymupdf.TOOLS.mupdf_warnings(reset=True)
    if not raw:
        return []
    normalized = [line.strip() for line in raw.splitlines() if line.strip()]
    counts = Counter(normalized)
    messages = []
    for msg, count in counts.most_common(25):
        record = dict(stage=stage, page=page, severity='mupdf', message=msg[:450], count=count)
        messages.append(record)
        diagnostics.append(record)
    if len(counts) > 25:
        diagnostics.append(dict(stage=stage, page=page, severity='mupdf',
                                message=f'{len(counts)-25} other distinct MuPDF diagnostics', count=1))
    return messages


def guarded_pdf_call(stage, page, diagnostics, callback, *, fallback=None, required=False):
    """Call one PyMuPDF operation; attach warnings even if no exception is raised.

    A required failed call raises after diagnostics are recorded. Optional stages
    return a conservative default and report the failure in manifest.json.
    """
    with PDF_LOCK:
        pymupdf.TOOLS.reset_mupdf_warnings()
        failure = None
        result = fallback
        try:
            result = callback()
        except Exception as exc:
            failure = exc
        finally:
            _collect(stage, page, diagnostics)
        if failure is not None:
            diagnostics.append(dict(stage=stage, page=page, severity='exception',
                                    message=f'{type(failure).__name__}: {failure}'[:450], count=1))
            if required:
                raise failure
        return result


def risky_graphics(diagnostics):
    """A malformed PDF function should not be repeatedly re-rendered for SVGs.

    Keep structured text and continue the document, but treat vector/exact
    screenshot extraction as unreliable and ask the user to verify source.
    """
    return any('stitching function' in d.get('message','').lower() or
               'cannot render' in d.get('message','').lower()
               for d in diagnostics)


def concise_diagnostics(diagnostics, *, limit=20):
    grouped = Counter()
    for d in diagnostics:
        grouped[(d['page'], d['stage'], d['severity'], d['message'])] += d.get('count', 1)
    result = []
    for (page, stage, severity, message), occurrences in grouped.most_common(limit):
        result.append(f'Page {page}, {stage}: {message} ({occurrences} occurrence(s))')
    if len(grouped) > limit:
        result.append(f'... and {len(grouped)-limit} more diagnostic groups (see manifest.json)')
    return result
