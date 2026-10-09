"""Run reproducible IEEE-style synthetic fixtures with audited metrics.

Usage: python benchmark/run_benchmark.py
Not a benchmark of pix2tex accuracy, real IEEE data or translation quality.
"""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from paperstudio.pipeline import process_pdf
from paperstudio.quality import structure_metrics,pdf_visual_metrics
from paperstudio.parser import parse_fitz_page,recurrent_margins
from paperstudio.overlay import render_overlay
import pymupdf as fitz


def run():
    from generate_ieee_fixtures import main as generate
    generate()
    out=ROOT/'results'
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for pdf in sorted((ROOT/'fixtures').glob('*.pdf')):
        gold=json.loads(pdf.with_suffix('.gold.json').read_text(encoding='utf-8'))
        original=process_pdf(pdf,out,engine='none',formats=('md','pdf'),pdf_layout='overlay',
                             progress=lambda _:None,force=True)
        md=Path(original['outputs']['md']).read_text(encoding='utf-8')
        scores=structure_metrics(md,gold)
        identity_visual=pdf_visual_metrics(pdf,original['outputs']['pdf'])
        # Geometry regression with deterministic mocked Chinese *replacement*.
        # Not a translation-accuracy test, no cloud model or API involved.
        with fitz.open(pdf) as doc:
            pages=[parse_fitz_page(doc,i,out/'_mock_assets',recurrent_margins(doc))
                   for i in range(doc.page_count)]
        for page in pages:
            for block in page.blocks:
                if block.kind in {'paragraph','heading','list','quote'} and len(block.text)>22:
                    block.translation='本研究分析了多模态信号处理与远程传输的关键结果。'
        sim_path=out / (pdf.stem+'_mock_zh_overlay.pdf')
        problems=render_overlay(pdf,pages,sim_path)
        visual=pdf_visual_metrics(pdf,sim_path)
        result={'fixture':pdf.name,'kind':'synthetic_IEEE_like', 'pages':original['pages'],
                'markdown_structure':scores, 'table_stitches':original['table_stitches'],
                'overlay_identity':identity_visual,
                'overlay_mock_chinese':visual,
                'mock_chinese_overflow_blocks':len(problems),
                'note':'Mock Chinese text tests re-layout mechanics only, not actual translation or formula OCR.'}
        rows.append(result)
        print(pdf.name, 'structure', scores['macro_average_observed_tasks'],
              'mock_SSIM',visual['mean_ssim'],'mock_maskIoU',visual['mean_layout_mask_iou'],
              'overflows',len(problems))
    (out/'benchmark_report.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'benchmark_summary.md').open('w',encoding='utf-8') as f:
        f.write('# IEEE-like synthetic benchmark results\n\n')
        f.write('**Limitations:** All three fixtures are generated, not real IEEE publications; formula OCR was not benchmarked. '
                'The mock Chinese does not measure translation quality. Each reported score uses only annotated observable tasks.\n\n')
        f.write('| Fixture | MD observed-task macro | Header F1 | Reading-order pairs | Table cell recall | Figure recall | Mock overlay SSIM | Coarse layout IoU | Overflow blocks |\n')
        f.write('|---|---:|---:|---:|---:|---:|---:|---:|---:|\n')
        for x in rows:
            m=x['markdown_structure']; v=x['overlay_mock_chinese']
            fmt=lambda z:('N/A' if z is None else f'{z:.3f}')
            f.write(f"| {x['fixture']} | {fmt(m['macro_average_observed_tasks'])} | {fmt(m['heading_f1'])} | {fmt(m['reading_order_pair_accuracy'])} | {fmt(m['table_cell_recall'])} | {fmt(m['figure_capture_recall'])} | {fmt(v['mean_ssim'])} | {fmt(v['mean_layout_mask_iou'])} | {x['mock_chinese_overflow_blocks']} |\n")
        f.write('\nDo not interpret high macro values as structural correctness on arbitrary real IEEE manuscripts.\n')
    return rows

if __name__=='__main__':run()
