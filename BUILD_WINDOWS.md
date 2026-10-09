# AcademicPDF Studio 0.2.0 — Windows EXE build and verification

**Important:** This source archive does NOT contain precompiled Windows EXE files. The development runtime used for this iteration is Linux; PyInstaller does not support building Windows frozen programs directly from a Linux Python environment. Do not rename a script to `.exe`.

## Automated Windows build (recommended)

1. Create an authorized GitHub repository for this project and push **the unpacked project root**, including `.github/workflows/windows-build.yml`.
2. On that repository, choose **Actions → Windows EXE build → Run workflow** (or push a `v0.2.0` tag).
3. The workflow builds `AcademicPDF-Studio-CLI.exe` and `AcademicPDF-Studio-GUI.exe` on `windows-latest`, smoke tests CLI, and uploads `AcademicPDF-Studio-Windows` artifacts.
4. Download and unzip the artifact on a Windows 10/11 x64 machine. Open PowerShell and run `./AcademicPDF-Studio-CLI.exe --help`.
5. Run an **actual translation smoke test** with a locally installed Ollama service/model or appropriate API credentials; `--engine none` is only structural testing.

Alternatively double-click `构建Windows_EXE.bat` on Windows with Python 3.11 installed.

## Binary completeness and limitations

- PyInstaller bundles Python runtime and core dependencies; the EXE does **not** include an Ollama service, LLM checkpoints, Docling weights or pix2tex model/weights.
- For formula OCR with `--equation-ocr pix2tex`, use the **Python project** with `requirements-math-ocr.txt`; an independently packaged full model build requires the pix2tex and Torch runtime plus licensed weights and is **not** part of this lightweight EXE profile.
- Dynamic anti-virus warnings may occur with unsigned one-file EXEs. Run your own digital signing and antivirus inspection process.
- This build procedure has not been executed on actual Windows hardware in this delivery.
- PyMuPDF licensing: AGPLv3 or commercial license; review distribution/compliance before offering binaries to third parties: https://pymupdf.io/licensing/ .
