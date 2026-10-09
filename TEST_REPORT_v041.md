# AcademicPDF Studio v0.4.1 — 故障与回归测试报告

- 日期：2026-10-09
- 工程来源：v0.4.0 原始 ZIP；在相同代码基础上进行修复，不是重新创建的演示项目。
- 实测环境：Linux x86_64、Python 3.13、PyMuPDF 1.26.7；与用户 Windows 3.11 环境不同。
- 关键限制：未获取产生错误的真实 PDF；**没有**实际复现截图中的 MuPDF 原始错误，也没有在 Windows 原机执行 BAT 或预编译 EXE。

## 测试结论

| 测试类别 | 本次结果 | 验收范围 |
|---|---|---|
| `python -m pytest tests -q` | **51/51 通过** | 解析、翻译适配器、HTTP、Windows 脚本静态检查、故障注入 |
| `python -m compileall -q paperstudio` | 通过 | 全部工程核心 Python 模块语法 |
| 静态导入 | 通过 | `studio_gui`、parser、pipeline、web、equations、figures 导入均不输出 fitz 弃用警告 |
| 复杂 PDF 函数测试 | 通过，**无同文案复现** | 合成 1,200 子函数 PDF 在本测试 MuPDF 版本正常提取正文与导出三格式 |
| MuPDF 错误注入 | 通过 | 重复 19 次同类错误被汇总为一个结构化诊断条目，原次数可追溯 |
| 结构化提取失败 | 通过 | 降级纯文本、标记 needs_review、无错误坐标 |
| 页面失败 | 通过 | 保留失败页标记，后续页面继续，失败页不写成功缓存 |
| 矢量/快照降级 | 通过 | 风险信号下跳过操作并写入告警 |
| PDF 源页保护 | 通过 | bbox 缺失的译文不会触发覆盖整页的 redaction |
| 加密/截断 PDF | 通过 | 明确异常，不制造成功假象 |
| 2 份并发 PDF | 通过 | 两个任务独立完成，没有错误日志串扰 |
| Web 子进程 HTTP | 通过 | 独立启动、健康检查、PDF 上传、任务进度 100%、下载 ZIP（含 MD/PDF/TXT/PNG） |
| CLI 双栏样例 | 通过 | `--engine none --pdf-layout overlay` 完成三格式导出 |
| Windows 原生 BAT | **未执行** | 缺少 Windows/Win32 命令解释器，仅通过代码静态测试 |
| 预编译 Windows EXE | **未构建** | 需 Windows x64 运行 PyInstaller 和真实 HTTP 测试 |

## 独立指标：IEEE-like 合成测试

| 示例 | MD 局部标注结构得分 | 模拟中文 PDF SSIM | 粗粒度布局 IoU | 文本溢出块 |
|---|---:|---:|---:|---:|
| `ieee_crosspage_table.pdf` | 1.000 | 0.97654 | 0.96240 | 1 |
| `ieee_two_column.pdf` | 1.000 | 0.97263 | 0.92920 | 1 |
| `ieee_vectors_equations.pdf` | 1.000 | 0.96787 | 0.93959 | 2 |

结构指标只计算已有人工标注的少量任务；PDF SSIM 基于模拟中文替换，不评价实际翻译、公式 OCR 准确率，也不能说明任意 IEEE PDF 完整无损。见 `benchmark/results/benchmark_report.json`。

## 用户问题的诊断覆盖方式

- 弃用警告：**直接修复**，所有工程 `.py` 中的旧式 `import fitz` 已消除。
- `too many sub-functions in stitching function`：**错误可见性和容错修复**。程序把 MuPDF 自身的底层消息保留在 `manifest.json`，必要时放弃可疑图形重放并继续文本提取与后续页面，但不会改写或修复 PDF 内部 function 对象。
- 模拟故障不等于真实重现：需要原始 PDF / 脱敏问题页，才能验证这一特定文件是否在新版本下安全且完整。
- `pymupdf_layout` 提示属于 PyMuPDF 的可选增强建议，不等于运行失败；使用 Docling 或其他解析路线应单独验证。

## 重现命令

```powershell
python -m pip install -r requirements-build.txt
python -m pytest tests -q
python studio_web.py --self-test
python -m paperstudio benchmark/fixtures/ieee_two_column.pdf -o output --engine none --pdf-layout overlay
python benchmark/run_benchmark.py
```

从网页上下载 `AcademicPDF-results.zip` 后，可检查每个论文子目录中的 `manifest.json`。
