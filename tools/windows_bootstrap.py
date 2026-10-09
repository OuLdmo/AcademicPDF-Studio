"""Windows environment bootstrap and EXE builder (stdlib only).

This program deliberately owns all non-ASCII user messages. Batch launchers
contain only ASCII, so they can be parsed by cmd.exe under CP936, CP950, etc.
"""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
RUNTIME_MODULES = ("pymupdf", "reportlab", "PIL", "requests", "tqdm")


def msg(s: str) -> None:
    """Log safely even when Windows CI redirects stdout through CP1252.

    A redirected Windows console may advertise cp1252 / cp936 even
    when our source is UTF-8. Never let diagnostic text crash installation
    or test collection: escape characters that the code page cannot encode.
    Chinese remains readable on terminals that support it.
    """
    output = sys.stdout
    encoding = getattr(output, "encoding", None) or "utf-8"
    try:
        safe = s.encode(encoding, errors="backslashreplace").decode(encoding)
    except (LookupError, UnicodeError):
        safe = s.encode("ascii", errors="backslashreplace").decode("ascii")
    print(safe, file=output, flush=True)


def execute(argv: list[str], *, cwd: Path = ROOT, check: bool = True) -> int:
    msg("$ " + subprocess.list2cmdline([str(a) for a in argv]))
    rc = subprocess.call([str(a) for a in argv], cwd=str(cwd))
    if rc and check:
        raise RuntimeError(f"执行命令失败（退出码 {rc}）：{argv[0]}")
    return rc


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def is_python_healthy(exe: Path) -> bool:
    if not exe.is_file():
        return False
    try:
        p = subprocess.run([str(exe), "-c", "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)"],
                           cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=12, check=False)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def get_runtime_python() -> Path:
    vpy = venv_python()
    if is_python_healthy(vpy):
        return vpy
    if VENV.exists():
        # Do not delete user data or silently replace a large installed environment.
        raise RuntimeError(
            f"检测到不完整或损坏的环境：{VENV}\n"
            "请先关闭软件，将 .venv 文件夹重命名为 .venv-old 后重新启动。"
        )
    msg("[1/3] 正在建立独立的 Python 环境（首次运行需要几分钟）……")
    execute([sys.executable, "-m", "venv", str(VENV)])
    if not is_python_healthy(vpy):
        raise RuntimeError("虚拟环境建立失败；请确保 Python 完整安装且包含 venv/pip。")
    return vpy


def modules_present(python: Path, modules: tuple[str, ...]) -> bool:
    check_code = "; ".join(f"import {m}" for m in modules)
    try:
        proc = subprocess.run([str(python), "-c", check_code], cwd=str(ROOT),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=35, check=False)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def install_requirements(python: Path, *, build: bool = False) -> None:
    # Build mode ALWAYS resolves its full dependency manifest. Old versions only
    # imported pytest/PyInstaller and incorrectly skipped missing numpy/skimage.
    if build:
        msg("[2/3] 验证 Windows 构建及测试依赖 (numpy/scikit-image included)…")
        execute([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                 "--prefer-binary", "-r", str(ROOT / "requirements-build.txt")])
        required = RUNTIME_MODULES + ("numpy", "skimage", "pytest", "PyInstaller")
        if not modules_present(python, required):
            raise RuntimeError("构建依赖检查失败：numpy/skimage/pytest/PyInstaller 未全部安装成功")
        return
    if modules_present(python, RUNTIME_MODULES):
        msg("[2/3] 基础运行依赖已就绪，跳过安装。")
        return
    msg("[2/3] 正在安装缺失的基础依赖……")
    execute([str(python), "-m", "pip", "install", "--disable-pip-version-check",
             "--prefer-binary", "-r", str(ROOT / "requirements.txt")])
    if not modules_present(python, RUNTIME_MODULES):
        raise RuntimeError("pip 完成但运行依赖缺失，请检查上方安装错误")


def check_layout() -> None:
    expected = [ROOT / "requirements.txt", ROOT / "studio_web.py",
                ROOT / "paperstudio" / "web_static" / "index.html",
                ROOT / "paperstudio" / "web_static" / "app.js",
                ROOT / "paperstudio" / "web_static" / "style.css"]
    missing = [str(f.relative_to(ROOT)) for f in expected if not f.is_file()]
    if missing:
        raise RuntimeError("工程缺少文件：" + ", ".join(missing) +
                           "。请将 ZIP 完整解压后再运行，不要在 ZIP 预览窗口内执行 BAT。")


def doctor() -> int:
    msg("AcademicPDF Studio Windows 环境诊断")
    msg(f"系统：{sys.platform}，Python：{sys.version.split()[0]}")
    msg(f"解释器：{sys.executable}")
    msg(f"项目目录：{ROOT}")
    msg(f"虚拟环境：{VENV}，存在：{VENV.exists()}")
    msg(f"系统 Python 版本符合要求：{(3, 11) <= sys.version_info[:2] < (3, 14)}")
    for name in RUNTIME_MODULES + ("numpy", "skimage", "pytest", "PyInstaller", "tkinter"):
        try:
            importlib.import_module(name)
            msg(f"  {name}: OK（当前解释器）")
        except Exception as e:
            msg(f"  {name}: 未安装/不可用：{type(e).__name__}")
    check_layout()
    if VENV.exists():
        msg(f"虚拟环境 Python 可用：{is_python_healthy(venv_python())}")
    return 0


def launch_app(python: Path, kind: str) -> int:
    if kind == "web":
        msg("[3/3] 正在启动本地网页服务……")
        msg("默认地址：http://127.0.0.1:8765/")
        msg("关闭本窗口可停止服务。首次加载浏览器后可上传 PDF。")
        return execute([str(python), str(ROOT / "studio_web.py")], check=False)
    if kind == "gui":
        if not modules_present(python, ("tkinter",)):
            raise RuntimeError("当前 Python 缺少 tkinter。请从 python.org 安装标准 Windows Python 版本。")
        msg("[3/3] 正在打开桌面图形界面……")
        return execute([str(python), str(ROOT / "studio_gui.py")], check=False)
    raise ValueError(kind)


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def smoke_exe(exe: Path) -> None:
    """Run *compiled* EXE on Windows, not source-only --help."""
    msg("[验证] EXE 静态资源与核心依赖自检……")
    execute([str(exe), "--self-test"])
    port = _get_free_port()
    with tempfile.TemporaryDirectory(prefix="academicpdf-exe-") as tmp:
        with subprocess.Popen([str(exe), "--no-browser", "--port", str(port),
                               "--data-dir", tmp], cwd=str(ROOT),
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) as p:
            started = False
            try:
                for _ in range(80):
                    if p.poll() is not None:
                        raise RuntimeError(f"EXE 提前退出，错误码：{p.returncode}")
                    try:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
                            import json
                            payload = json.load(response)
                            if payload.get("ok"):
                                started = True
                                break
                    except (OSError, ValueError):
                        pass
                    time.sleep(.5)
                if not started:
                    raise RuntimeError("EXE 启动超时，未通过 HTTP 健康检查。")
                msg("[验证] Windows EXE 真实 HTTP 健康检查通过。")
            finally:
                p.terminate()
                try:
                    p.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=5)


def build(python: Path, mode: str) -> int:
    if os.name != "nt":
        raise RuntimeError("Windows EXE 必须在 Windows x64 环境构建；Linux 上运行本脚本不会生成 Windows EXE。")
    install_requirements(python, build=True)
    msg("[构建] 先运行自动化测试……")
    execute([str(python), "-m", "pytest", "tests", "-q"])
    msg("[构建] 生成浏览器版 EXE（onedir 模式）……")
    execute([str(python), "-m", "PyInstaller", "--clean", "--noconfirm", "--onedir",
             "--name", "AcademicPDF-Web", "--add-data",
             "paperstudio/web_static;paperstudio/web_static",
             "--collect-submodules", "pymupdf", "studio_web.py"])
    exe = ROOT / "dist" / "AcademicPDF-Web" / "AcademicPDF-Web.exe"
    if not exe.is_file():
        raise RuntimeError(f"PyInstaller 未输出预期 EXE：{exe}")
    smoke_exe(exe)
    if mode == "build-all":
        msg("[构建] 生成命令行和桌面版 EXE……")
        execute([str(python), "-m", "PyInstaller", "--clean", "--noconfirm",
                 "--onefile", "--name", "AcademicPDF-Studio-CLI", "studio_cli.py"])
        execute([str(python), "-m", "PyInstaller", "--clean", "--noconfirm",
                 "--onefile", "--windowed", "--name", "AcademicPDF-Studio-GUI", "studio_gui.py"])
        cli_exe = ROOT / "dist" / "AcademicPDF-Studio-CLI.exe"
        gui_exe = ROOT / "dist" / "AcademicPDF-Studio-GUI.exe"
        if not cli_exe.is_file() or not gui_exe.is_file():
            raise RuntimeError("CLI/GUI 构建缺少 EXE 文件。")
        execute([str(cli_exe), "--help"])
        msg("CLI --help 已通过；GUI 实际打开窗口仍需人工验证。")
    msg(f"成功：{exe}")
    msg("分发时必须复制 dist/AcademicPDF-Web 整个目录，而不仅是单独的 EXE。")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AcademicPDF Studio Windows launcher and builder")
    parser.add_argument("--mode", choices=("web", "gui", "doctor", "build-web", "build-all", "install-argos"), default="web")
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 11) or sys.version_info >= (3, 14):
            raise RuntimeError("需要 Python 3.11/3.12/3.13。推荐使用 Python 3.11 x64。")
        if args.mode == "doctor":
            return doctor()
        if os.environ.get("ACADEMICPDF_LAUNCHER_SMOKE") == "1":
            # Windows CI validates all .bat/.cmd entrypoints without launching a
            # perpetual server or rebuilding virtual environments.
            check_layout()
            msg(f"CMD-LAUNCHER-SMOKE OK: mode={args.mode}")
            return 0
        check_layout()
        python = get_runtime_python()
        if args.mode in ("build-web", "build-all"):
            return build(python, args.mode)
        install_requirements(python)
        if args.mode == "install-argos":
            msg("[Argos] 安装引擎到软件专用虚拟环境（需联网）…")
            execute([str(python), "-m", "pip", "install", "--prefer-binary", "-r", str(ROOT / "requirements-free.txt")])
            msg("[Argos] 下载英文到中文语言模型（首次使用需要联网）…")
            execute([str(python), str(ROOT / "tools" / "install_argos_model.py")])
            return 0
        return launch_app(python, args.mode)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        msg("\n[ERROR] " + str(exc))
        msg("运行‘诊断环境.bat’可以查看安装状态。")
        msg("完整说明见：TROUBLESHOOTING.md")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
