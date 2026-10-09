# Architecture / 技术架构简述

```text
PDF source
  -> page-level PyMuPDF parser (optional Docling)
  -> Block/Page intermediate representation (schema.py)
  -> OCR/figure/table augmentation (equations.py / figures.py / tables.py)
  -> term-protected translation (translate.py; engines.py)
  -> export Markdown / TXT / PDF (export.py; overlay.py)
  -> manifest.json + diagnostics + cached intermediate pages
```

- `paperstudio/parser.py`: 原生文本与阅读顺序启发式、多栏基本解析。
- `paperstudio/pdf_health.py`: 底层 MuPDF 诊断聚合和异常降级。
- `paperstudio/schema.py`: 结构化页和内容块，便于多个解析后端共存。
- `paperstudio/tables.py`: 可选保守跨页表格拼接。
- `paperstudio/equations.py`: 可选 OCR 接口，模型精度需要独立测试。
- `paperstudio/translate.py`: 翻译引擎适配、不可改动标记校验与缓存。
- `paperstudio/export.py`: 结构化 Markdown 与 TXT/重排 PDF；`overlay.py` 负责保守覆盖模式。
- `paperstudio/pipeline.py`: 页面缓存、异常报告与批量处理。
- `paperstudio/web.py` + `web_static`: 本地 HTTP 控制台和任务队列；`gui.py` 为 Tkinter。

**Known boundaries:** PDF is a visual rendering, Markdown is a logical flow. Image crop, table span and absolute text positioning cannot always be represented losslessly in standard Markdown. Preserve source geometry in the intermediate representation where possible and report uncertainty rather than silently dropping data.
