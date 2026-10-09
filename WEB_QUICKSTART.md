> **v0.4.1 更新：** 浏览器左侧「⚙ 翻译引擎配置」可输入 DeepSeek/OpenAI/DeepL Key、API 地址、模型并测试连接。免费本地引擎见 [START_HERE_v040.md](START_HERE_v040.md)。

> **针对 CMD 乱码及 `.bat` 报错：** 请先阅读 [WINDOWS_FIX_GUIDE.md](WINDOWS_FIX_GUIDE.md)，不要继续使用 v0.3.0 的旧脚本。

# AcademicPDF Studio v0.3.1 · 网页版 3 分钟上手

## 最简单的方式：Windows 11（无须命令行）

1. 下载并解压 `AcademicPDF-Studio-v0.3.1.zip`，**解压完整文件夹**（不要在 ZIP 预览窗口里双击运行）。
2. 如果文件夹内已有打包好的 `dist/AcademicPDF-Web/AcademicPDF-Web.exe`，直接双击 EXE；**否则**先从 <https://www.python.org/downloads/windows/> 安装 Python 3.11 x64，勾选 **Add python.exe to PATH**。
3. 双击 **`Start-Web.cmd`** 或 **`启动网页版.bat`**。首次运行会创建 `.venv` 并安装项目依赖（需要互联网），之后自动打开浏览器：<http://127.0.0.1:8765/>。
4. 选择 PDF → 选择翻译引擎 → 开始转换 → 在线预览或点击 **下载全部结果 ZIP**。ZIP 包含 `.md`、`.pdf`、`.txt`、`assets/`、`manifest.json`。
5. 完成后关闭启动脚本弹出的黑色命令窗口，服务即可停止。只关闭浏览器标签页不会停止服务。

> 如果 8765 端口被占用，在命令行运行 `.venv\Scripts\python.exe studio_web.py --port 8877`，然后访问 <http://127.0.0.1:8877/>。

## 不安装翻译模型，先体验转换

选择 **“只转换格式（不翻译）”**，可直接使用 PDF → Markdown / PDF / TXT，无需 Ollama 或 API 密钥；它**不会**将英语翻译为中文。

## 纯本地中文翻译（推荐）

1. 安装 Ollama：<https://ollama.com/>。
2. 在 PowerShell 运行 `ollama pull qwen2.5:3b`（模型下载需要网络和数 GB 磁盘空间）。
3. 确认 Ollama 服务在 `127.0.0.1:11434` 运行；一般 Windows 安装后的 Ollama 会自动启动，必要时运行 `ollama serve`。
4. 网页中选择 **Ollama · 本地中文翻译**，模型填 `qwen2.5:3b`，上传 PDF，选择 **纯中文** 或 **中英双语**。
5. Ollama 模型下载完成后，默认处理流程会在本机运行。首次下载模型不代表在翻译时上传 PDF。

默认解析器 PyMuPDF 无需显卡。Docling / pix2tex 为**额外可选**依赖；在首次安装依赖和模型时需要联网。

## 命令行替代方式（Windows / macOS / Linux）

```powershell
python -m pip install -r requirements.txt
python studio_web.py
```

浏览器访问 <http://127.0.0.1:8765/>；修改数据目录：

```powershell
python studio_web.py --data-dir "D:\AcademicPDF-Results" --port 8765
```

## 输出文件在哪里？

- 默认 `~/Documents/AcademicPDF-Studio-Output/`（如果没有 Documents，回退到用户主目录）。
- 网页也会提供单独的 `.md`、`.pdf`、`.txt` 下载按钮，以及含 `assets/` 的完整 ZIP。
- 任务文件保存在本机磁盘，即使浏览器关闭也不会被自动上传到外部云端。
- 服务重启后历史任务不在网页任务列表中，但文件仍保留在本机输出目录；再次上传相同 PDF，会生成新任务目录。**当前网页版不承诺跨任务复用旧任务目录缓存。** 每个任务内的解析和翻译缓存仍可用于原有命令行流程。

## 在线 / 远程访问与隐私

- 网页版实际是**本机浏览器界面 + 本机 Python HTTP 服务**，不是已经部署到公网的网站，不支持单靠访问某个公共链接随时使用。
- 服务默认绑定 `127.0.0.1`，**没有公开用户账户/权限系统**；不要将它直接暴露给公网，也不要做无验证端口转发。
- 如果必须远程使用，应自行部署认证、HTTPS、访问隔离、速率限制、上传大小限制和定期清理，或仅通过受信 VPN 访问。
- **OpenAI / DeepL** 翻译将待翻译文字提交给第三方服务。使用它们时请提前在操作系统中设置 `OPENAI_API_KEY` / `DEEPL_AUTH_KEY`，并在启动脚本前确保环境变量在当前进程中有效。不要将密钥写入论文或上传表单。
- PDF 具有潜在恶意内容风险，建议在操作系统权限受限的环境中处理来源不明的 PDF。

## 备注

- 网页的“阅读视图”是**简易 Markdown 预览**，用于快速核对标题、段落、图片和大部分加粗，不是完整的 KaTeX/GFM 渲染器。复杂表格和 LaTeX 请在 Obsidian、Typora 等专业编辑器中检查。
- 翻译质量依赖所选本地模型与解析结果。PDF 视觉覆盖有可能出现译文溢出，`manifest.json` 将记录相关警告。
- Windows 原生 EXE 的确切构建步骤见 `BUILD_WINDOWS_WEB.md`。当前 ZIP 包为**源代码 + 一键启动脚本**，不含预编译 `.exe`。

## Docker 本机运行（选用）

```bash
docker build -t academicpdf-studio:0.3 .
docker run --rm -p 127.0.0.1:8765:8765 -v "$PWD/academicpdf-results:/data" academicpdf-studio:0.3
```

访问 <http://127.0.0.1:8765/>。**不要**把 `-p 127.0.0.1:8765:8765` 改成公网端口映射；本应用尚未提供适合公网开放的登录与权限系统。
