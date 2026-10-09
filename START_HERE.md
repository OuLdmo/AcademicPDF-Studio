# AcademicPDF Studio v0.3.1 — 一分钟开始

**之前 v0.3.0 的 BAT 因编码不兼容可能出现一串“不是内部或外部命令”报错。新版本已重写全部启动脚本。**

1. 下载 **`AcademicPDF-Studio-Windows-Fix-v0.3.1.zip`**，右键**全部解压**，建议到 `D:\AcademicPDF-Studio`。
2. 电脑安装 **Python 3.11 x64**（首次安装需要互联网）。不知道是否安装？运行 `Diagnose-Windows.cmd`；没有 Python 时会提示下载地址。
3. 双击 **`Start-Web.cmd`**（或者 `启动网页版.bat`）。首次启动自动建立 `.venv` 并安装运行依赖；随后浏览器访问 **http://127.0.0.1:8765/**（如端口被占用，以黑窗口输出的地址为准）。
4. 先选择 **“只转换格式（不翻译）”**，上传软件自带的 `examples/demo_paper.pdf`，点击“开始转换”，查看预览并下载 ZIP。
5. 确认可用后，如果需要本地中文翻译，再安装 Ollama、运行 `ollama pull qwen2.5:3b`、在页面中选择 Ollama。该模型不随软件捆绑。

**如果仍然报错：** 先用 `Diagnose-Windows.cmd` 查看环境，再参考 [`WINDOWS_FIX_GUIDE.md`](WINDOWS_FIX_GUIDE.md)。不要复制旧版本的 BAT、虚拟环境或只从 ZIP 预览窗口运行。

**关于 EXE：** 此包带 Windows **构建脚本**，不是已预编译的 Windows EXE。要获得 EXE，双击 `Build-Windows-Web.cmd` 在 Windows 原生运行并通过构建后健康检查。构建产物需分发整个 `dist/AcademicPDF-Web` 文件夹。
