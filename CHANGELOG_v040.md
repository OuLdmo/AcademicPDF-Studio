# AcademicPDF Studio v0.4.0 — 2026-10-08

## Windows build dependency error fixed

The v0.3.1 build script claimed all dependencies were installed after importing only pytest and PyInstaller. Then `tests/test_v020_features.py` immediately crashed with `ModuleNotFoundError: No module named 'numpy'` because `paperstudio/quality.py` imported numpy at collection time.

v0.4.0 introduces `requirements-build.txt` and **unconditionally** runs its `pip install -r` before each Windows EXE build, then validates numpy, skimage, pytest, PyInstaller, and runtime imports. Windows CI uses the same manifest.

## Translation engine configuration

- Browser: expanded engine configuration panel, model, URL, masked API Key field, and "test connection" action, with per-engine defaults.
- Desktop: new "翻译引擎配置 / API Key" pop-up with the same fields, masked credential, and asynchronous connection test.
- API keys are held in RAM for the task and are never added to conversion reports, logs, ZIP, or local browser storage. Local web service only binds loopback by default.
- Engine adapters: DeepSeek `deepseek-flash`, OpenAI, DeepL, Ollama, Argos offline en→zh, self-hosted LibreTranslate. Additional DeepSeek models may be entered manually.
- Argos optional installation via `Install-Argos.cmd`: installs engine and first-use model into the same `.venv` as the application, not system Python.
- Web engine connection test is a real short translation request and may incur API charges.

## Validation

- Regression tests including local fake DeepSeek ChatCompletions server, LibreTranslate, Argos adapter, credential omission checks, and web configuration-to-PDF flow.
- Chromium interface interaction tested with locally loaded HTML/CSS/JS. The execution environment disallows browser navigation to localhost, so this does not constitute a full browser HTTP-navigation test; server HTTP endpoints were independently exercised.
- Windows native GUI/EXE compilation and paid API tests have NOT been conducted here.

## Known limitations

- Argos needs optional dependency and the en→zh language package downloaded separately. Its translation quality for specialized scientific text can be substantially below a good LLM.
- Self-hosted LibreTranslate and local Ollama can be used without paying a translation API bill, but still consume computer resources and require installation.
- The official LibreTranslate hosted API may require a paid key; DeepSeek/OpenAI/DeepL are not assumed free.
- An EXE built without Argos optional binaries/models can still use Ollama or LibreTranslate servers; Argos in EXE would require packaging optional libraries/models separately.
- PDF OCR, complex equations and layout remain subject to previous v0.2 limitations.
