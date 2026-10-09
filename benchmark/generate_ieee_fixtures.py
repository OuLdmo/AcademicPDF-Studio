"""Reproducible, rights-clear IEEE-like two-column evaluation fixtures.

These are not published IEEE manuscripts; they exercise typical IEEE geometry.
Gold labels are handcrafted at generation time and are not model predictions.
"""
import json
from pathlib import Path
import pymupdf as fitz

ROOT=Path(__file__).resolve().parent / 'fixtures'
W,H=612,792

def t(page,x,y,text,size=10,font='helv'):
    page.insert_text((x,y),text,fontsize=size,fontname=font)

def cols(page, tag='A', with_formula=False):
    t(page,50,52,'A Two-Column Study of Biosignal Transmission',17,'hebo')
    t(page,50,77,'Researcher A, Researcher B',10)
    t(page,50,123,'1. Introduction',12,'hebo')
    t(page,50,166, f'{tag} Left-first paragraph: adaptive ECG codecs.',10)
    t(page,50,192, f'{tag} Left-second paragraph: spectral regularity.',10)
    t(page,333,166,f'{tag} Right-first paragraph: telemetry system.',10)
    t(page,333,192,f'{tag} Right-second paragraph: streaming fusion.',10)
    if with_formula:
        t(page,135,320,'E = m c^2',13)
        t(page,50,340,'Eq. (1) energy equation.',9)

def table(page,y_start,labels,colwidths=(50,175,300,430,565)):
    xs=colwidths
    n=len(labels)
    ys=[y_start+24*i for i in range(n+1)]
    for x in xs:
        page.draw_line((x,ys[0]),(x,ys[-1]),color=(0,0,0),width=.65)
    for y in ys:
        page.draw_line((xs[0],y),(xs[-1],y),color=(0,0,0),width=.65)
    for ix,row in enumerate(labels):
        for j,cell in enumerate(row):
            t(page,xs[j]+5,y_start+17+24*ix,cell,9)

def chart(page):
    # Many line drawing commands -> cluster-based vector extraction.
    x0,y0=352,328
    for i in range(13):
        x=x0+i*14
        y=y0+55-int(25*__import__('math').sin(i/2.5))
        if i:
            page.draw_line((prevx,prevy),(x,y),color=(.05,.35,.65),width=1.8)
        prevx,prevy=x,y
    page.draw_line((x0,y0+95),(x0+168,y0+95),color=(0,0,0),width=1)
    page.draw_line((x0,y0+95),(x0,y0),color=(0,0,0),width=1)
    t(page,348,453,'Figure 1. Original vector ECG response.',9)

def write(name, doc, gold):
    path=ROOT/name
    doc.save(path)
    doc.close()
    (ROOT/(Path(name).stem+'.gold.json')).write_text(json.dumps(gold,indent=2,ensure_ascii=False),encoding='utf-8')

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    p=fitz.open();a=p.new_page(width=W,height=H); cols(a,'A')
    write('ieee_two_column.pdf',p,{'anchors':['A Left-first paragraph','A Left-second paragraph','A Right-first paragraph','A Right-second paragraph'],
          'headings':['A Two-Column Study of Biosignal Transmission','1. Introduction'],'tables':[], 'equations':[], 'figures':0})
    p=fitz.open();a=p.new_page(width=W,height=H);cols(a,'B')
    t(a,50,602,'Table 1. ECG error before and after normalization.',9)
    table(a,625,[['Signal','Baseline','Method','Metric'],['ECG100','DWT','Hybrid','PRD'],['ECG101','Delta','Adaptive','SNR'],['ECG102','RLE','Huffman','CR'],['ECG103','Wavelet','Entropy','MSE']])
    b=p.new_page(width=W,height=H)
    table(b,58,[['Signal','Baseline','Method','Metric'],['ECG104','DWT','Hybrid','PRD'],['ECG105','Delta','Adaptive','SNR']])
    t(b,50,330,'2. Quantitative Results',12,'hebo')
    t(b,50,370,'The evaluation uses consistent sample rates.',10)
    write('ieee_crosspage_table.pdf',p,{'anchors':['B Left-first paragraph','B Left-second paragraph','B Right-first paragraph','B Right-second paragraph'],
        'headings':['A Two-Column Study of Biosignal Transmission','1. Introduction','2. Quantitative Results'], 'tables':['ECG100','ECG105'], 'table_shape':[7,4],
        'equations':[],'figures':0,'expected_stitches':1})
    p=fitz.open();a=p.new_page(width=W,height=H);cols(a,'C',True);chart(a)
    write('ieee_vectors_equations.pdf',p,{'anchors':['C Left-first paragraph','C Left-second paragraph','C Right-first paragraph','C Right-second paragraph'],
        'headings':['A Two-Column Study of Biosignal Transmission','1. Introduction'], 'tables':[], 'equations':['E = m c^2'], 'figures':1})
    print('Generated 3 synthetic IEEE-style PDFs in',ROOT)

if __name__=='__main__':main()
