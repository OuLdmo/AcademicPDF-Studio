"""Regression checks for CP936/CP950-safe Windows CMD launchers.

These checks run on Linux CI too; Windows-native execution is checked in
.github/workflows/build-windows.yml on the windows-2022 runner.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from tools import windows_bootstrap as wb
from paperstudio import web

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", [
    "启动网页版.bat", "启动图形界面.bat", "构建Windows_网页版EXE.bat",
    "构建Windows_EXE.bat", "诊断环境.bat",
    "Start-Web.cmd", "Start-Desktop.cmd", "Build-Windows-Web.cmd",
    "Build-Windows-All.cmd", "Diagnose-Windows.cmd", "tools/bootstrap.cmd", "Install-Argos.cmd",
])
def test_cmd_script_is_cp936_safe(name):
    content = (ROOT / name).read_bytes()
    assert content.startswith(b"@echo off\r\n")
    assert all(byte < 128 for byte in content), "BAT must not contain raw UTF-8 Chinese text"
    assert content.count(b"\n") == content.count(b"\r\n"), "Use Windows CRLF newlines"
    assert b"chcp" not in content.lower(), "Avoid changing the code page in cmd.exe"
    assert b"%~dp0" in content, "Always use a path relative to the BAT itself"


def test_bootstrap_python_available_offline():
    proc = subprocess.run([sys.executable, str(ROOT / "tools/windows_bootstrap.py"),
                           "--mode", "doctor"], cwd=ROOT,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=20)
    assert proc.returncode == 0, proc.stderr
    assert "AcademicPDF Studio" in proc.stdout


@pytest.mark.parametrize("legacy_encoding", ["cp1252", "ascii", "cp936"])
def test_doctor_under_legacy_windows_stdout_encoding(legacy_encoding):
    """Prevent a UnicodeEncodeError on non-UTF8 Windows CI consoles."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = f"{legacy_encoding}:strict"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/windows_bootstrap.py"), "--mode", "doctor"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=25,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"AcademicPDF Studio" in proc.stdout
    if legacy_encoding in ("cp1252", "ascii"):
        assert b"\\u" in proc.stdout, "Han characters should be escaped"


def test_launcher_smoke_under_legacy_windows_stdout_encoding():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252:strict"
    env["ACADEMICPDF_LAUNCHER_SMOKE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/windows_bootstrap.py"),
         "--mode", "build-web"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"CMD-LAUNCHER-SMOKE OK" in proc.stdout


def test_web_self_test_ok():
    result = subprocess.run([sys.executable, str(ROOT / "studio_web.py"), "--self-test"],
                            cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "SELF-TEST OK" in result.stdout


def test_corrupt_venv_is_not_silently_deleted(monkeypatch, tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    monkeypatch.setattr(wb, "VENV", venv)
    with pytest.raises(RuntimeError, match="重命名"):
        wb.get_runtime_python()
    assert venv.is_dir()


def test_import_probe_failure_is_explicit(tmp_path):
    assert wb.modules_present(tmp_path / "does-not-exist", ("fitz",)) is False


def test_source_layout_check():
    wb.check_layout()


def test_build_rejected_outside_windows():
    if sys.platform == "win32":
        pytest.skip("Negative scenario requires non-Windows")
    with pytest.raises(RuntimeError, match="Windows x64"):
        wb.build(Path(sys.executable), "build-web")


def test_occupied_port_reused_when_existing_academicpdf(monkeypatch):
    monkeypatch.setattr(web, "create_server", Mock(side_effect=OSError(98, "used")))
    monkeypatch.setattr(web, "_existing_local_server", lambda host, port: port == 8765)
    assert web.main(["--no-browser"]) == 0
    web.create_server.assert_called_once()


def test_explicit_occupied_port_exits_with_error(monkeypatch, capsys):
    monkeypatch.setattr(web, "create_server", Mock(side_effect=OSError(98, "used")))
    monkeypatch.setattr(web, "_existing_local_server", lambda host, port: False)
    assert web.main(["--no-browser", "--port", "8877"]) == 2
    assert "8877" in capsys.readouterr().out


def test_default_occupied_port_uses_second(monkeypatch):
    class FakeServer:
        server_address = ("127.0.0.1", 8766)
        service = Mock(data_dir=ROOT)
        def serve_forever(self, **kwargs):
            pass
        def shutdown(self):
            pass
        def server_close(self):
            pass
    fake_server = FakeServer()
    def fake_create_server(*, host, port, data_dir=None):
        if port == 8765:
            raise OSError(98, "port occupied")
        assert port == 8766
        return fake_server
    monkeypatch.setattr(web, "create_server", fake_create_server)
    monkeypatch.setattr(web, "_existing_local_server", lambda host, port: False)
    assert web.main(["--no-browser"]) == 0
    fake_server.service.pool.shutdown.assert_called_once()


def test_non_port_startup_error_not_masked(monkeypatch, capsys):
    monkeypatch.setattr(web, "create_server", Mock(side_effect=PermissionError(13, "no permission")))
    assert web.main(["--no-browser"]) == 2
    assert "ERROR" in capsys.readouterr().out
