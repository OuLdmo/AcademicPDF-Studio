"""CLI: python -m paperstudio / paperstudio command."""
import argparse
import json
import sys
from pathlib import Path

from .pipeline import discover, process_pdf
from .engines import ENGINES, defaults


def parser():
    p = argparse.ArgumentParser(prog="paperstudio", description="Local-first PDF academic translator")
    p.add_argument("input", help="PDF path or a directory (recursive)")
    p.add_argument("-o", "--output", default="./paperstudio_output")
    p.add_argument("--backend", choices=["fitz", "docling"], default="fitz")
    p.add_argument("--engine", choices=list(ENGINES), default="ollama")
    p.add_argument("--model", default=None, help="Default qwen2.5:7b for Ollama, gpt-4.1-mini for OpenAI")
    p.add_argument("--api-key", help="API key (visible in shell history); prefer setting the engine environment variable")
    p.add_argument("--api-url", help="Custom Ollama/OpenAI-compatible/DeepL endpoint; opt-in")
    p.add_argument("--mode", choices=["zh", "bilingual"], default="zh")
    p.add_argument("--formats", default="md,pdf,txt", help="Comma-separated: md,pdf,txt")
    p.add_argument("--glossary", help="Terminology JSON: {\"ECG\": \"心电图\"}")
    p.add_argument("--force", action="store_true", help="Reparse pages; translation cache kept")
    p.add_argument("--snapshot-pages", action="store_true", help="Append a full-page visual backup per page (larger output)")
    p.add_argument("--equation-ocr", choices=["off","pix2tex"], default="off",
                   help="Opt-in local pix2tex formula OCR; requires heavy optional model")
    p.add_argument("--no-vectors", action="store_true", help="Disable vector graphic extraction")
    p.add_argument("--no-table-stitch", action="store_true", help="Disable conservative multipage table stitching")
    p.add_argument("--pdf-layout", choices=["reflow","overlay"], default="reflow",
                   help="Reflow reading copy or preserve original page geometry with translated overlay")
    p.add_argument("--strict", action="store_true", help="Deprecated: translation failures already return a nonzero status")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        formats = tuple(x.strip().lower() for x in args.formats.split(",") if x.strip())
        glossary = {}
        if args.glossary:
            glossary = json.loads(Path(args.glossary).read_text(encoding="utf-8"))
            if not isinstance(glossary, dict):
                raise ValueError("Glossary must be JSON object")
        files = discover(args.input)
        if not files:
            print("No PDFs were found.", file=sys.stderr)
            return 1
        failed = 0
        for file in files:
            try:
                report = process_pdf(file, args.output, backend=args.backend,
                    engine=args.engine,
                    model=args.model or defaults(args.engine)["model"],
                    url=args.api_url, api_key=args.api_key,
                    mode=args.mode, formats=formats, glossary=glossary, force=args.force,
                    snapshots=args.snapshot_pages, equation_ocr=args.equation_ocr,
                    vector_figures=not args.no_vectors,
                    stitch_tables=not args.no_table_stitch, pdf_layout=args.pdf_layout)
                # Always report a nonzero exit code if any text could not be translated.
                # A partial file is still saved for review and resume.
                if report["warnings"]:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"ERROR processing {file}: {e}", file=sys.stderr)
        print(f"Processing finished: total={len(files)} failed={failed}")
        return 1 if failed else 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
