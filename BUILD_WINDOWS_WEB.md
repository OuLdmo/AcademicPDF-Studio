> **v0.3.1 更新：** 中文 BAT 已改为纯 ASCII；优先双击 `Build-Windows-Web.cmd`；构建步骤现在会自动补齐 pytest/PyInstaller，并对成品 EXE 执行 HTTP 健康检查。

# 如何得到真正的 Windows EXE（v0.3.0）

## 为什么本次交付包没有预编译 EXE？

本次工程在 **Linux x86_64** 环境编写、运行和测试，容器没有 Windows 系统、Windows Python 与 Wine。PyInstaller **不是跨平台编译器**：它必须在目标平台上收集相应的 CPython 解释器、DLL、扩展包和运行依赖。从 Linux 构建的产物是 Linux ELF，**不是可直接双击运行的 Windows EXE**。将 `.sh`、`.bat` 或 Linux ELF 改名为 `.exe` 并不能解决问题。

另外，实验环境当前无法通过 pip 从公共网络下载额外构建工具，因此也不具备构建或验证 Windows 二进制所需的基础设施。本项目**没有**虚构任何 EXE 下载链接。

## 方案 A：在你的 Windows 电脑双击生成（推荐，最直接）

1. 安装 Python 3.11 x64（勾选 Add Python to PATH）。
2. 解压全部工程文件到英文或中文路径均可的可写目录，确保磁盘空闲空间 > 1.5 GB（具体取决于依赖）。
3. 双击 `构建Windows_网页版EXE.bat`。脚本会自动创建环境、安装依赖、运行测试，再调用 PyInstaller。
4. 成功后获取：

   ```text
   dist/AcademicPDF-Web/AcademicPDF-Web.exe
   dist/AcademicPDF-Web/_internal/...
   ```

   **请完整保留 `AcademicPDF-Web/` 目录！** PyInstaller `--onedir` 的 EXE 依赖其旁边的 `_internal` 运行库和资源文件，只复制单个 EXE 会导致启动失败。
5. 双击 `AcademicPDF-Web.exe`，它会启动本机网页并自动打开浏览器。

> Windows SmartScreen 如果提示未知发布者，可通过查看源码、自行在受信任机器构建和扫描文件来判断是否运行。不要为了未知二进制随意关闭系统保护。

## 方案 B：GitHub Actions 云端 Windows runner 自动构建

这个方法在**没有 Windows 电脑**时尤其适合，但需要 GitHub 仓库和联网：

1. 新建一个你有写入权限的 GitHub 仓库，把此工程全部代码（包括 `.github/workflows/build-windows.yml`）上传，**不要上传你的 API 密钥、论文或本地缓存**。
2. 打开仓库 **Actions → Build Windows EXE (Web + CLI + GUI) → Run workflow**。
3. 等待工作流完成 `Run tests`、`Build browser application` 和 `Smoke test Windows executable / browser endpoint` 三个环节。
4. 在工作流页面底部 **Artifacts** 下载 `AcademicPDF-Web-Windows-x64`，解压内部 `AcademicPDF-Web-Windows-x64.zip`。
5. 从压缩包内解压 `AcademicPDF-Web/` 文件夹，并双击 `AcademicPDF-Web.exe`。

> GitHub Actions 的 artifact 是构建输出，不等同于经过 Windows Defender 签名或代码签名的安装包。公网 GitHub 构建也会受到服务条款和运行额度限制。

## 打包后的注意事项

- EXE 内包含网页服务及默认 PDF 解析依赖；**不包含**几 GB 的 Ollama 模型、Ollama 服务、Docling 模型或 pix2tex 模型。
- 如果希望不安装本地模型也可翻译，可用 OpenAI/DeepL（需要网络和密钥，文字会发送到第三方）。
- `--help` 能运行只证明命令行入口没有崩溃；GitHub Actions 另有访问 `/api/health` 的 EXE 服务端冒烟测试。
- 不同 Windows 版本、中文字体与杀毒软件可能引起额外环境问题，请在实际目标电脑上做一次完整 PDF 上传与转换验证。
- **许可：** PyMuPDF 是 AGPLv3 / 商业许可。公开分发打包了该依赖的 EXE 时，需要依法履行相关开源许可义务，或取得相应商业授权。即使本项目的自有代码使用 MIT，第三方依赖许可也不会自动变成 MIT。

## 方案 C：免 EXE 直接使用网页版

即使没有任何 EXE，只要 Python 依赖已安装，双击 `启动网页版.bat` 就会自动在浏览器打开网页，这与 EXE 最终呈现的网页功能基本一致。它不要求用到命令行操作，也不需要把源文件逐一拷贝给工具。
