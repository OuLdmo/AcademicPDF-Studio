# 同类产品调研：AcademicPDF Studio 技术吸收方案

研究时间：2026-10-08。比较为定性功能评估，非相同样本下测得的排名。

| 方案 | 技术要点 | 优势 | 限制 | 实施借鉴 |
|---|---|---|---|---|
| MinerU | 文档版面/VLM/OCR/公式与表格恢复 | 复杂学术文档解析、表格图形、多格式结构化 | 模型内存/速度、许可额外限制 | 高精度解析作为未来适配器；逐页缓存 |
| Marker | 文档结构识别，输出 Markdown/JSON/HTML | 格式化公式和表格、去页眉页脚、资源提取 | 模型较重，代码与权重许可不同 | 结构化中间对象与 Markdown 主格式 |
| Meta Nougat | 视觉编码器与文字解码器 | 面向论文数学和表格的 OCR | 误识别/推理资源与版式限制 | 专门保护公式，未来可接公式 OCR |
| Microsoft MarkItDown | 多格式解析器→Markdown | 快速简单、可编程可批量 | 不保证出版版式 | 统一文件 CLI/批处理 |
| IBM Docling | DoclingDocument、布局识别、表格结构模型 | 本地、结构化、跨栏识别 | OCR 首次模型安装、跨页内容可误分 | 可选 Docling 单页增强后端 |
| PDFMathTranslate | 布局感知下的文字翻译和重新放置 | 公式/图表保留、译文 PDF 视觉一致性 | PDF 固定布局挤压、以 PDF 为核心 | 非翻译区域保护与模型适配 |
| BabelDOC | PDF 布局恢复、翻译排版与双语 PDF | 原文/中文对照，公式位置保护 | 复杂跨页 / 跨栏限制 | 对照模式和分块缓存 |
| Reflo | 在线学术 PDF 译文阅读产品 | 引文与原图同上下文阅读 | 缺乏公开完整模型/性能/离线资料 | 用户体验及 QA 追溯思想 |

权衡：`PyMuPDF` 不是以上方案之一，但轻量、跨平台、有坐标和图片提取 API；用于可复现基线。`Docling` 满足增强解析。高级模型均未嵌入，以降低默认安装资源和避免复制许可受限代码。图片、矢量绘图、跨栏表格、公式必须保留独立 QA 提示。

Sources:
- https://github.com/opendatalab/MinerU
- https://github.com/datalab-to/marker
- https://github.com/datalab-to/marker/blob/master/README.md
- https://github.com/facebookresearch/nougat
- https://github.com/microsoft/markitdown
- https://github.com/docling-project/docling
- https://arxiv.org/abs/2501.17887
- https://github.com/PDFMathTranslate/PDFMathTranslate
- https://github.com/funstory-ai/BabelDOC
- https://tryreflo.com/tools/translate-academic-paper-pdf

许可提醒：MinerU 使用其自定义开源许可；Marker 代码 Apache-2.0、权重另有约束；Docling 代码 MIT；PDFMathTranslate AGPL-3.0，使用时应查最新仓库文件。不能由代码许可推定全部模型许可。

## 后续提高真实精度的建议

1. 建立含 IEEE 双栏、跨页三线表、矢量波形、公式密集 PDF、扫描页的黄金集和人工答案。
2. 新增 DoclingDocument 元信息（bounding boxes, cell spans）→ 中间结构，绘图区域裁切与图文配对。
3. 专门公式 OCR（UniMERNet/LaTeX OCR）并对公式语义做判定，复用源文件中的 TeX 比瞎猜更好。
4. 对翻译后的中文重新排版做视觉差异度检测：页面渲染、块 IOU、字符缺失率、图号匹配率、结构层级相似度。
5. 高保真 PDF 可选集成 PDFMathTranslate/BabelDOC 为独立后端，检查许可，避免将视觉排版要求强加给 Markdown。

额外关键许可来源： https://pymupdf.io/licensing （PyMuPDF 官方：AGPLv3 或商业授权）。
