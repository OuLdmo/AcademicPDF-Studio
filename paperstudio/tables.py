"""Conservative boundary table continuation stitching.

Avoid ungrounded merges by checking dimensions, page edge positions and column
count. Tables with inconsistent shapes remain separate for human review.
"""
import re


def _norm(cell):
    return re.sub(r'\W+', '', (cell or '').lower())


def stitch_across_pages(pages, bottom=.76, top=.29):
    merged = []
    for a, b in zip(pages, pages[1:]):
        left_tables = [block for block in a.blocks if block.kind == 'table' and block.bbox]
        right_tables = [block for block in b.blocks if block.kind == 'table' and block.bbox]
        if not left_tables or not right_tables:
            continue
        x = max(left_tables, key=lambda t: t.bbox[3])
        y = min(right_tables, key=lambda t: t.bbox[1])
        if x.bbox[3] < bottom * a.height or y.bbox[1] > top * b.height:
            continue
        if not x.rows or not y.rows:
            continue
        columns = max(map(len, x.rows))
        if columns < 2 or max(map(len, y.rows)) != columns:
            continue
        # Only align tables in a similar horizontal lane (two-column included).
        width = max(x.bbox[2] - x.bbox[0], y.bbox[2] - y.bbox[0])
        if abs(x.bbox[0] - y.bbox[0]) > max(18, .16 * width):
            continue
        # Pages should have no non-table body text after/before the tables in
        # the same column. Footnotes and captions are permitted.
        def obstructed(page, table, after):
            cx = (table.bbox[0] + table.bbox[2]) / 2
            for item in page.blocks:
                if item is table or item.kind in {'image','footnote'} or not item.bbox:
                    continue
                icx = (item.bbox[0] + item.bbox[2]) / 2
                if abs(icx - cx) > width * .58:
                    continue
                if item.kind == 'paragraph' and len(item.text) > 35:
                    if after and item.bbox[1] >= table.bbox[3] + 5:
                        return True
                    if not after and item.bbox[3] <= table.bbox[1] - 5:
                        return True
            return False
        if obstructed(a,x,True) or obstructed(b,y,False):
            continue
        rows = list(y.rows)
        repeated_header = (len(rows)>0 and len(x.rows)>0 and
                           [_norm(t) for t in rows[0]] == [_norm(t) for t in x.rows[0]])
        if repeated_header:
            rows.pop(0)
        if not rows:
            continue
        initial_len=len(x.rows)
        for row,col,rs,cs in y.spans:
            if repeated_header and row == 0:
                continue
            x.spans.append([initial_len + row - (1 if repeated_header else 0),col,rs,cs])
        x.rows.extend(rows)
        x.table_pages = sorted(set((x.table_pages or [a.number]) + [b.number]))
        y.review.append(f'Continued into table on page {a.number}')
        b.blocks.remove(y)
        merged.append({'from':a.number,'to':b.number,'rows_added':len(rows),'repeated_header':repeated_header})
    return merged
