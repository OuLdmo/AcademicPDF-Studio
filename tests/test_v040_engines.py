"""End-to-end engine configuration without external/paid API calls."""
import io
import json
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from paperstudio.engines import ENGINES, defaults
from paperstudio.translate import Translator
from paperstudio.web import create_server
from test_web import multipart
from tools import windows_bootstrap as wb


class FakePaidChat(BaseHTTPRequestHandler):
    history = []
    def do_POST(self):
        n = int(self.headers['Content-Length'])
        request = json.loads(self.rfile.read(n))
        type(self).history.append((self.path, self.headers.get('Authorization'), request['model']))
        source = request['messages'][-1]['content'].split('Text:\n')[-1]
        result = source.replace('Hello world.', '你好，世界。').replace('The signal', '信号').replace('We measure', '我们测量')
        body = json.dumps({'choices':[{'message':{'content':result}}]}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args):
        pass


def serve_fake():
    FakePaidChat.history = []
    server = HTTPServer(('127.0.0.1', 0), FakePaidChat)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    return server, thread


def test_deepseek_api_fingerprint_and_no_key_leak(tmp_path):
    server, thread = serve_fake()
    try:
        t = Translator('deepseek', 'deepseek-flash', tmp_path / 'translations.json',
                       url=f'http://127.0.0.1:{server.server_port}', api_key='SECRET-DEMO', retries=0)
        assert t.translate('The signal is here [1]') == '信号 is here [1]'
        assert FakePaidChat.history[0] == ('/chat/completions', 'Bearer SECRET-DEMO', 'deepseek-flash')
        assert 'SECRET-DEMO' not in (tmp_path / 'translations.json').read_text(encoding='utf-8')
    finally:
        server.shutdown();server.server_close();thread.join(3)


def test_libretranslate_json_request(monkeypatch, tmp_path):
    import paperstudio.translate as module
    calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'translatedText':'心电图'}
    def fake_post(url,**kw):
        calls.append((url,kw))
        return Response()
    monkeypatch.setattr(module.requests,'post',fake_post)
    t=Translator('libretranslate','',tmp_path / 'x.json',url='http://127.0.0.1:5000',retries=0)
    assert t.test_connection() == '心电图'
    assert calls[0][0].endswith('/translate')
    assert calls[0][1]['json']['target']=='zh'


def test_argos_offline_mock(monkeypatch,tmp_path):
    import sys, types
    package = types.ModuleType('argostranslate')
    translate = types.ModuleType('argostranslate.translate')
    translate.translate=lambda content,src,dst: '离线成功'
    package.translate=translate
    monkeypatch.setitem(sys.modules,'argostranslate',package)
    monkeypatch.setitem(sys.modules,'argostranslate.translate',translate)
    t=Translator('argos','',tmp_path / 'x.json', retries=0)
    assert t.test_connection()=='离线成功'


def test_windows_build_installs_numpy_skimage_even_if_old_basics_present(monkeypatch):
    commands=[]
    monkeypatch.setattr(wb,'execute',lambda cmd,**kw: commands.append(cmd) or 0)
    monkeypatch.setattr(wb,'modules_present',lambda py,mods: True)
    wb.install_requirements(Path('fake-python'),build=True)
    assert commands
    assert 'requirements-build.txt' in ' '.join(map(str,commands[0]))
    content=(wb.ROOT/'requirements-build.txt').read_text()
    assert 'numpy' in content and 'scikit-image' in content


def test_web_test_engine_and_configured_pdf_translation(tmp_path):
    fake, fthread = serve_fake()
    web=create_server(port=0,data_dir=tmp_path)
    thread=threading.Thread(target=web.serve_forever,daemon=True)
    thread.start()
    base=f'http://127.0.0.1:{web.server_address[1]}'
    endpoint=f'http://127.0.0.1:{fake.server_port}'
    try:
        def request(path, payload, content_type):
            return urllib.request.urlopen(urllib.request.Request(base+path,data=payload,
                headers={'Content-Type':content_type,'X-CSRF-Token':web.service.csrf}),timeout=12)
        conf={'engine':'deepseek','model':'deepseek-flash','api_url':endpoint,'api_key':'SECRET-WEB'}
        with request('/api/engines/test',json.dumps(conf).encode(),'application/json') as r:
            assert json.load(r)['sample']=='你好，世界。'
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(urllib.request.Request(base+'/api/engines/test',data=b'{}',
                headers={'Content-Type':'application/json'}),timeout=10)
        assert exc.value.code==403
        pdf=Path(__file__).resolve().parents[1]/'examples'/'demo_paper.pdf'
        data,ct=multipart({**conf,'mode':'zh','vector_figures':'false'}, [('demo_paper.pdf',pdf.read_bytes())])
        with request('/api/jobs',data,ct) as r: jid=json.load(r)['id']
        for _ in range(90):
            with urllib.request.urlopen(base+'/api/jobs/'+jid,timeout=5) as r: state=json.load(r)
            if state['status'] in {'done','warning','error'}:break
            time.sleep(.2)
        assert state['status'] in {'done','warning'},state
        with urllib.request.urlopen(base+'/api/jobs/'+jid+'/preview?file=0') as r:
            md=r.read().decode('utf-8')
        assert '信号' in md or '我们测量' in md
        assert 'SECRET-WEB' not in json.dumps(state)
        with urllib.request.urlopen(base+state['zip_url']) as r: data=r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert all('SECRET-WEB' not in z.read(n).decode('utf-8','ignore') for n in z.namelist() if n.endswith(('.json','.md','.txt')))
    finally:
        web.shutdown();web.service.pool.shutdown(wait=True);web.server_close();thread.join(2)
        fake.shutdown();fake.server_close();fthread.join(2)
