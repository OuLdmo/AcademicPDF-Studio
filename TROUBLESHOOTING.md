# AcademicPDF Studio v0.4.2 — 故障排查

## Windows CI: `UnicodeEncodeError: charmap`

旧版在 Windows Actions 的 CP1252 输出编码下直接打印中文会崩溃。新版 `tools/windows_bootstrap.py:msg()` 使用当前输出编码，并对不可编码字符采用 `\uXXXX` 转义，不再中断程序。

用 PowerShell 复现验证：

    $env:PYTHONIOENCODING='cp1252:strict'
    py -3.11 tools/windows_bootstrap.py --mode doctor
    Remove-Item Env:PYTHONIOENCODING
    py -3.11 -m pytest tests/test_windows_launchers.py -q

显示 `\uXXXX` 是兼容旧控制台代码页的文本转义，不是 PDF 转换错误。

## 缺少 numpy / skimage

应安装完整的 `requirements-build.txt`，且确保 pip 和 pytest 使用同一个 Python 虚拟环境。

## MuPDF stitching function 错误

属于 PDF 底层函数解析问题，不能通过隐藏告警认定转换无损。保留异常页与 `manifest.json` 的 `diagnostics`，按页排查并必要时选择 OCR/备用解析。

## 网页和 EXE

检查 8765 端口及诊断输出。Windows EXE 必须在 Windows x64 下打包，公开分发前需处理 PyMuPDF 许可问题。

不要在 GitHub Issue 中上传 API Key 或保密论文。
