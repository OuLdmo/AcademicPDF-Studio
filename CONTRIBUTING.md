# 参与开发 / Contributing

1. 先查看 [KNOWN_ISSUES.md](KNOWN_ISSUES.md)、[ROADMAP.md](ROADMAP.md)，避免重复问题。
2. 创建独立分支；提交一个问题对应一个 PR，优先提交小规模、可复现的测试。
3. 环境安装：`python -m pip install -r requirements-build.txt`，然后 `python -m pytest tests -q`。Windows 启动器的真实验证必须在 Windows CMD 中进行。
4. PDF 解析问题请提供：最小复现 PDF（公开版权/使用权明确，或经脱敏）、页号、PyMuPDF 版本、期望输出、实际 Markdown/截图、`manifest.json` 的非敏感诊断片段。
5. 质量 PR 请同时附 Markdown 结构指标（优先）与独立 PDF 视觉报告，明确是否为真实论文或合成数据。
6. 不上传机密论文、API 密钥、token 或 `.venv`；不要将收费第三方 API 集成测试默认加入 PR 自动执行。
7. 执行 `python -m compileall -q paperstudio` 和全量测试后申请评审。
