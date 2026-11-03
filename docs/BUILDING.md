# 🛠️ Building for Windows | Windows 编译说明

[简体中文](#简体中文) · [English](#english)

---

## 🇨🇳 简体中文

### 🧩 编译环境

- 64 位 Windows 10 / 11。
- 已安装 Python，版本需与 `requirements.txt` 中固定的 PySide6 版本兼容。
- 首次安装依赖时需要网络连接。
- 制作安装包还需要 Inno Setup 6：<https://jrsoftware.org/isinfo.php>。

### 📦 编译 Portable 文件夹版

在项目根目录双击 `build_portable.bat`。产物位于：

```text
dist\\MuMu-GPS-Controller-Portable\\
```

发布时必须提供整个文件夹，不能只复制 `MuMu-GPS-Controller-Portable.exe`。

### 🗂️ 编译单文件 EXE

在项目根目录双击 `build_windows.bat`。产物位于：

```text
dist\\MuMu-GPS-Controller.exe
```

单文件版启动时会先从 EXE 提取运行所需文件，因此启动速度可能比文件夹版稍慢。

### 🧰 编译普通 Windows 安装程序

1. 安装 Inno Setup 6。
2. 在项目根目录双击 `build_installer.bat`。
3. 脚本先使用 PyInstaller 构建文件夹版，再调用 Inno Setup 编译安装包。

产物位于：

```text
dist\\installer\\MuMu-GPS-Controller-Setup.exe
```

安装程序支持选择安装目录、创建开始菜单快捷方式、可选创建桌面快捷方式，以及 Windows 卸载入口。

### ✅ 发布前检查

- 在干净的 Windows 用户账户或另一台电脑上测试。
- 测试安装、启动、重新安装和卸载。
- 测试 MuMu 路径配置、多个实例、GPS 定位、Random Walk 和 Route Walk。
- 确认 `gps_config.json`、`gps_locations.json` 和 `gps_theme.json` 没有进入 Git 提交。
- 上传安装程序时，放在 GitHub Releases 的附件中，不要提交到源码仓库。

---

## 🇬🇧 English

### 🧩 Build environment

- 64-bit Windows 10 / 11.
- Python compatible with the PySide6 version pinned in `requirements.txt`.
- Internet access for installing dependencies on the first build.
- Inno Setup 6 is required only for the installer: <https://jrsoftware.org/isinfo.php>.

### 📦 Build the Portable folder

Run `build_portable.bat` from the project root. Output:

```text
dist\\MuMu-GPS-Controller-Portable\\
```

Distribute the complete folder. Do not copy only the EXE.

### 🗂️ Build the one-file executable

Run `build_windows.bat` from the project root. Output:

```text
dist\\MuMu-GPS-Controller.exe
```

The one-file build extracts its runtime files when launched, so startup may be slower than the folder build.

### 🧰 Build the Windows installer

1. Install Inno Setup 6.
2. Run `build_installer.bat` from the project root.
3. The script builds the folder application with PyInstaller, then compiles the installer with Inno Setup.

Output:

```text
dist\\installer\\MuMu-GPS-Controller-Setup.exe
```

The setup program supports a custom destination folder, a Start Menu shortcut, an optional Desktop shortcut, and a Windows uninstall entry.

### ✅ Pre-release checklist

- Test on a clean Windows account or another PC.
- Test installation, launch, reinstall, and uninstall.
- Test manager-path configuration, multiple instances, GPS teleport, Random Walk, and Route Walk.
- Ensure `gps_config.json`, `gps_locations.json`, and `gps_theme.json` are not committed.
- Upload the installer as a GitHub Release asset, not as a source file in the repository.
