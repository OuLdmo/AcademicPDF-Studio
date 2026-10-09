"""Local-only browser UI. No Flask or cloud services are required.

The HTTP service binds to 127.0.0.1 by default. File conversion runs in a
worker thread, while the browser polls a bounded status endpoint. The PDF
processor and translation engines are the same as the CLI, not a mock API.
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import threading
import urllib.request
import traceback
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .pipeline import process_pdf
from .engines import ENGINES, defaults
from .translate import Translator

MAX_UPLOAD_BYTES = 80 * 1024 * 1024
MAX_FILES = 12
WEB_VERSION = "0.4.1"
STATIC_DIR = Path(__file__).with_name("web_static")
LOG = logging.getLogger(__name__)


def default_data_dir() -> Path:
    override = os.environ.get("ACADEMICPDF_HOME")
    if override:
        return Path(override).expanduser().resolve()
    documents = Path.home() / "Documents"
    return (documents if documents.is_dir() else Path.home()) / "AcademicPDF-Studio-Output"


def _safe_filename(name: str) -> str:
    # The original document name is never used as a directory component.
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r'[^\w.()\-\u4e00-\u9fff ]', '_', name, flags=re.UNICODE)
    return (name.strip(". ") or "paper.pdf")[:120]


def parse_submission(content_type: str, body: bytes):
    """Parse a bounded multipart request without deprecated Python cgi."""
    if not content_type.lower().startswith("multipart/form-data;"):
        raise ValueError("请使用文件上传表单")
    raw = b"MIME-Version: 1.0\r\nContent-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + body
    msg = BytesParser(policy=default).parsebytes(raw)
    if not msg.is_multipart():
        raise ValueError("无法识别上传内容")
    uploads = []
    fields = {}
    for part in msg.iter_parts():
        field = part.get_param("name", header="content-disposition")
        if not field:
            continue
        blob = part.get_payload(decode=True) or b""
        if field == "files":
            name = _safe_filename(part.get_filename() or "paper.pdf")
            if not name.lower().endswith(".pdf"):
                raise ValueError(f"仅支持 PDF 文件：{name}")
            if b"%PDF-" not in blob[:1024]:
                raise ValueError(f"文件不是有效的 PDF：{name}")
            if not blob:
                raise ValueError(f"文件为空：{name}")
            uploads.append((name, blob))
            if len(uploads) > MAX_FILES:
                raise ValueError(f"单次最多上传 {MAX_FILES} 个 PDF")
        else:
            if len(blob) > 12000:
                raise ValueError("选项内容过长")
            fields[field] = blob.decode("utf-8", errors="replace")
    if not uploads:
        raise ValueError("请上传至少一个 PDF 文件")
    return uploads, fields


def _choices(fields: dict) -> dict:
    def enum(name, values, fallback):
        value = fields.get(name, fallback)
        if value not in values:
            raise ValueError(f"无效的选项 {name}: {value}")
        return value
    engine = enum("engine", set(ENGINES), "none")
    backend = enum("backend", {"fitz", "docling"}, "fitz")
    equation_ocr = enum("equation_ocr", {"off", "pix2tex"}, "off")
    mode = enum("mode", {"zh", "bilingual"}, "zh")
    layout = enum("pdf_layout", {"reflow", "overlay"}, "reflow")
    model = fields.get("model", "")[:128].strip() or defaults(engine)["model"]
    glossary_s = fields.get("glossary", "").strip()
    glossary = json.loads(glossary_s) if glossary_s else {}
    if not isinstance(glossary, dict) or len(glossary) > 300 or any(not isinstance(k, str) or not isinstance(v, str) for k, v in glossary.items()):
        raise ValueError("术语表需要 JSON 对象，例如 {\"ECG\":\"心电图\"}")
    return dict(engine=engine, backend=backend, equation_ocr=equation_ocr, mode=mode, pdf_layout=layout,
                model=model, url=fields.get("api_url", "").strip()[:512] or None,
                api_key=fields.get("api_key", "").strip()[:512] or None, glossary=glossary, vector_figures=fields.get("vector_figures") != "false",
                stitch_tables=fields.get("stitch_tables") != "false", snapshots=fields.get("snapshots") == "true")


class Job:
    def __init__(self, job_id: str, root: Path, entries, options: dict):
        self.id = job_id
        self.root = root
        self.entries = entries  # names/paths saved on disk, no PDF data in memory
        self.options = options
        self.status = "queued"
        self.percent = 0
        self.current = "等待空闲工作线程"
        self.logs = []
        self.error = None
        self.warnings = []
        self.reports = []
        self.zip_file = None
        self._lock = threading.RLock()

    def log(self, msg):
        with self._lock:
            s = str(msg)
            self.logs.append(s[:500])
            self.logs = self.logs[-90:]
            self.current = s[:230]

    def snapshot(self):
        with self._lock:
            finished = self.status in {"done", "warning", "error"}
            public_files = []
            for idx, entry in enumerate(self.entries):
                row = {"name": entry["name"], "pages": None, "urls": {}}
                if idx < len(self.reports):
                    report = self.reports[idx]
                    if report:
                        row["pages"] = report.get("pages")
                        row["urls"] = {k: f"/api/jobs/{self.id}/download?file={idx}&format={k}"
                                       for k, v in report.get("outputs", {}).items() if Path(v).is_file()}
                public_files.append(row)
            return {"id": self.id, "status": self.status, "progress": self.percent,
                    "current": self.current, "logs": self.logs.copy(), "error": self.error,
                    "files": public_files, "warnings": self.warnings[:30],
                    "zip_url": f"/api/jobs/{self.id}/zip" if finished and self.zip_file and self.zip_file.is_file() else None}


class Service:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.jobs = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="academicpdf")
        self.csrf = secrets.token_urlsafe(32)

    def submit(self, uploads, opts):
        job_id = secrets.token_hex(16)
        root = self.data_dir / job_id
        incoming = root / "input"
        incoming.mkdir(parents=True)
        entries = []
        for i, (name, content) in enumerate(uploads):
            path = incoming / f"{i+1:02d}_{name}"
            path.write_bytes(content)
            entries.append({"name": name, "path": path})
        job = Job(job_id, root, entries, opts)
        with self.lock:
            self.jobs[job_id] = job
        self.pool.submit(self._run, job)
        return job

    def get_job(self, job_id):
        with self.lock:
            return self.jobs.get(job_id)

    def _run(self, job):
        with job._lock:
            job.status = "running"
            job.percent = 1
        any_success = False
        try:
            for index, entry in enumerate(job.entries):
                with job._lock:
                    job.percent = max(job.percent, int(index / len(job.entries) * 90))
                job.log(f"开始处理 {index + 1}/{len(job.entries)}: {entry['name']}")
                def progress(message, fileidx=index):
                    job.log(message)
                    m = re.search(r"\[PAGE\s+(\d+)/(\d+)\]", message)
                    if m:
                        page, total = map(int, m.groups())
                        with job._lock:
                            job.percent = max(job.percent, int((fileidx + .50 * page / max(1, total)) / len(job.entries) * 95))
                    m = re.search(r"翻译完成：第\s*(\d+)\s*页", message)
                    if m:
                        # Translation progress is approximate: the source page count is unknown until manifest.
                        with job._lock:
                            job.percent = max(job.percent, int((fileidx + .60) / len(job.entries) * 95))
                try:
                    report = process_pdf(entry["path"], job.root / "output", **job.options,
                                         progress=progress, formats=("md", "pdf", "txt"))
                    any_success = True
                    with job._lock:
                        job.reports.append(report)
                        job.warnings += [f"{entry['name']}: {w}" for w in report.get("warnings", [])]
                except Exception as exc:
                    job.log(f"失败: {entry['name']}: {exc}")
                    with job._lock:
                        job.reports.append(None)
                        job.warnings.append(f"{entry['name']}: {type(exc).__name__}: {exc}")
                with job._lock:
                    job.percent = max(job.percent, int((index + 1) / len(job.entries) * 95))
            if any_success:
                zpath = job.root / "AcademicPDF-results.zip"
                with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                    for report in job.reports:
                        if not report:
                            continue
                        dest = Path(next(iter(report["outputs"].values()))).parent
                        for path in dest.rglob("*"):
                            if path.is_file() and ".cache" not in path.parts:
                                z.write(path, arcname=f"{dest.name}/{path.relative_to(dest).as_posix()}")
                with job._lock:
                    job.zip_file = zpath
            # Never retain credentials in completed jobs, logs or manifest files.
            job.options.pop("api_key", None)
            with job._lock:
                job.status = ("warning" if job.warnings else "done") if any_success else "error"
                job.error = "所有 PDF 均处理失败，请查看日志" if not any_success else None
                job.percent = 100
                job.current = "转换完成" if any_success else "转换失败"
        except Exception as exc:
            job.options.pop("api_key", None)
            LOG.exception("Unhandled job exception")
            with job._lock:
                job.status = "error"
                job.error = f"{type(exc).__name__}: {exc}"
                job.log(f"服务异常: {exc}")


class AcademicHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, service):
        self.service = service
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "AcademicPDF/0.4.1"

    def log_message(self, fmt, *args):
        LOG.info("%s %s", self.client_address[0], fmt % args)

    def _headers(self, code, content_type, length, *, attachment=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()

    def send_bytes(self, data, content_type="application/octet-stream", status=200, attachment=None):
        self._headers(status, content_type, len(data), attachment=attachment)
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, data, status=200):
        self.send_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def fail(self, status, message):
        self.send_json({"error": message}, status)

    def _route_job(self, path):
        match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})(?:/(zip|download|preview|assets))?", path)
        if not match:
            return None, None
        return self.server.service.get_job(match.group(1)), match.group(2) or "status"

    def _host_is_local(self):
        """Reject DNS rebinding hostnames on the default loopback listener."""
        if self.server.server_address[0] not in {"127.0.0.1", "localhost", "::1"}:
            return True
        host = self.headers.get("Host", "").lower().split(":")[0]
        return host in {"127.0.0.1", "localhost", "[::1]"}

    def do_GET(self):
        if not self._host_is_local():
            return self.fail(403, "不允许从非本机域名访问")
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/":
            b = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
            b = b.replace("__CSRF_TOKEN__", self.server.service.csrf)
            return self.send_bytes(b.encode("utf-8"), "text/html; charset=utf-8")
        if path in ("/static/style.css", "/static/app.js"):
            p = STATIC_DIR / Path(path).name
            ct = "text/css; charset=utf-8" if p.suffix == ".css" else "application/javascript; charset=utf-8"
            return self.send_bytes(p.read_bytes(), ct)
        if path == "/api/health":
            return self.send_json({"ok": True, "version": WEB_VERSION, "local_only": self.server.server_address[0] in {"127.0.0.1", "::1", "localhost"}})
        job, route = self._route_job(path)
        if not job:
            return self.fail(404, "未找到任务")
        if route == "status":
            return self.send_json(job.snapshot())
        params = parse_qs(parsed.query)
        if route == "zip":
            if not job.zip_file or not job.zip_file.is_file():
                return self.fail(404, "结果 ZIP 尚未生成")
            return self.send_bytes(job.zip_file.read_bytes(), "application/zip", attachment="AcademicPDF-results.zip")
        try:
            idx = int(params.get("file", ["0"])[0])
        except ValueError:
            return self.fail(400, "文件序号错误")
        with job._lock:
            if not 0 <= idx < len(job.reports) or job.reports[idx] is None:
                return self.fail(404, "文件结果不存在")
            report = job.reports[idx]
        outputs = report.get("outputs", {})
        if route in {"download", "preview"}:
            fmt = params.get("format", ["md"])[0] if route == "download" else "md"
            if fmt not in {"md", "txt", "pdf"} or fmt not in outputs:
                return self.fail(404, "输出格式不存在")
            file_path = Path(outputs[fmt]).resolve()
            if not file_path.is_file():
                return self.fail(404, "文件已被删除")
            if route == "preview":
                return self.send_bytes(file_path.read_bytes(), "text/plain; charset=utf-8")
            mime = {"md": "text/markdown; charset=utf-8", "pdf": "application/pdf", "txt": "text/plain; charset=utf-8"}[fmt]
            return self.send_bytes(file_path.read_bytes(), mime, attachment=f"paper-{idx+1}.{fmt}")
        if route == "assets":
            rel = params.get("path", [""])[0]
            folder = Path(next(iter(outputs.values()))).parent.resolve()
            desired = (folder / rel).resolve()
            # Only grant access to files in the generated assets directory.
            if not desired.is_relative_to(folder / "assets") or not desired.is_file():
                return self.fail(404, "资源文件不存在")
            mime = mimetypes.guess_type(desired.name)[0] or "application/octet-stream"
            if mime not in {"image/png", "image/jpeg", "image/webp", "image/svg+xml", "image/gif"}:
                return self.fail(415, "不支持的预览格式")
            return self.send_bytes(desired.read_bytes(), mime)
        self.fail(404, "未知接口")

    def do_POST(self):
        if not self._host_is_local():
            return self.fail(403, "不允许从非本机域名访问")
        if self.path not in {"/api/jobs", "/api/engines/test"}:
            return self.fail(404, "未知接口")
        if not secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), self.server.service.csrf):
            return self.fail(403, "安全校验失败，请刷新页面")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host', '')}":
            return self.fail(403, "不接受来自其他网站的请求")
        if self.path == "/api/engines/test":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n < 2 or n > 8192:
                    return self.fail(413, "配置内容过大或为空")
                obj = json.loads(self.rfile.read(n))
                if not isinstance(obj, dict):
                    raise ValueError("配置格式错误")
                engine = obj.get("engine", "none")
                if engine not in ENGINES:
                    raise ValueError("无效的翻译引擎")
                translator = Translator(engine, str(obj.get("model") or defaults(engine)["model"])[:128],
                    self.server.service.data_dir / ".engine-test-cache.json",
                    url=str(obj.get("api_url") or "")[:512] or None,
                    api_key=str(obj.get("api_key") or "")[:512], retries=0)
                sample = translator.test_connection()
                return self.send_json({"ok": True, "sample": sample})
            except Exception as exc:
                # Keep details useful without reflecting request values (such as API keys).
                from requests import RequestException
                if isinstance(exc, RequestException):
                    return self.fail(502, "翻译服务网络连接失败或服务器拒绝请求，请核对地址、密钥与模型")
                return self.fail(400, str(exc)[:240])
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if length <= 0 or length > MAX_UPLOAD_BYTES + 100000:
                return self.fail(413, "上传内容过大或为空（最多 80 MB）")
            uploads, fields = parse_submission(self.headers.get("Content-Type", ""), self.rfile.read(length))
            opts = _choices(fields)
            job = self.server.service.submit(uploads, opts)
            return self.send_json({"id": job.id, "status": job.status}, 201)
        except (ValueError, json.JSONDecodeError) as exc:
            return self.fail(400, str(exc))
        except Exception:
            LOG.exception("submit failed")
            return self.fail(500, "任务创建失败，请查看本地运行日志")


def create_server(*, host="127.0.0.1", port=8765, data_dir=None):
    if host not in {"127.0.0.1", "localhost", "::1"} and os.getenv("ACADEMICPDF_ALLOW_REMOTE") != "1":
        raise ValueError("Web UI defaults to local-only. Set ACADEMICPDF_ALLOW_REMOTE=1 explicitly to bind externally; add authentication and HTTPS first.")
    service = Service(Path(data_dir) if data_dir else default_data_dir())
    return AcademicHTTPServer((host, port), service)


def self_test() -> bool:
    """Offline smoke check for source launches AND built PyInstaller EXE."""
    for relative in ("index.html", "app.js", "style.css"):
        file_path = STATIC_DIR / relative
        if not file_path.is_file() or file_path.stat().st_size == 0:
            print(f"SELF-TEST FAIL: 缺少静态文件 {file_path}", flush=True)
            return False
    try:
        import pymupdf as fitz
        import reportlab
        import PIL
        import requests
        import tqdm
        assert fitz and reportlab and PIL and requests and tqdm
    except (ImportError, AssertionError) as exc:
        print(f"SELF-TEST FAIL: 必需依赖不可用：{exc}", flush=True)
        return False
    print(f"SELF-TEST OK: AcademicPDF {WEB_VERSION}, web_static={STATIC_DIR}", flush=True)
    return True


def _existing_local_server(host: str, port: int) -> bool:
    """Only reuse an existing AcademicPDF server on the default loopback host."""
    if host not in ("127.0.0.1", "localhost"):
        return False
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1.5) as reply:
            response = json.load(reply)
            return bool(response.get("ok") and str(response.get("version", "")) == WEB_VERSION)
    except (OSError, ValueError, TimeoutError):
        return False


def main(argv=None):
    p = argparse.ArgumentParser(description="AcademicPDF Studio local web app")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=None,
                   help="指定固定端口；不指定时优先使用 8765，冲突时自动尝试 8766-8774")
    p.add_argument("--data-dir", default=None)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--self-test", action="store_true", help="检查软件与静态文件是否齐全，然后退出")
    args = p.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 1
    logging.basicConfig(level=logging.WARNING)
    base_port = args.port if args.port is not None else 8765
    ports = [base_port] if args.port is not None else list(range(8765, 8775))
    server = None
    for port in ports:
        try:
            server = create_server(host=args.host, port=port, data_dir=args.data_dir)
            break
        except OSError as exc:
            if getattr(exc, "errno", None) not in (48, 98, 10048):
                print(f"[ERROR] 无法创建数据目录或启动服务：{exc}", flush=True)
                return 2
            if _existing_local_server(args.host, port):
                url = f"http://{args.host}:{port}/"
                print(f"AcademicPDF 已在运行，打开已有服务：{url}", flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
                return 0
            if args.port is not None:
                print(f"[ERROR] 端口 {port} 已被占用；请更换 --port 或关闭占用的程序。", flush=True)
                return 2
    if server is None:
        print("[ERROR] 8765-8774 端口均已占用，请通过 --port 指定空闲端口。", flush=True)
        return 2
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"AcademicPDF Studio {WEB_VERSION} | 本地网页: {url}", flush=True)
    print(f"输出目录: {server.service.data_dir}", flush=True)
    print("按 Ctrl+C 关闭服务。网页关闭不等于服务停止。", flush=True)
    if not args.no_browser:
        timer = threading.Timer(.7, lambda: webbrowser.open(url))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.service.pool.shutdown(wait=False, cancel_futures=True)
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
