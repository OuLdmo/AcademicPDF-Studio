import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf as fitz

from paperstudio.schema import Block,Page
from paperstudio.export import block_md
from paperstudio.tables import stitch_across_pages
from paperstudio.equations import EquationOCR
from paperstudio.quality import structure_metrics,pdf_visual_metrics
from paperstudio.overlay import render_overlay
from paperstudio.parser import parse_fitz_page


def test_merged_cell_html():
    b=Block('table',rows=[['Head',''],['ECG','4']],spans=[[0,0,1,2]])
    out=block_md(b)
    assert '<th colspan="2">Head</th>' in out
    assert '><section' not in out


def test_stitch_with_repeated_header():
    p1=Page(1,600,800,[Block('table',rows=[['X','Y'],['A','1']],bbox=[50,605,560,780])])
    p2=Page(2,600,800,[Block('table',rows=[['X','Y'],['B','2']],bbox=[50,40,560,145])])
    merges=stitch_across_pages([p1,p2])
    assert merges and merges[0]['repeated_header']
    assert p1.blocks[0].rows == [['X','Y'],['A','1'],['B','2']]
    assert p2.blocks==[]


def test_do_not_merge_mismatched_columns():
    p1=Page(1,600,800,[Block('table',rows=[['X','Y'],['A','1']],bbox=[50,605,560,780])])
    p2=Page(2,600,800,[Block('table',rows=[['X','Y','Z'],['B','2','3']],bbox=[50,40,560,145])])
    assert stitch_across_pages([p1,p2])==[]


def test_optional_equation_ocr_with_local_fake(tmp_path):
    doc=fitz.open();p=doc.new_page(width=600,height=800)
    p.insert_text((130,220),'E = m c^2',fontsize=12)
    recognizer=EquationOCR('off')
    assert recognizer.recognize(p,(100,200,310,240),tmp_path,'eq1')==('','')
    class FakeModel:
        def __call__(self,img):
            return r'E = mc^{2}'
    recognizer=EquationOCR('pix2tex')
    recognizer.model=FakeModel()
    latex,crop=recognizer.recognize(p,(100,200,310,240),tmp_path,'eq2')
    assert latex == r'E = mc^{2}'
    assert (tmp_path/Path(crop).name).exists()
    assert block_md(Block('equation',text='E = m c^2', latex=latex)).startswith('$$')
    doc.close()


def test_vector_svg_crop_and_pdf_visual(tmp_path):
    doc=fitz.open();p=doc.new_page(width=612,height=792)
    for i in range(12):
        p.draw_line((100+i*12,100+i*3),(112+i*12,150+i*2),color=(1,0,0))
    p.insert_text((40,45),'A Test Header',fontsize=19)
    src=tmp_path/'source.pdf';doc.save(src);doc.close()
    with fitz.open(src) as d:
        parsed=parse_fitz_page(d,0,tmp_path/'assets')
    figures=[b for b in parsed.blocks if b.vector_svg]
    assert figures
    xml=ET.parse(tmp_path/figures[0].vector_svg).getroot()
    assert xml.attrib['viewBox']
    with fitz.open(src) as d:
        p=Page(1,612,792,[Block('paragraph',text='A Test Header',translation='中文标题',bbox=[40,24,220,50],size=19)])
    out=tmp_path/'translated.pdf'
    issues=render_overlay(src,[p],out)
    scores=pdf_visual_metrics(src,out)
    assert out.is_file() and scores['mean_ssim']<1.0
    assert scores['generated_pages']==1


def test_manual_gold_metrics():
    gold={'headings':['Paper','1. Introduction'],'anchors':['Left-one','Left-two','Right-one'],
          'tables':['ECG100'],'equations':['E = mc^2'],'figures':1}
    md='# Paper\n\n## 1. Introduction\n\nLeft-one Left-two Right-one\n\n| ECG100 |\n\nE = mc^2\n\n![PDF figure](assets/x.png)'
    m=structure_metrics(md,gold)
    assert m['macro_average_observed_tasks']==1.
