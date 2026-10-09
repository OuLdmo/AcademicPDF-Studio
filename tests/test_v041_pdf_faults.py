"""Fault-injection and regression checks, not a claim of real-PDF benchmark accuracy."""
import json
from pathlib import Path

import pymupdf as fitz
import pytest

import paperstudio.parser as parser
import paperstudio.pipeline as pipeline
from paperstudio import pdf_health
from paperstudio.schema import Page, Block
from paperstudio.web import WEB_VERSION, _existing_local_server


def sample_pdf(path, pages=2):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=612, height=792)
        page.insert_text((48, 52), f'Title {i+1}', fontsize=16)
        page.insert_text((48, 102), f'Biomarkers from ECG on page {i+1}.', fontsize=11)
        page.insert_text((320, 102), f'PPG sensor data on page {i+1}.', fontsize=11)
    doc.save(path)
    doc.close()


def test_real_sample_pipeline_no_fitz_deprecation(tmp_path):
    src = tmp_path / '双栏 文献 & 特殊路径.pdf'
    sample_pdf(src, 3)
    report = pipeline.process_pdf(src, tmp_path/'中文 输出 & 空格', engine='none', progress=lambda _: None)
    assert report['pages'] == 3
    assert report['diagnostics'] == []
    assert report['needs_review'] is False
    for target in report['outputs'].values():
        assert Path(target).is_file()
    with fitz.open(report['outputs']['pdf']) as f:
        assert f.page_count > 0
    text = Path(report['outputs']['md']).read_text(encoding='utf-8')
    assert 'Biomarkers from ECG' in text
    assert 'PPG sensor data' in text


def test_mupdf_diagnostic_capture_counts_without_spamming(monkeypatch):
    class FakeTools:
        def __init__(self):
            self.pending = ''
            self.display_errors = True
        def reset_mupdf_warnings(self):
            self.pending = ''
        def mupdf_display_errors(self, value):
            self.display_errors = value
        def mupdf_display_warnings(self, value):
            pass
        def mupdf_warnings(self, reset=True):
            s = self.pending
            if reset:
                self.pending = ''
            return s
    mock = FakeTools()
    monkeypatch.setattr(pdf_health.pymupdf, 'TOOLS', mock)
    pdf_health.configure_mupdf()
    assert mock.display_errors is False
    issues = []
    def broken_but_recovers():
        mock.pending = ('syntax error: too many sub-functions in stitching function\n'*19)
        return {'blocks': [1]}
    got = pdf_health.guarded_pdf_call('page parse', 4, issues, broken_but_recovers)
    assert got['blocks'] == [1]
    assert len(issues) == 1
    assert issues[0]['count'] == 19
    assert 'stitching function' in issues[0]['message']
    assert pdf_health.risky_graphics(issues)
    assert any('19 occurrence(s)' in s for s in pdf_health.concise_diagnostics(issues))


def test_page_failure_keeps_following_pages_and_flags(tmp_path, monkeypatch):
    src=tmp_path/'fault.pdf'; sample_pdf(src, 3)
    parse_real = pipeline.parse_fitz_page
    calls=[]
    def injected(doc, i, *args, **kwargs):
        if i == 1:
            calls.append('failed page')
            raise RuntimeError('injected structured parser failure')
        return parse_real(doc,i,*args,**kwargs)
    monkeypatch.setattr(pipeline, 'parse_fitz_page', injected)
    logs=[]
    report=pipeline.process_pdf(src,tmp_path/'out',engine='none',progress=logs.append)
    assert calls == ['failed page']
    assert report['pages'] == 3
    assert report['needs_review']
    assert any(d['page']==2 and d['severity']=='exception' for d in report['diagnostics'])
    md=Path(report['outputs']['md']).read_text(encoding='utf-8')
    assert '<!-- source-page: 3 -->' in md
    assert 'page 3' in md
    assert any('failed; retained page marker' in log for log in logs)
    # The failed page may not enter the persistent cache.
    assert not list((Path(report['outputs']['md']).parent/'.cache/pages').glob('0002_*.json'))


def test_text_structured_failure_falls_back_and_reports(tmp_path, monkeypatch):
    src=tmp_path/'fallback.pdf'; sample_pdf(src,1)
    original=parser.guarded_pdf_call
    def fake(stage, number, issues, fn, **kw):
        if stage=='structured text':
            issues.append(dict(stage=stage,page=number,severity='exception',message='failed',count=1))
            return None
        return original(stage,number,issues,fn,**kw)
    monkeypatch.setattr(parser, 'guarded_pdf_call', fake)
    report=pipeline.process_pdf(src,tmp_path/'out',engine='none',formats=('md',), progress=lambda _:None)
    assert report['needs_review']
    assert any('plain text retained' in d['message'] for d in report['diagnostics'])
    assert 'Biomarkers from ECG' in Path(report['outputs']['md']).read_text(encoding='utf-8')
    assert not list((Path(report['outputs']['md']).parent/'.cache/pages').glob('0001_*.json'))


def test_pdf_function_risky_skips_vector_and_snapshot(tmp_path, monkeypatch):
    src=tmp_path/'drawings.pdf';sample_pdf(src,1)
    original=parser.guarded_pdf_call
    def fake(stage, number, issues, fn, **kw):
        result=original(stage,number,issues,fn,**kw)
        if stage=='structured text':
            issues.append(dict(stage=stage,page=number,severity='mupdf',
                message='syntax error: too many sub-functions in stitching function',count=12))
        return result
    monkeypatch.setattr(parser,'guarded_pdf_call',fake)
    result=pipeline.process_pdf(src,tmp_path/'out',engine='none',snapshots=True,progress=lambda _:None)
    assert any(d['stage']=='vector extraction' and d['severity']=='skipped' for d in result['diagnostics'])
    assert any(d['stage']=='page snapshot' and d['severity']=='skipped' for d in result['diagnostics'])
    assert result['needs_review']
    assert 'ECG' in Path(result['outputs']['md']).read_text(encoding='utf-8')


def test_encrypted_pdf_rejected_clearly(tmp_path):
    src=tmp_path/'locked.pdf'
    with fitz.open() as d:
        d.new_page().insert_text((50,60),'secret')
        d.save(src, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='user')
    with pytest.raises(ValueError,match='password-protected'):
        pipeline.process_pdf(src,tmp_path/'out',engine='none',progress=lambda _:None)


def test_corrupted_non_pdf_not_report_success(tmp_path):
    src=tmp_path/'fake.pdf';src.write_bytes(b'%PDF-1.7\nTruncated...')
    with pytest.raises(Exception):
        pipeline.process_pdf(src,tmp_path/'out',engine='none',progress=lambda _:None)


def test_web_version_smoke_and_windows_imports():
    assert WEB_VERSION == '0.4.1'
    from tools.windows_bootstrap import RUNTIME_MODULES
    assert 'pymupdf' in RUNTIME_MODULES
    assert 'fitz' not in RUNTIME_MODULES


def test_high_cardinality_pdf_function_fixture_is_handled(tmp_path):
    """Large stitching function graph: model may or may not warn by MuPDF version."""
    fixture = Path(__file__).with_name('fixtures') / 'malformed_stitching_1200.pdf'
    assert fixture.exists()
    result = pipeline.process_pdf(fixture, tmp_path/'results', engine='none',
                                  snapshots=True, progress=lambda _: None)
    assert result['pages'] == 1
    text = Path(result['outputs']['md']).read_text(encoding='utf-8')
    assert 'Left column paragraph' in text
    assert 'Right column paragraph' in text
    assert Path(result['outputs']['pdf']).stat().st_size > 1000


def test_overlay_does_not_redact_whole_page_for_fallback_text(tmp_path):
    from paperstudio.overlay import render_overlay
    original = tmp_path / 'source.pdf'
    sample_pdf(original, 1)
    # No geometry: even if a translation exists, original content must remain.
    text = Block('paragraph', 'Biomarkers from ECG', translation='心电信号生物标志物', bbox=[])
    dest = tmp_path / 'overlay.pdf'
    problems = render_overlay(original, [Page(1, 612, 792, [text])], dest)
    assert any(p['issue'].startswith('overlay_missing_geometry') for p in problems)
    with fitz.open(dest) as doc:
        assert 'Biomarkers from ECG' in doc[0].get_text()


def test_two_concurrent_documents_have_separate_diagnostics(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    files = []
    for i in range(2):
        p = tmp_path / f'parallel_{i}.pdf'
        sample_pdf(p, 2)
        files.append(p)
    def process(p):
        return pipeline.process_pdf(p, tmp_path/'outputs', engine='none',
                                    formats=('md',), progress=lambda _: None)
    with ThreadPoolExecutor(max_workers=2) as executor:
        r1, r2 = list(executor.map(process, files))
    assert r1['diagnostics'] == [] and r2['diagnostics'] == []
    assert r1['source'] != r2['source']
    assert Path(r1['outputs']['md']).exists() and Path(r2['outputs']['md']).exists()
