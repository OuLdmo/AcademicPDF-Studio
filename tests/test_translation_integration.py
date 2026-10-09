"""Integration test using a local mock of Ollama; never calls external services."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pymupdf as fitz

from paperstudio.pipeline import process_pdf


class LocalOllamaMock(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers["Content-Length"])
        content = json.loads(self.rfile.read(size))
        original = content["messages"][-1]["content"].split("Text:\n", 1)[-1]
        translated = original.replace("The signal", "信号").replace("is sampled", "采样").replace("We measure", "我们测量")
        body = json.dumps({"message": {"content": translated}}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass


def test_ollama_http_and_chinese_pdf(tmp_path):
    pdf = tmp_path / "signals.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((40, 70), "The signal is sampled at 360 Hz [1].", fontsize=12)
    p.insert_text((40, 120), "We measure voltage in mV.", fontsize=12)
    doc.save(pdf)
    doc.close()
    http = HTTPServer(("127.0.0.1", 0), LocalOllamaMock)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        report = process_pdf(pdf, tmp_path / "out", engine="ollama", model="mock",
            url=f"http://127.0.0.1:{http.server_port}", mode="bilingual",
            formats=("md", "txt", "pdf"), progress=lambda _: None)
        assert report["warnings"] == []
        translated = Path(report["outputs"]["md"]).read_text(encoding="utf-8")
        assert "信号" in translated and "[1]" in translated
        assert "> The signal is sampled" in translated
        out_pdf = fitz.open(report["outputs"]["pdf"])
        assert out_pdf.page_count >= 1
        assert Path(report["outputs"]["txt"]).exists()
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=3)
