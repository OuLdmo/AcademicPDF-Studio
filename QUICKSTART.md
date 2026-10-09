# AcademicPDF Studio v0.4.2 — 快速开始

1. 安装 Python 3.11 x64，在仓库根目录双击 `Diagnose-Windows.cmd`。
2. 双击 `Start-Web.cmd`，浏览器访问 `http://127.0.0.1:8765/`。
3. 先用 `examples/demo_paper.pdf` 测试 `none` 格式转换，再配置 Ollama、Argos、LibreTranslate、DeepSeek 等翻译引擎。
4. 桌面版 `Start-Desktop.cmd`；打包 EXE 使用 `Build-Windows-Web.cmd`。

命令行使用软件虚拟环境安装 `requirements.txt`，运行 `python -m paperstudio --help` 查看具体参数。

- [Windows 故障排查](TROUBLESHOOTING.md)
- [EXE 构建](BUILD_WINDOWS_WEB.md)
- [已知问题](KNOWN_ISSUES.md)

处理失败时检查 `manifest.json` 中的 `diagnostics` 和 `needs_review`。
