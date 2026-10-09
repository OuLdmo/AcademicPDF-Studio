# v0.4.1：Windows 最短修复步骤

1. 下载完整 v0.4.1 ZIP，**解压到新目录**，例如 `D:\AcademicPDF-Studio-v041`。不要在压缩包预览窗口内直接运行 CMD。
2. 保留你已有的论文与结果；不要覆盖原始 PDF。如旧版已经有 `.venv`，新目录会建立独立环境，避免继续沿用损坏的旧环境。
3. 先双击 `Diagnose-Windows.cmd`；随后双击 `Start-Web.cmd` 打开网页版（或 `Start-Desktop.cmd` 打开图形界面）。首次安装依赖需联网。
4. 打开 `http://127.0.0.1:8765/`，选择“仅转换格式/none”，先用 `examples/demo_paper.pdf` 测试，再选 DeepSeek、Ollama 或免费引擎。
5. 将之前引发错误的 PDF 放入转换界面。若出现异常，下载结果 ZIP，检查 `manifest.json` 的 `diagnostics`、`needs_review` 和 `warnings`。
6. 如果只在某个 PDF 上出现 stitching function 报错，可尝试关闭“矢量图捕获”和“原页截图”后重试，或改用 Docling OCR 解析。必要时使用受信任 PDF 软件重新打印为 PDF（可能改变书签、文本层与引用，应保留原件）。

如果需要诊断原始 PDF 导致的 MuPDF 报错，应提供出错文件或可复现的脱敏页面，才能进一步定位页码和对象。请勿上传保密文献到第三方在线转换服务。

## 需要执行 EXE 构建时

Windows x64 + Python 3.11（或 3.12/3.13）：双击 `Build-Windows-Web.cmd`。该操作将先安装 `requirements-build.txt`、运行 51 项测试，随后编译并执行 EXE 的本地 HTTP 健康检查。成功后复制 **整个** `dist\AcademicPDF-Web` 文件夹。当前 ZIP **未包含预编译 EXE**，Linux 环境不能原生构建 Windows PE 程序。

构建失败时，先运行 `Diagnose-Windows.cmd` 并提供完整命令行日志及 `manifest.json`，不要只提供最后一行错误。
