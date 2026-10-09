# AcademicPDF Studio 0.3.0 功能更新及验收

## 本轮主要改进

- 新增 `studio_web.py` / `paperstudio/web.py`：无需 Flask/FastAPI 的本机 HTTP 服务，复用现有 `process_pdf` 完整处理逻辑。
- 新增响应式网页：拖放与多文件上传、翻译引擎与模型、单/双语模式、PDF overlay/reflow、Docling/pix2tex 可选开关、矢量图与跨页表格选项、术语 JSON。
- 新增页面进度与日志、Markdown 阅读/源码预览、复制按钮、MD/TXT/PDF 独立下载、包含 assets 和 manifest 的 ZIP。
- 新增 `启动网页版.bat` 自动创建虚拟环境和安装依赖；新增 Windows PyInstaller `onedir` 自动构建脚本以及 GitHub Actions Windows build & health smoke test。
- 安全措施：默认 127.0.0.1、随机启动 CSRF token、Origin 校验、PDF 头部和数量/大小限制、输出资源路径限定、可下载文件类型限制、安全响应头与 Content Security Policy。不代表公网环境的成熟安全性。
- 保留 v0.2.0 的数学 OCR 可选接口、跨页表格拼接、矢量图提取、PDF 视觉覆盖、两个独立质量评估维度和合成双栏基准。

## 真实验证的范围

- `python -m pytest tests -q`: 13 项自动化测试通过（其中 v0.3.0 新增两个测试）；包括上传、CSRF、生成结果、Markdown 预览、PDF/ZIP 下载及路径遍历拦截。
- `node --check paperstudio/web_static/app.js`: JavaScript 静态语法验证通过。
- 使用 Chromium 的本地 HTML 静态页面截图检查布局生成成功；运行环境浏览器策略禁止访问任何本地 HTTP URL，因而**没有完成基于浏览器真实网络点击的端到端交互测试**。
- 后端通过 Python urllib 对真实 HTTP 服务、真实示例 PDF 完成端到端操作。
- Windows EXE 未生成，原因与可执行步骤见 `BUILD_WINDOWS_WEB.md`。

## 已知限制

- 服务进程退出后网页无法继续访问，除非重新打开 BAT/EXE。没有云端托管，没有公网 URL。
- 无法替代真正的精确公式 OCR 质量验证和真实 IEEE 双栏数据集人工标注；旧版量化数据来自合成 PDF。
- Markdown 阅读视图只提供基础渲染，复杂公式需外部专业编辑器。
- 同时只运行一个转换工作线程，防止重型 OCR/LLM 任务造成资源争用。
- 默认最多 12 PDF / 合计 80 MB，缓存和完成文件位于本机数据目录，需由用户定期清理。
