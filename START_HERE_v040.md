# AcademicPDF Studio v0.4.0 — Windows quick start / 紧急修复

**下载完整 ZIP、解压后使用，不要在压缩包内运行 CMD/BAT。**

## 最快的网页版启动

1. 在 Windows 11 安装 Python 3.11 x64（包括 pip 和 Python Launcher）。
2. 在项目文件夹双击 `Start-Web.cmd`。首次启动会自动创建 `.venv` 并安装核心依赖。
3. 在浏览器打开 `http://127.0.0.1:8765/`；支持备用端口。
4. 在左侧选择**翻译引擎**，展开“⚙ 翻译引擎配置”。填写模型、服务地址、API Key，再点击“测试连接与翻译”。
5. 上传 PDF，点击“开始转换”。完成后下载 Markdown、PDF、TXT 或 ZIP。

桌面版：双击 `Start-Desktop.cmd`，然后点击 `⚙ 翻译引擎配置 / API Key`。

## 你截图中的 numpy 导入错误

新版构建脚本现在会自动安装测试依赖。若仍在旧目录里尝试修复，打开 CMD，进入项目根目录后运行：

```bat
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m pytest tests -q
```

以上 `requirements-build.txt` **仅在 v0.4.0 中提供**，旧版本先完整替换为新版。不要只安装 `pytest` 后就构建 EXE。

如果 `.venv` 损坏，将它重命名为 `.venv-old` 后重新运行 `Start-Web.cmd`，新环境会自动创建。

## 配置四种典型翻译方案

| 引擎 | 模型 | URL | Key | 费用与联网 |
|---|---|---|---|---|
| Ollama | `qwen2.5:3b` | `http://127.0.0.1:11434` | 留空 | 本地免费；第一次需 `ollama pull qwen2.5:3b`，模型要先启动 |
| Argos | 留空 | 留空 | 留空 | 离线免费；双击 `Install-Argos.cmd` 下载英文→中文模型（初次联网） |
| LibreTranslate | 留空 | `http://127.0.0.1:5000` | 自建一般留空 | 可自建免费：需另外运行 LibreTranslate 服务 |
| DeepSeek | `deepseek-flash` | `https://api.deepseek.com` | DeepSeek API Key | 按 tokens 收费；先创建密钥、账户需有可用额度 |

还支持 `deepseek-v4-pro`（手动更改模型）、OpenAI 及 DeepL。**不要把收费 API 误认为免费。**

## Windows EXE 的实际边界

本包是可运行 Python 网页版和 Windows 构建工程，**不是预编译 Windows EXE**。在 Windows 上运行 `Build-Windows-Web.cmd` 可以编译并对生成的 `dist\AcademicPDF-Web\AcademicPDF-Web.exe` 做启动/HTTP 自检。PyInstaller 必须在 Windows 上构建 Windows EXE；官方 Python 3.11 x64 推荐。整个 `dist\AcademicPDF-Web` 文件夹必须一起分发。

## 隐私与安全

API Key 输入框遮掩显示，任务处理完成后从服务端任务选项移除；不保存在浏览器 localStorage、不输出到报告。远程 API 处理的是论文待翻译文本，即**不是完全离线**。API Key 可能由用户环境变量提供。不要把私密论文提交给不信任的公共免费翻译服务。

**验证**：完整功能测试、浏览器控件测试；真实第三方收费服务、Windows 编译产物未在此 Linux 环境测试。
