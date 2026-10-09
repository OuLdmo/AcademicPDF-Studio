"""Stdlib HTTP integration tests: real PDFs, zero external translation calls."""
import io
import json
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest

from paperstudio.web import _choices, _safe_filename, create_server, parse_submission


def multipart(fields, files, boundary='test-boundary-001'):
    body = bytearray()
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for name, content in files:
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
        body += content + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    return bytes(body), f'multipart/form-data; boundary={boundary}'


def test_upload_parser_handles_unicode_and_rejects_nonpdf():
    raw, content_type = multipart({'engine': 'none'}, [('demo_中文.pdf', b'%PDF-1.4\nwhatever')])
    up, fields = parse_submission(content_type, raw)
    assert up[0][0] == 'demo_中文.pdf'
    assert fields['engine'] == 'none'
    with pytest.raises(ValueError):
        parse_submission(content_type, multipart({}, [('malicious.pdf', b'something bad')])[0])
    assert _safe_filename('../../etc/passwd.pdf') == 'passwd.pdf'
    assert _choices({'engine': 'none'})['engine'] == 'none'
    with pytest.raises(ValueError):
        _choices({'engine': 'evil'})


def test_server_end_to_end_upload_preview_zip(tmp_path):
    server = create_server(port=0, data_dir=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = f'http://127.0.0.1:{server.server_address[1]}'

    def http(path, headers=None):
        return urllib.request.urlopen(urllib.request.Request(root + path, headers=headers or {}), timeout=35)

    try:
        with http('/') as r:
            html = r.read().decode()
            assert 'AcademicPDF' in html
            assert server.service.csrf in html
            assert r.headers.get('Content-Security-Policy')
        with http('/api/health') as r:
            assert json.load(r)['ok'] is True
        source = Path(__file__).resolve().parents[1] / 'examples' / 'demo_paper.pdf'
        assert source.is_file()
        body, content_type = multipart(
            {'engine': 'none', 'backend': 'fitz', 'mode': 'bilingual', 'pdf_layout': 'reflow',
             'vector_figures': 'false', 'stitch_tables': 'true', 'snapshots': 'false'},
            [('demo_paper.pdf', source.read_bytes())])
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(urllib.request.Request(root + '/api/jobs', data=body,
                headers={'Content-Type': content_type}), timeout=10)
        assert e.value.code == 403
        with urllib.request.urlopen(urllib.request.Request(root + '/api/jobs', data=body,
            headers={'Content-Type': content_type, 'X-CSRF-Token': server.service.csrf}), timeout=15) as r:
            payload = json.load(r)
        jid = payload['id']
        for _ in range(120):
            with http('/api/jobs/' + jid) as r:
                status = json.load(r)
            if status['status'] in {'done', 'warning', 'error'}:
                break
            time.sleep(.25)
        assert status['status'] == 'done', status
        assert status['progress'] == 100
        assert status['files'][0]['urls']['md'].endswith('format=md')
        with http(f'/api/jobs/{jid}/preview?file=0') as r:
            md = r.read().decode('utf-8')
        assert len(md) > 100
        assert 'UNTRANSLATED' in md or 'untranslated' in md.lower()
        with http(status['files'][0]['urls']['md']) as r:
            assert len(r.read()) > 100
        with http(status['files'][0]['urls']['pdf']) as r:
            assert r.read(5) == b'%PDF-'
        with http(status['zip_url']) as r:
            zbytes = r.read()
        with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
            names = z.namelist()
            assert any(n.endswith('.md') for n in names)
            assert any(n.endswith('.pdf') for n in names)
            assert any(n.endswith('manifest.json') for n in names)
            assert not any('/.cache/' in n for n in names)
        with pytest.raises(urllib.error.HTTPError) as e:
            http(f'/api/jobs/{jid}/assets?file=0&path=../manifest.json')
        assert e.value.code == 404
    finally:
        server.shutdown()
        server.service.pool.shutdown(wait=True)
        server.server_close()
        thread.join(timeout=2)
