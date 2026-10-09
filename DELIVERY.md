# Delivery checklist — AcademicPDF Studio v0.2.0

## Included

- `paperstudio/`: modular Python code for PDF parsing, optional local pix2tex OCR, geometry-based vector extraction, cross-page table stitching, translation engine adapters, Markdown/TXT/PDF export, fixed-geometry PDF overlay, QA metrics, persistent caching and Tkinter GUI.
- `requirements.txt`, `requirements-math-ocr.txt`, `requirements-benchmark.txt` and Windows launcher/build batch scripts.
- `.github/workflows/windows-build.yml`: **Windows-native** PyInstaller build plus unit-test and CLI smoke-test steps.
- `benchmark/fixtures/`: generated IEEE-like two-column PDF fixtures, each with manually specified gold labels, plus generator.
- `benchmark/results/benchmark_summary.md` / `benchmark_report.json`: latest local output scores.
- `examples/v020_sample/`: a sample Markdown + assets and simulated Chinese PDF overlay, for review.
- `README.md`, `VALIDATION.md`, `BUILD_WINDOWS.md`.

## Verification completed

- 11 automated tests passed in Linux Python environment.
- 3 synthetic IEEE-style documents processed with independent structure and PDF visual metrics.
- Mock translation overlay rendered and checked for Chinese text and retained vector figure; overflow issues reported.
- ZIP archive tested for CRC and file listing.

## Not delivered / limitations

- **No precompiled Windows EXE is included.** Linux runtime cannot produce a correctly bundled/tested Windows PyInstaller EXE; building is specified for actual Windows in workflow/BAT.
- **No real pix2tex OCR model accuracy verification.** Optional integration test injects a deterministic stand-in.
- **No real-world IEEE PDF gold-standard validation.** Fixture scores are optimistic for limited synthetic target structures.
- **No pixel-perfect full-text translation across arbitrary PDFs.** Overflow can leave original text and must be reviewed.
- PyMuPDF AGPL/commercial licensing applies to binary redistribution.
