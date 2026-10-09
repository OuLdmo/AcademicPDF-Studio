# AcademicPDF Studio v0.3.1 — Windows 修复及使用手册

## 为什么旧版 BAT 会报“不是内部或外部命令”？

v0.3.0 的部分 BAT 以 UTF-8 保存，但里面直接写了中文命令和含中文内容的括号块。CMD 的代码页与文件编码不一致时，可能将命令拆分为无效片段（你截图中的 `ython.exe`、`emicPDF-Web.exe` 等）。旧版构建 BAT 也调用了未安装的 `pytest`。

**新版本的全部 BAT/CMD 都只有 ASCII 字节，使用 CRLF 行尾，中文提示及环境检测放在 Python 中执行。** 不再使用 `chcp 65001` 来试图修补批处理解析。源代码仍为 UTF-8。

## 最快修复流程（推荐）

1. **重新下载并完整解压 v0.3.1 的 ZIP**；不要直接在压缩包预览窗口内运行 BAT。
2. 将工程放到可写的目录，例如 `D:\AcademicPDF-Studio` 或 `C:\Users\<用户名>\Documents\AcademicPDF-Studio`。不要放到 `C:\Program Files`、`C:\Windows` 或受限网络盘。
3. 如果电脑上留有旧工程中的 `.venv`，建议不要直接复制到新工程。**新版本默认会自行创建自己的 `.venv`**；如已存在损坏的 `.venv`，请先关闭软件，并将其重命名为 `.venv-old`（不要覆盖里面的数据）。
4. 首选双击 **`Start-Web.cmd`** 或 **`启动网页版.bat`**。Windows 首次运行需要安装 Python **3.11 x64**，并能访问 PyPI 安装依赖。安装 Python 时选中 *Python launcher* 和 *Add python.exe to PATH*。**即使未勾选 PATH，只要 `py -3.11` 能用，也可以启动。**
5. 成功后会在浏览器打开 `http://127.0.0.1:8765/`；若端口冲突，程序会尝试 8766～8774，并打印实际 URL。初次建议选“只转换格式”，上传 `examples/demo_paper.pdf` 验证管线，再配置 Ollama。

> 第一次联网安装的 PyMuPDF 等依赖与实际翻译是不同的两件事。选择“只转换格式”不代表已经翻译成中文。

## 入口文件对照

| 中文入口（全部修复） | ASCII 文件名（效果相同） | 用途 |
|---|---|---|
| `启动网页版.bat` | `Start-Web.cmd` | Python 网页版；若已有经自检的 Windows EXE，优先启动 EXE |
| `启动图形界面.bat` | `Start-Desktop.cmd` | Tkinter 桌面版 |
| `诊断环境.bat` | `Diagnose-Windows.cmd` | 显示 Python 和依赖状态 |
| `构建Windows_网页版EXE.bat` | `Build-Windows-Web.cmd` | 在 Windows 上构建并自动检查 Web EXE |
| `构建Windows_EXE.bat` | `Build-Windows-All.cmd` | 构建 Web、桌面和 CLI EXE |

## 问题定位

- **`Python 3.11+ was not found`**：下载 [Python 3.11 x64](https://www.python.org/downloads/windows/)，安装后重启 CMD。PowerShell 输入 `py -3.11 --version` 检查；`python --version` 不可用不一定代表 `py` 也不可用。
- **提示 `.venv` 不完整**：关闭所有程序后，将 `.venv` 文件夹重命名为 `.venv-old`，再次双击 `Start-Web.cmd`；不要修改全局 Python 环境来补救。
- **pip 无法下载依赖**：检查代理、防火墙、证书和网络；打开 `Diagnose-Windows.cmd` 读取版本信息。可在 PowerShell 中执行 `py -3.11 -m pip --version` 排查 pip。
- **出现 `Access is denied` 或 `Permission denied`**：移动到用户目录，再重新解压；检查杀毒软件阻止虚拟环境写入。
- **一直打不开 8765 网址**：先查看 CMD 是否显示实际 URL，程序可能自动切换到 8766 等端口；测试 `http://127.0.0.1:8765/api/health`。只要命令窗口关了，服务就会停止。
- **打开后转换失败**：先将翻译引擎设为 `none`，测试示例 PDF。使用 Ollama 时需另行 `ollama pull qwen2.5:3b` 并启动服务；OpenAI/DeepL 需 API 密钥且会发送待翻译文本到第三方。
- **中文路径/空格路径**：新增脚本使用 `%~dp0` 定位工程，且不在 CMD 源码写中文文本，已增加带空格/中文目录的 Python 层验证。真正 CMD 执行仍须在 Windows 本机或 Windows Actions 验证。
- **打包后 DLL/资源丢失**：执行 `Build-Windows-Web.cmd`，只有 EXE 通过 `--self-test` 和 HTTP `/api/health` 后才会提示成功。必须分发 `dist/AcademicPDF-Web/` **整个目录**，不能仅复制 `AcademicPDF-Web.exe`。

## 环境诊断与快速命令

```powershell
# 在 PowerShell 进入解压根目录后
py -3.11 --version
.\Diagnose-Windows.cmd
.\Start-Web.cmd

# 可选：直接绕过 BAT（已存在 venv）
.\.venv\Scripts\python.exe studio_web.py --self-test
.\.venv\Scripts\python.exe studio_web.py --no-browser --port 8765
```

## EXE 构建的必要限制

当前交付是**修正后的源码包 + 可运行启动脚本 + Windows 构建脚本**，不是一个经 Windows 实测的独立 EXE。PyInstaller 不能直接从当前 Linux 构建环境生成 Windows 原生 EXE。要真正生成 EXE，在 Windows 11 x64 双击 `Build-Windows-Web.cmd`，构建完成后检查：

`dist\AcademicPDF-Web\AcademicPDF-Web.exe`

或者把源代码上传至你自己的 GitHub 仓库，在 **Actions → Build Windows Web EXE (CMD and HTTP smoke) → Run workflow** 执行 Windows runner 构建并下载工件。该工作流包含 CMD 入口冒烟测试、自动化测试、EXE 静态资源检查及真实 HTTP 健康检查。若 CI 未实际运行，不应把配置文件视为构建成功。

请注意：本软件捆绑 PyMuPDF 时需核查 AGPLv3/商业许可义务；开源源码许可与第三方组件许可不是一回事。
