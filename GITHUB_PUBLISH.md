# GitHub 上传说明

推荐独立仓库：`OuLdmo/AcademicPDF-Studio`，而不是混入 `wechat2md-fidelity-clipper` 等无关仓库。

## 创建仓库

1. 打开 https://github.com/new，Owner 选择 `OuLdmo`，仓库名填写 `AcademicPDF-Studio`。
2. 按你的要求选择 Public / Private。**公开发布前请先确认论文附件、第三方组件许可及模型许可**。
3. 建议仓库初始不勾选 README、.gitignore 或 License，因为工程已包含这些文件。
4. 新仓库创建后，返回对话提供仓库链接，以便通过已连接的 GitHub 账户完成提交并核对。

## 也可以直接在你的 Windows Git Bash / PowerShell 推送

进入本发布目录（即 README.md、paperstudio/ 所在的根目录）：

```powershell
git init -b main
git add .
git commit -m "Initial import: AcademicPDF Studio v0.4.1 with issues and roadmap"
git remote add origin https://github.com/OuLdmo/AcademicPDF-Studio.git
git push -u origin main
```

需要安装 Git 并在推送时完成 GitHub 登录认证（HTTPS 不再接受账户密码作为 Git 认证）。上述命令仅在**目标仓库已经创建且为空**时直接适用。

上传后在仓库 Actions 页面：普通 push 会触发 `Python tests`（Linux+Windows）；在 Actions 中手动运行 `Build Windows Web EXE (CMD and HTTP smoke)` 可以生成 Windows x64 构建产物供下载。此构建配置的通过与否仍需以 GitHub 实际运行结果为准。

## Windows 一键推送脚本（需要先创建空仓库）

如果 Git for Windows 已安装、GitHub 登录配置完成，也可以直接双击 `Publish-To-GitHub.cmd`，确认后会将本项目提交并推送至 **`OuLdmo/AcademicPDF-Studio`**。为避免误传，脚本会拒绝已有不同 `origin` 地址的文件夹。它不会在 GitHub 上创建仓库，也不会替你授权登录。需要使用其他仓库名请自行修改脚本中的目标仓库地址，或使用上面的 Git 命令。
