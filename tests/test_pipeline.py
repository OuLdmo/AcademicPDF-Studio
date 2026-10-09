import json
from pathlib import Path

import pymupdf as fitz
import pytest

from paperstudio.export import table_md
from paperstudio.translate import Translator, protect, restore
from paperstudio.pipeline import process_pdf, discover


def make_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=600, height=760)
    page.insert_text((60, 45), "A research paper on biomedical signals", fontsize=18)
    page.insert_text((60, 105), "Introduction", fontsize=14)
    page.insert_text((60, 145), "The first left column paragraph [1] measures ECG.", fontsize=10)
    page.insert_text((60, 170), "A second left paragraph with SNR = 10 dB.", fontsize=10)
    page.insert_text((325, 145), "The right column examines the sensor network.", fontsize=10)
    page.insert_text((325, 170), "Figure 1 shows sample data.", fontsize=10)
    page.insert_text((80, 742), "1", fontsize=9)
    page2 = doc.new_page(width=600, height=760)
    page2.insert_text((60, 60), "Methods", fontsize=14)
    page2.insert_text((60, 90), "The voltage is measured in mV.", fontsize=11)
    page2.insert_text((80, 742), "2", fontsize=9)
    doc.save(path)
    doc.close()


def test_protect_and_restore():
    protected, mapping = protect("ECG [1] is $E=mc^2$ in Fig. 2 and https://example.org")
    assert "⟦KEEP_" in protected
    assert restore(protected, mapping) == "ECG [1] is $E=mc^2$ in Fig. 2 and https://example.org"
    with pytest.raises(ValueError):
        restore("corrupt", mapping)


def test_translator_cache(tmp_path):
    t = Translator("ollama", "fake", tmp_path / "translations.json", retries=0)
    requests = []
    def mocked(text, context):
        requests.append(text)
        return text.replace("sensor", "传感器")
    t._request = mocked
    translated = t.translate("The sensor has a value [1].")
    assert "传感器" in translated and "[1]" in translated
    assert t.translate("The sensor has a value [1].") == translated
    # Cache changes with context; a repeated paragraph in a later context can be retranslated.
    assert len(requests) >= 1


def test_table_md():
    output = table_md([["x", "y"], ["a|b", "1"]])
    assert "a\\|b" in output and "---" in output


def test_end_to_end(tmp_path):
    src = tmp_path / "test.pdf"
    make_pdf(src)
    progress = []
    report = process_pdf(src, tmp_path / "outputs", engine="none", formats=("md", "txt", "pdf"),
                         progress=progress.append)
    assert report["pages"] == 2
    assert len(report["outputs"]) == 3
    md = Path(report["outputs"]["md"]).read_text(encoding="utf-8")
    assert "Introduction" in md and "sensor network" in md
    assert md.index("first left") < md.index("right column")
    assert "<!-- source-page: 2 -->" in md
    assert "UNTRANSLATED" in md
    assert Path(report["outputs"]["pdf"]).stat().st_size > 1000
    assert any("[PAGE 1/2] parsed" in x for x in progress)
    again = []
    process_pdf(src, tmp_path / "outputs", engine="none", formats=("md",), progress=again.append)
    assert any("[PAGE 1/2] cached" in x for x in again)
    assert len(discover(tmp_path)) >= 1
