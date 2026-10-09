"""Independent structure fidelity and PDF appearance metrics.

Ground-truth labels should come from manually reviewed document annotations,
not from the parser being measured. SSIM reflects pixel changes, including
legitimate language changes, and must not be interpreted as translation quality.
"""
from pathlib import Path
import re
import numpy as np
import pymupdf as fitz
from PIL import Image, ImageFilter


def structure_metrics(markdown, gold):
    def norm(s):
        return re.sub(r'\s+', ' ', s).strip().lower()
    source_headings = [norm(s) for s in gold.get('headings', [])]
    predicted_headings = [norm(re.sub(r'^#{1,6}\s+', '', line)) for line in markdown.splitlines()
                          if re.match(r'^#{1,6}\s+', line)]
    # Gold headings are a subset of all document headings (e.g. title is also a heading).
    tp = sum(1 for label in source_headings if label in predicted_headings)
    heading_recall = tp / len(source_headings) if source_headings else None
    heading_precision = tp / len(predicted_headings) if predicted_headings else (1. if not source_headings else 0.)
    heading_f1 = ((2*heading_precision*heading_recall/(heading_precision+heading_recall))
                  if heading_recall is not None and (heading_precision+heading_recall)>0 else
                  (0. if heading_recall is not None else None))
    anchors = gold.get('anchors', [])
    positions = [markdown.find(a) for a in anchors]
    coverage = sum(p >= 0 for p in positions) / len(anchors) if anchors else None
    pairs = [(positions[i],positions[j]) for i in range(len(positions))
             for j in range(i+1,len(positions))]
    order_acc = sum(i>=0 and j>=0 and i<j for i,j in pairs) / len(pairs) if pairs else None
    table_terms = gold.get('tables', [])
    table_recall = sum(k in markdown for k in table_terms) / len(table_terms) if table_terms else None
    # Infer shape of first regular GFM table (header included, separator excluded).
    target_shape=gold.get('table_shape')
    table_shape_acc=None
    if target_shape:
        lines=markdown.splitlines()
        candidate=[]
        for line in lines:
            if line.startswith('| ') and line.endswith(' |'):
                if re.match(r'^\|(?:\s*[-:]+\s*\|)+$', line):
                    continue
                candidate.append(line)
        if candidate:
            col_count=max(0,len(candidate[0].split('|'))-2)
            table_shape_acc=1. if [len(candidate),col_count]==target_shape else 0.
        else:
            table_shape_acc=0.
    equations = gold.get('equations', [])
    eq_recall = sum(k in markdown for k in equations) / len(equations) if equations else None
    target_figs = gold.get('figures',0)
    figure_recall = min(1.,markdown.count('![PDF figure]')/target_figs) if target_figs else None
    scores = {'heading_precision':heading_precision, 'heading_recall':heading_recall,
              'heading_f1':heading_f1, 'anchor_coverage':coverage,
              'reading_order_pair_accuracy':order_acc, 'table_cell_recall':table_recall,
              'table_shape_accuracy':table_shape_acc,
              'equation_text_recall':eq_recall, 'figure_capture_recall':figure_recall}
    # Use a single heading term in the macro (F1), not precision and recall
    # separately, to avoid triple-counting this one component.
    valid=[scores[k] for k in ('heading_f1','anchor_coverage','reading_order_pair_accuracy',
        'table_cell_recall','table_shape_accuracy','equation_text_recall','figure_capture_recall')
        if scores.get(k) is not None]
    scores['macro_average_observed_tasks'] = sum(valid)/len(valid) if valid else None
    # Label coverage is NOT a full WER or formula OCR metric; deliberate naming.
    return scores


def _thumbnail(page, shape=(384,288)):
    p=page.get_pixmap(matrix=fitz.Matrix(1.25,1.25), colorspace=fitz.csGRAY,alpha=False)
    return np.asarray(Image.frombytes('L',[p.width,p.height],p.samples).resize(
        (shape[1],shape[0]),Image.Resampling.BILINEAR),dtype=np.float32)/255.


def pdf_visual_metrics(source, generated):
    from skimage.metrics import structural_similarity as ssim
    a=fitz.open(str(source));b=fitz.open(str(generated))
    try:
        n=min(a.page_count,b.page_count)
        results=[]
        for i in range(n):
            ia,ib=_thumbnail(a[i]),_thumbnail(b[i])
            raw_ssim=float(ssim(ia,ib,data_range=1.0))
            # Estimate coarse layout overlap, not word glyph agreement: blurred
            # foreground occupancy reduces sensitivity to legitimate CJK changes.
            ba=(ia<.90).astype('float32');bb=(ib<.90).astype('float32')
            def blur(x):
                im=Image.fromarray((x*255).astype('uint8'))
                return np.asarray(im.filter(ImageFilter.MaxFilter(11)),dtype=np.uint8)>0
            m1,m2=blur(ba),blur(bb)
            intersection=np.logical_and(m1,m2).sum()
            union=np.logical_or(m1,m2).sum()
            iou=float(intersection/union) if union else 1.
            results.append({'page':i+1,'ssim':round(raw_ssim,5),'layout_mask_iou':round(iou,5)})
        return {'source_pages':a.page_count,'generated_pages':b.page_count,
                'page_retention':n/max(1,a.page_count),
                'mean_ssim':round(sum(x['ssim'] for x in results)/n,5) if n else None,
                'mean_layout_mask_iou':round(sum(x['layout_mask_iou'] for x in results)/n,5) if n else None,
                'pages':results,
                'caveat':'SSIM changes with translated text; high similarity is not translation quality or proof of 1:1 fidelity.'}
    finally:
        a.close();b.close()
