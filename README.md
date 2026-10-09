# AcademicPDF Studio | 学术 PDF 翻译与 Markdown 转换

[![Project status](https://img.shields.io/badge/status-research%20prototype-orange)](#当前状态) [![Python](https://img.shields.io/badge/Python-3.11-blue)](pyproject.toml) [![License](https://img.shields.io/badge/own%20code-MIT-green)](LICENSE)

**AcademicPDF Studio v0.4.1**：本地优先的学术 PDF 转换工作台，优先生成**结构清晰、可编辑的 Markdown**，并同时导出 PDF / TXT。提供本地浏览器界面、Tkinter 桌面界面和命令行；支持常规双栏 PDF、部分公式与表格恢复、图片/矢量图提取、中文翻译和双语对照。

> **研究原型，不是任意 PDF 均可 1:1 还原的产品。** Markdown 不能精确表示 PDF 的分页、多栏、绝对坐标与合并单元格。遇到失败或降级的页面，应查看 `manifest.json` 中的 `diagnostics`、`needs_review`，并对照原文复核。程序目前**没有交付经过 Windows 原机验收的预编译 EXE**。

## 快速开始 / Quick start

### Windows 11（推荐先使用网页版）

1. 安装 **Python 3.11 x64** 并勾选 Add Python to PATH。
2. 克隆或下载本仓库，在**完整解压后的项目根目录**双击 `Start-Web.cmd`；首次安装依赖需要网络。
3. 浏览器打开 `http://127.0.0.1:8765/`；首次测试推荐「仅格式转换」，使用 `examples/demo_paper.pdf`。
4. 要翻译成中文，配置 Ollama（本地免费）、Argos Translate（下载语言包后离线免费）、LibreTranslate（可自建）或 DeepSeek / OpenAI / DeepL（云 API；按各服务政策计费）。**上传学术原文至第三方翻译服务前请确认授权与隐私要求**。

桌面界面：`Start-Desktop.cmd`。环境诊断：`Diagnose-Windows.cmd`。Windows EXE 构建：`Build-Windows-Web.cmd`（需要在 Windows 运行，默认输出 `dist/AcademicPDF-Web/` 整个目录）。

### CLI / 跨平台

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m paperstudio examples/demo_paper.pdf -o output --engine none --mode bilingual --formats md,pdf,txt
```

本地 Ollama 翻译示例：

```bash
python -m paperstudio examples/demo_paper.pdf -o output --engine ollama --model qwen2.5:3b --mode zh
```

`--engine none` **不会翻译**；请先运行 Ollama 并下载对应模型。查看 `python -m paperstudio --help` 获取其他参数。对保密论文优先选离线方案；复杂/扫描论文可选 Docling、pix2tex 等额外依赖，但启动耗时、显存和精度均取决于模型环境。

## 处理能力与限制

| 项目 | 当前能力 | 当前限制 |
| --- | --- | --- |
| Markdown | 标题、段落、基本双栏顺序、列表/表格/公式/图像引用 | 深层标题、跨栏阅读顺序、复杂表格和脚注不保证完全准确 |
| 数学公式 | 保护原有表达；可选 pix2tex 接口 | 真实模型 OCR 准确率未系统评测，部分公式仍需人工核对 |
| 图表 | 位图提取、部分 PDF 绘图矢量候选（PNG/SVG） | 复杂裁切/混合内容/图注对应有漏检风险 |
| 跨页表格 | 列结构和页边界启发式拼接 | 误拼或漏拼；合并单元格不等价于原生 Markdown 表格 |
| PDF | 中文重排 `reflow`；保守覆盖 `overlay` | 不能保证像素级一致；长中文可产生溢出或降级 |
| 翻译 | Ollama / Argos / LibreTranslate / DeepSeek / OpenAI / DeepL | 术语一致性依赖模型和词表；云端接口需要网络/费用 |
| 故障恢复 | MuPDF 底层诊断汇总、保守降级、页面缓存 | 报错页不等于内容已经完整恢复；缺少原始故障 PDF 的复现验证 |
| 发布 | Python / 本地 Web / Tkinter / Windows 打包工作流 | **尚无经 Windows 原生验证的预编译 EXE** |

## 实际测试范围

- v0.4.1 源码随附测试集：**51 项自动化测试**；可通过 `python -m pip install -r requirements-build.txt` 和 `python -m pytest tests -q` 运行。上游测试报告记录 Linux / Python 3.13 环境，不等价于 Windows 原生打包验收。
- `benchmark/fixtures/` 含 **3 份合成 IEEE 双栏风格样例**与参考标注；结构得分仅覆盖有限的已标注元素，**不应宣传为真实 IEEE 论文的整体准确率**。
- 碰到 `MuPDF error: ... stitching function`，请保留受影响文档和 `manifest.json`。当前修复的是诊断和降级逻辑，不能保证从损坏/异常 PDF 里无损恢复全部内容。

参阅：[验收报告](TEST_REPORT_v041.md) · [已知问题](KNOWN_ISSUES.md) · [未来路线图](ROADMAP.md) · [安全与隐私](SECURITY.md) · [架构说明](docs/ARCHITECTURE.md) · [v0.4.1 更新](CHANGELOG_v041.md)。

## 工程目录

```text
paperstudio/                 核心解析、OCR接口、翻译、导出、Web 和桌面 GUI
paperstudio/web_static/      浏览器 UI 静态文件
benchmark/                   合成双栏论文生成器、标注与评测脚本
tests/                       单元、故障注入和 Web 接口测试
tools/                       Windows 环境检查、打包验证工具
.github/workflows/           自动化测试及 Windows 构建
Start-Web.cmd                Windows 浏览器入口
Start-Desktop.cmd            Windows 桌面入口
```

## 许可证与第三方依赖

仓库中**原创源码**以 [MIT](LICENSE) 授权。第三方库和模型权重独立遵循其许可；**PyMuPDF 提供 AGPLv3 与商业授权选项**。将 PyMuPDF 包装进 EXE 或公开部署网络服务前，必须核查 AGPL 义务或取得适当商业授权，不能仅凭本仓库的 MIT 文件判断可闭源分发。模型使用、PDF 原文版权、API 调用费用均由使用者另行确认。

## 参与改进

欢迎提交可重复的 issue、测试用例与 PR。出现论文解析 bug 时，请附软件版本、Python/Windows 版本、失败页号、`manifest.json` 的诊断摘要；**请先移除个人信息、论文保密内容与 API Key**。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。
