"""Translation adapters and exact protected-token validation."""
import json
import os
import re
import time
import warnings

import requests

from .cache import digest_text, read_json, write_json
from .engines import ENGINES, defaults

# Capture entire math snippets, citations, URLs, inline HTML image/link destinations,
# and equation-reference macros. No OCR-based equation recovery is claimed.
PROTECT_RE = re.compile(
    r"\$\$[\s\S]*?\$\$|\$(?!\s)(?:\\.|[^$\n])+?\$|"
    r"\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|"
    r"\\(?:cite|ref|eqref|label|autoref)\{[^{}]*\}|"
    r"\[[0-9,;\s–-]+\]|https?://[^\s)]+|"
    r"\b(?:doi\s*:\s*|10\.)\d{2,9}/[^\s,;]+|"
    r"\b(?:Fig(?:ure)?|Table|Eq(?:uation)?)\.?\s*\d+[A-Za-z]?\b",
    re.I,
)

PROMPT = """You are a careful academic translator. Translate the following scholarly text into
natural, precise Simplified Chinese. Preserve scientific meaning, units, all citations,
LaTeX/math, placeholders, bibliographic information and any Markdown syntax. Do not
add explanations, omit sentences, or hallucinate. Output translated text only.
Context (previous paragraph, for terminology only): {context}
Terminology JSON: {glossary}
Protected tokens must appear exactly as given, once each.
Text:\n{text}"""


def protect(s):
    substitutions = {}
    def sub(match):
        token = f"⟦KEEP_{len(substitutions):04d}⟧"
        substitutions[token] = match.group(0)
        return token
    return PROTECT_RE.sub(sub, s), substitutions


def restore(s, protected):
    for token, original in protected.items():
        if s.count(token) != 1:
            raise ValueError(f"The translation modified protected token {token}")
        s = s.replace(token, original)
    if "⟦KEEP_" in s:
        raise ValueError("Unrecognized protected translation token")
    return s


class Translator:
    def __init__(self, engine, model, cache_path, glossary=None, url=None, retries=2, api_key=None):
        self.engine = engine
        self.model = model
        self.url = url
        self.api_key = api_key or ""
        self.glossary = glossary or {}
        self.cache_path = cache_path
        self.cache = read_json(cache_path, {})
        self.retries = retries
        self.warnings = []
        self.previous = ""
        if engine not in ENGINES:
            raise ValueError("Unknown translation backend: " + engine)

    def _request(self, text, context):
        if self.engine == "none":
            return text
        prompt = PROMPT.format(text=text, context=context[:400],
                               glossary=json.dumps(self.glossary, ensure_ascii=False))
        if self.engine == "ollama":
            # Explicitly local by default; arbitrary user-supplied URLs are opt-in.
            endpoint = (self.url or "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
            r = requests.post(endpoint, json={"model": self.model or "qwen2.5:7b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False, "options": {"temperature": 0}}, timeout=300)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        if self.engine in {"openai", "deepseek"}:
            # OpenAI-compatible ChatCompletions: no SDK installation needed.
            info = defaults(self.engine)
            key = self.api_key or os.getenv(info["env"], "")
            if not key:
                raise ValueError(f"{info['env']} is not set; enter an API key in settings")
            base = (self.url or info["url"]).rstrip("/")
            endpoint = base if base.endswith("/chat/completions") else base + ("" if base.endswith("/v1") else ("/v1" if self.engine == "openai" and base == "https://api.openai.com" else "")) + "/chat/completions"
            response = requests.post(endpoint, json={
                "model": self.model or info["model"],
                "messages": [{"role": "system", "content": "Translate to Simplified Chinese; output translation only."},
                             {"role": "user", "content": prompt}],
                "stream": False,
            }, headers={"Authorization": "Bearer " + key}, timeout=180)
            response.raise_for_status()
            return (response.json()["choices"][0]["message"]["content"] or "").strip()
        if self.engine == "deepl":
            key = self.api_key or os.getenv("DEEPL_AUTH_KEY", "")
            if not key:
                raise ValueError("DEEPL_AUTH_KEY is not set; enter an API key in settings")
            host = self.url or ("https://api-free.deepl.com" if key.endswith(":fx") else "https://api.deepl.com")
            r = requests.post(host.rstrip("/") + "/v2/translate", data={"text": text,
                "target_lang": "ZH", "preserve_formatting": "1"},
                headers={"Authorization": "DeepL-Auth-Key " + key}, timeout=90)
            r.raise_for_status()
            return r.json()["translations"][0]["text"]
        if self.engine == "libretranslate":
            base = (self.url or defaults("libretranslate")["url"]).rstrip("/")
            endpoint = base if base.endswith("/translate") else base + "/translate"
            payload = {"q": text, "source": "auto", "target": "zh", "format": "text"}
            if self.api_key or os.getenv("LIBRETRANSLATE_API_KEY"):
                payload["api_key"] = self.api_key or os.getenv("LIBRETRANSLATE_API_KEY")
            r = requests.post(endpoint, json=payload, timeout=180)
            r.raise_for_status()
            return r.json()["translatedText"]
        if self.engine == "argos":
            try:
                import argostranslate.translate as argos
            except ImportError as exc:
                raise ValueError("Argos not installed. Run pip install -r requirements-free.txt") from exc
            try:
                return argos.translate(text, "en", "zh")
            except Exception as exc:
                raise ValueError("Argos English→Chinese model missing. Install en_zh .argosmodel first.") from exc
        raise AssertionError(self.engine)

    def test_connection(self):
        if self.engine == "none":
            return "无需翻译引擎"
        return self._request("Hello world.", "")[:400]

    def translate(self, text, skip=False):
        if skip or not text.strip() or self.engine == "none":
            return text
        key = digest_text(self.engine, self.model, self.url, self.glossary, digest_text(self.api_key)[:12] if self.api_key else "env-key", text,
                          self.previous[-400:])
        if key in self.cache:
            self.previous = text
            return self.cache[key]
        safe, replaced = protect(text)
        error = None
        for attempt in range(self.retries + 1):
            try:
                translated = restore(self._request(safe, self.previous), replaced)
                if not translated.strip():
                    raise ValueError("Translation returned empty text")
                self.cache[key] = translated
                write_json(self.cache_path, self.cache)
                self.previous = text
                return translated
            except (requests.RequestException, KeyError, ValueError, RuntimeError, ImportError, IndexError) as exc:
                # Fail fast on configuration/network outages rather than silently
                # producing dozens of pages of untranslated text.
                if isinstance(exc, requests.ConnectionError) and self.engine == "ollama":
                    raise RuntimeError("Cannot reach translation server. Start 'ollama serve' or check --api-url") from exc
                if isinstance(exc, requests.HTTPError) and getattr(exc.response, "status_code", None) in {401, 403, 404}:
                    raise RuntimeError(f"Translation service returned HTTP {exc.response.status_code}; check API credentials and model name") from exc
                if isinstance(exc, ValueError) and ("is not set" in str(exc) or "Argos" in str(exc)):
                    raise
                error = exc
                if attempt < self.retries:
                    time.sleep(min(2 ** attempt, 3))
        msg = f"Translation failed; kept original text unchanged: {error}"
        self.warnings.append(msg)
        warnings.warn(msg)
        return text


def translate_pages(pages, translator, progress=lambda _: None):
    in_references = False
    in_frontmatter = True
    for page in pages:
        for block in page.blocks:
            text = block.text
            heading = block.kind in {"heading", "title"}
            if heading and re.match(r"^\s*(?:\d+\.?\s*)?(?:references|bibliography)\s*$", text, re.I):
                in_references = True
            if re.search(r"\babstract\b", text, re.I):
                in_frontmatter = False
            # References and raw LaTeX/figures remain identical; author's name line
            # in the front-matter is conservatively skipped for short blocks.
            skip = in_references or block.kind in {"equation", "image", "table", "footnote"} and not text
            skip = skip or (in_frontmatter and page.number == 1 and block.kind == "paragraph"
                            and len(text.split()) < 10 and not re.search(r"\babstract\b", text, re.I))
            if block.kind == "markdown":
                # Docling Markdown pages: translate paragraph lines, protecting syntax-only lines.
                translated = []
                for section in re.split(r"(\n\s*\n)", text):
                    stripped = section.strip()
                    keep = (not stripped or stripped.startswith(("![](", "<", "|", "$$", "```"))
                            or set(stripped) <= set("|-: "))
                    translated.append(section if keep or in_references else translator.translate(section))
                block.translation = "".join(translated)
            elif block.kind == "table":
                # Each cell is translated independently, retaining row/column order.
                new_rows = []
                for row_index, row in enumerate(block.rows):
                    new_rows.append([translator.translate(cell, skip=(in_references or not cell.strip())) for cell in row])
                block.translation = json.dumps(new_rows, ensure_ascii=False)
            elif block.kind in {"title", "heading", "paragraph", "list", "quote", "footnote"}:
                block.translation = translator.translate(text, skip=in_references)
            else:
                block.translation = text
        progress(f"翻译完成：第 {page.number} 页")
    return pages
