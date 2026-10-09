# Windows EXE 构建（v0.4.2）

**需要 Windows x64 环境**。PyInstaller 不能在 Linux 上直接生成 Windows EXE。先阅读 [快速开始](QUICKSTART.md)。

## Windows 本机

1. 安装 Python 3.11 x64 并完整克隆/下载本仓库。
2. 双击 `Build-Windows-Web.cmd`。将安装 `requirements-build.txt`、运行测试、打包并校验 EXE 自检和 HTTP 健康接口。
3. 输出为 `dist\AcademicPDF-Web\AcademicPDF-Web.exe`，使用时保留整个 `AcademicPDF-Web` 文件夹（包括 `_internal`）。

## GitHub Actions

在 Actions 中选择 **Build Windows Web EXE (CMD and HTTP smoke)** 并手动触发。工作流通过测试和打包后的 HTTP 验证，才会生成 `AcademicPDF-Web-Windows-x64` Artifact。

**提醒：** EXE 不包含 Ollama/Docling/pix2tex 大模型。公开分发包含 PyMuPDF 的软件前，请核对 AGPLv3/商业授权要求。
