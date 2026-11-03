# 🚀 Publish on GitHub | GitHub 发布说明

[简体中文](#简体中文) · [English](#english)

---

## 🇨🇳 简体中文

建议将 **源代码** 放在 GitHub Repository，将编译好的 **安装程序** 放在 GitHub Releases。这样开发者可以查看源码，普通用户可以直接下载并安装。

### 1. 🏠 Repository 内容

项目主页：<https://github.com/jackson10222/MuMu-GPS-Controller>

上传源码、文档、图标和构建脚本，例如：

- `gps_controller_qt.py`
- `requirements.txt`
- `README.md`、`README.zh-CN.md`
- `LICENSE`、`.gitignore`
- `assets/`、`Languages/`、`docs/`
- `build_portable.bat`、`build_windows.bat`、`build_installer.bat`
- `MuMu-GPS-Controller-Setup.iss`

### 2. 🚫 不要上传

- `build/`、`dist/`
- `.venv/`、`venv/`、`__pycache__/`
- `gps_config.json`、`gps_locations.json`、`gps_theme.json`
- 个人日志、个人位置数据或本机路径配置
- 编译好的 EXE（建议放在 Release 附件）

### 3. 🏷️ 创建 Release

1. 打开 Repository 的 **Releases** 页面。
2. 点击 **Draft a new release**。
3. 由于 `v1.0.0` Release 已存在，请更新现有 Release，不要创建重复 Tag。
4. Release title：`MuMu GPS Controller v1.0.0`。
5. 将 `dist/installer/MuMu-GPS-Controller-Setup.exe` 拖到附件区域。
6. 从 `docs/RELEASE_NOTES_v1.0.0.md` 复制中英文发布说明。
7. 点击 **Publish release**。

普通用户只需要下载 `MuMu-GPS-Controller-Setup.exe`。Portable 文件夹版如果也要提供，需要先把整个 `dist/MuMu-GPS-Controller-Portable/` 文件夹压缩成 ZIP，再作为另一个 Release 附件上传。

### 4. 📝 Repository 简介

建议使用：

`A Windows GPS controller for MuMu Player 6/12 | MuMu 模拟器 GPS 定位控制工具（支持多开）`

### 5. ✅ 发布前检查

- 确认 README 中的仓库地址正确。
- 确认 `LICENSE` 与项目采用的 MIT License 一致。
- 确认没有提交个人 GPS 记录、模拟器路径或本机配置。
- 在另一台 Windows 电脑或干净 Windows 账户上安装并测试。
- 确认 Release 附件是最终编译完成的 Setup EXE，而不是中间文件。

---

## 🇬🇧 English

Keep the **source code** in the GitHub Repository and upload the compiled **installer** to GitHub Releases. Developers can inspect the code while regular users can download and install the application directly.

### 1. 🏠 Repository content

Repository: <https://github.com/jackson10222/MuMu-GPS-Controller>

Upload source code, documentation, assets, and build scripts, including the Python source, requirements, both README files, LICENSE, .gitignore, `assets/`, `Languages/`, `docs/`, the build scripts, and the Inno Setup recipe.

### 2. 🚫 Do not upload

- Build outputs such as `build/` and `dist/`.
- Virtual environments and Python caches.
- Personal JSON data such as `gps_config.json`, `gps_locations.json`, and `gps_theme.json`.
- Logs, personal GPS data, or machine-specific paths.
- Compiled EXE files in the source tree; attach them to a Release instead.

### 3. 🏷️ Create a Release

1. Open the repository's **Releases** page.
2. Select **Draft a new release**.
3. The `v1.0.0` Release already exists. Update the existing Release; do not create a duplicate tag.
4. Attach `dist/installer/MuMu-GPS-Controller-Setup.exe`.
5. Copy the bilingual notes from `docs/RELEASE_NOTES_v1.0.0.md`.
6. Publish the release.

For a Portable download, ZIP the entire `dist/MuMu-GPS-Controller-Portable/` folder and attach that ZIP as a separate asset.

### 4. 📝 Suggested repository description

`A Windows GPS controller for MuMu Player 6/12 | MuMu 模拟器 GPS 定位控制工具（支持多开）`

### 5. ✅ Pre-release checklist

- Ensure repository URLs are correct.
- Ensure the included MIT license is the one intended for the project.
- Do not commit personal GPS history, emulator paths, or local settings.
- Test setup on another Windows PC or a clean Windows account.
- Attach the final Setup EXE, not an intermediate build artifact.
