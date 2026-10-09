# AcademicPDF Studio v0.4.2 — 2026-10-09

### Windows CI 编码修复

- 修复 Windows Actions 的 CP1252 stdout 严格编码环境下，诊断日志直接输出中文触发 `UnicodeEncodeError` 的问题。
- 新增 CP1252、ASCII、CP936 的跨进程编码回归测试，以及启动入口的旧代码页 smoke 测试。
- Windows CI 新增显式 CP1252 诊断步骤。

### 仓库清理

- 删除旧版重复安装/发布说明、仓库初始化辅助脚本以及未引用的预览截图。
- 保留实际运行入口、测试集、双栏基准夹具、主要源代码与 Windows 构建工作流。
- 统一版本为 v0.4.2；新增 `QUICKSTART.md`、`TROUBLESHOOTING.md`。

### 仍需优化

独立 Windows EXE 分发验收、真实复杂论文 OCR/表格与 PDF 视觉一致性尚未完成，参见 `KNOWN_ISSUES.md`。
