"""Optional offline mathematical OCR with conservative failure behavior.

The model is never downloaded unless the user explicitly selects --equation-ocr pix2tex.
OCR is uncertain: latex and original image are both kept for audit.
"""
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image


class EquationOCR:
    def __init__(self, backend="off"):
        self.backend = backend
        self.model = None
        if backend not in {"off", "pix2tex"}:
            raise ValueError("Unknown equation OCR backend")

    def recognize(self, page, rect, assets: Path, identifier: str):
        if self.backend == "off":
            return "", ""
        assets.mkdir(parents=True, exist_ok=True)
        # Larger rendering helps distinguish subscripts, superscripts and Greek symbols.
        crop = fitz.Rect(rect) + (-3, -3, 3, 3)
        crop = crop & page.rect
        img_path = assets / f"{identifier}_math.png"
        page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=crop, alpha=False).save(str(img_path))
        if self.model is None:
            try:
                from pix2tex.cli import LatexOCR
            except ImportError as e:
                raise RuntimeError('Missing pix2tex. Run: pip install "pix2tex[api]" (or pix2tex)') from e
            self.model = LatexOCR()
        try:
            result = str(self.model(Image.open(img_path).convert("RGB"))).strip()
        except Exception as e:
            raise RuntimeError(f"pix2tex failed on {identifier}: {e}") from e
        result = result.strip('$ \t\r\n')
        if not result or len(result) > 5000 or re.search(r"[\x00-\x08]", result):
            raise ValueError(f"Invalid math OCR output: {identifier}")
        return result, "assets/" + img_path.name


def math_equation_candidate(block):
    """Conservative detection; not an arbitrary line with equals sign.

    A centered or short equation line may still be missed; this is why a model
    backend is opt-in and the unmodified source PDF is always available.
    """
    if block.kind != 'equation':
        return False
    s = block.text.strip()
    return 1 < len(s) < 240 and any(c in s for c in '=∑∫√∂∇')
