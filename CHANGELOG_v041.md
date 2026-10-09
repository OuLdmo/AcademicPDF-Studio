# AcademicPDF Studio v0.4.1 — 2026-10-09

## 为什么本次修复

Windows GUI/网页日志重复输出：

```text
warning: The `fitz` API is deprecated ... Use `import pymupdf` instead.
MuPDF error: syntax error: too many sub-functions in stitching function
```

这些是两类不同的问题：前者是项目遗留的模块名；后者是 PDF 内部 **FunctionType 3（stitching function）** 相关的 PDF 引擎错误，可能来自复杂或非法的 PDF 函数/图形。它**不是**软件的跨页表格拼接功能。仅凭截图无法确定究竟哪个 PDF 页面导致该错误，因此本版采用真实程序错误捕获和降级策略，不声称修复输入 PDF 内部不合法的对象。

## 主要变更

1. 全部应用/工具/测试脚本内的 `import fitz` 改为 `import pymupdf as fitz`，不再触发旧 API 导入警告。
2. 新增 `paperstudio/pdf_health.py`，使用 `PyMuPDF.TOOLS` 抑制底层消息的无限控制台刷屏，同时**保留、分类、计数** MuPDF 诊断，并写入最终 `manifest.json`。
3. 逐页、逐阶段错误隔离：文本提取失败采用纯文本后备；单页失败保留页码，继续后续页面；Docling 失败退回本地解析。
4. 发现异常 PDF function 错误时停止可能重复触发错误的高成本矢量/SVG/页面快照流程，而非继续反复重放；这部分损失会记录为 `skipped`，要求复核原文件。
5. 严禁无坐标 fallback 文本在 `overlay` 模式中整页擦除：发现缺失坐标时保持源页不动，并记录 `overlay_missing_geometry`。
6. 不再将异常页缓存为“确认解析成功”；缓存版本升级，防止复用过去的不完整数据。
7. 修正网页版版本识别，重复启动只复用**同一版本**的健康服务；PyInstaller Windows hook 改为 `--collect-submodules pymupdf`。
8. PDF 报告增加 `diagnostics`、`needs_review`，GUI 警告提示不再误称全部为“翻译失败片段”。
9. 新增 11 项 v0.4.1 回归用例（原 40 → 51），覆盖底层错误聚合、解析异常隔离、原页保护、复杂函数示例、并发、密码 PDF 和损坏 PDF。

## 功能限制与未完成验证

- 用户提供的是错误截图而非触发错误的原始 PDF，**未复现相同底层错误的真实页面**。预置了一个 1,200 子函数的测试 PDF，但在测试环境的 MuPDF 1.26.7 下，它不会产生与截图完全相同的日志；错误文案通过故障注入测试被覆盖。
- 未在原生 Windows 运行环境测试 BAT 和 EXE；当前不是预编译 Windows EXE 交付。
- 没有在真实 IEEE 论文全集上重新测量公式 OCR 或实际中文翻译质量。
- 凡被跳过/降级的页面与图表仍需人工核对；报告里 `needs_review=true` 代表不能视为完全无损。

具体命令、测试记录见 `TEST_REPORT_v041.md` 和 `START_HERE_v041.md`。
