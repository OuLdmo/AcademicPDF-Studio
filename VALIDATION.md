# AcademicPDF Studio v0.2.0 — validation report

## Scope and reproducibility

**IEEE style, not real IEEE publications.** Three rights-clear, hand-annotated, generated two-column PDFs exercise (i) reading order and numbered headings, (ii) multi-page table and repeated header, and (iii) formula text and vector drawings. The generator lives at `benchmark/generate_ieee_fixtures.py`; gold annotations are `benchmark/fixtures/*.gold.json`.

Run:

```powershell
python -m pip install -r requirements-benchmark.txt
python -m pytest tests -q
python benchmark/run_benchmark.py
```

Generated full machine-readable reports are in `benchmark/results/benchmark_report.json`; readable summary in `benchmark/results/benchmark_summary.md`.

## Two separate objectives

**Markdown structural quality** uses manual anchors, heading F1, reading-order pair agreement, table content and shape match, raw equation-text preservation and figure capture (only those applicable to each fixture). The macro only averages *annotated/observable tasks*; it is not page-wide precision or a verified formula-LaTeX-OCR score. For real manuscripts, ground truth must be annotated manually before computing accuracy.

**PDF visual quality** renders original and result to grayscale thumbnail pages and computes SSIM (pixel structural similarity) plus dilated foreground-mask IoU (coarse layout overlap). The score includes all changed language glyphs. High SSIM is not proof of correct Chinese translation, semantic correspondence, native vector recovery or print-ready equivalence.

Synthetic mock Chinese replacement uses predetermined Chinese placeholder text, not an LLM translation service. It measures the **overlay mechanism only**. If Chinese does not fit the original rectangle, the converter records an overflow and preserves the original text instead of silently truncating content.

## Key limitations not validated by this build

- No real pix2tex model checkpoints were installed; only its interface, image cropping, LaTeX serialization and fallback logic have been tested with an injected deterministic mock. No formula recognition accuracy can be claimed.
- Real IEEE manuscripts, their figures/equations and editor-specific rendering have not been benchmarked against manual ground truth. The three generated test PDFs do not constitute a representative production benchmark.
- Table stitching is conservative and can miss a split table; false stitches are possible if two separate near-identical tables meet all heuristics. Human review needed.
- Visual SVG candidate detection is geometrical (clusters of native PDF paths), **not a semantic chart classifier**. Rasterized Markdown figures are editable only as embedded assets; the companion SVG preserves the source vector drawing for inspection.
- The exported reflow PDF is not 1:1 with the original page. `--pdf-layout overlay` follows original coordinates where text can fit, and gives a warnings list if not.
- Neither the Windows PyInstaller build nor any Windows installation has been completed in this Linux environment; no compiled EXE is present here.

## Development regression

The old v0.1.0 pipeline can be run on these same generated fixtures to compare. This is a tiny, tightly targeted regression, not a claim of broad improved document accuracy. New tests include formula OCR image preservation (mock), non-merge protection, cross-page rows, HTML cell spans, PDF visual metrics, and SVG clip.

## Observed test results, 2026-10-08

On 3 limited synthetic fixtures, v0.2.0 reported an observed-task structure macro of **1.000** each. With the same generated fixtures and the original v0.1.0 parser (re-evaluated against the v0.2.0 gold annotation), observed-task macros were **0.700 / 0.889 / 0.733** for cross-page table / simple two-column / vector-formula, respectively. This particular improvement is largely due to recognizing numbered headings as headings and capturing vector figures. These tiny fixtures are too narrow to establish generalized accuracy. The mock Chinese PDF overlay produced approximate SSIM **0.977 / 0.973 / 0.968**, with coarse layout-mask IoU **0.962 / 0.929 / 0.940**. The overlay logged **1 / 1 / 2** overflow blocks respectively, which remain untranslated in the visual PDF for manual review. For the full per-page machine-readable report, open `benchmark/results/benchmark_report.json`.
