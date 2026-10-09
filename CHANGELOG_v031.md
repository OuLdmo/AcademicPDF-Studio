# v0.3.1 稳定性修复记录

1. 针对 Windows 中文 CMD 报“不是内部或外部命令”：重写全部 5 个 `.bat` 为纯 ASCII/CRLF，并新增 5 个英文别名 `.cmd` 和共用的 `tools/bootstrap.cmd`。
2. 将 Python 发现（优先 `py -3.11`，后备 3.12/3.13、PATH）、虚拟环境创建、缺失依赖安装、错误报告转交至 `tools/windows_bootstrap.py`，避免 CMD 对 UTF-8 中文命令误解析。
3. 修复构建脚本调用 `pytest` 而未安装的问题：构建前显式安装 pytest 和 PyInstaller；失败即停止，绝不伪报成功。
4. 网页程序 `--self-test` 检查核心模块与全部静态资源；EXE 构建结束后再检查 HTTP `/api/health`。
5. 网页 8765 被占用时复用已有 AcademicPDF 本地服务，或自动使用备用端口。显示真实 URL；明确处理目录权限失败。
6. 修正版本标识为 0.3.1，新增故障排查手册和 Windows Actions BAT/EXE 冒烟测试。
7. Linux 环境执行多层自动化、源代码启动和 HTTP 转换验证。**但不将 Linux 测试冒充 Windows CMD 原生执行或真实 Windows EXE 构建验证。**
