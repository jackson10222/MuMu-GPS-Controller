# 📍 MuMu GPS Controller

[English README](README.md) · **简体中文**

一款 Windows 桌面工具，用于控制 **MuMu Player 6 和 MuMu Player 12** 的模拟器 GPS 虚拟位置。支持手动定位、随机移动、多站点路线行走、收藏地点、定位历史，以及同时控制多个模拟器实例。

> ⚠️ **重要说明：** 本项目是社区开发工具，并非 MuMu／网易官方软件。MuMu Player 需要用户自行安装。实际兼容性取决于用户安装的 MuMu 版本、`MuMuManager.exe` 和第三方 MuMu Python API。

---

## ✨ 功能介绍

- 📍 **手动 GPS 定位：** 输入纬度、经度，粘贴 Google Maps 链接，或解析坐标。
- 🖥️ **多开模拟器控制：** 配置多个 MuMu 实例编号，一次将 GPS 更新发送到所有已配置实例。
- 🚶 **随机移动（Random Walk）：** 定位后可在指定半径和持续时间内随机移动。
- 🗺️ **路线行走（Route Walk）：** 添加多个 Stops，在地点之间按设定速度插值移动；显示进度并支持暂停、继续和停止。
- ⭐ **收藏地点：** 保存、整理和快速使用常用坐标。
- 🕘 **定位历史与路线历史：** 记录之前的定位和路线操作。
- 🔁 **重复定位确认：** 如果准备再次发送的手动坐标已存在于定位历史，会显示上次记录时间并询问是否继续。
- 🌐 **三种界面语言：** 简体中文、繁体中文和英文。
- 🎨 **主题设置：** 使用预设颜色主题，或自定义界面颜色。

## 🧩 支持环境

- Windows 10 或 Windows 11，64 位。
- MuMu Player 6 或 MuMu Player 12。
- 对应 MuMu 安装目录中的 `MuMuManager.exe`。
- 从源码运行：需要安装与 `requirements.txt` 中 PySide6 版本兼容的 Python。
- 自行编译 Windows 程序：需要 PyInstaller（提供的 `.bat` 脚本会自动安装）。
- 自行制作 Windows 安装包：需要 Inno Setup 6。

本项目目前使用 PySide6 6.12.0 在 Windows 环境中开发和打包。普通用户使用已经编译好的程序时，不需要另外安装 Python。MuMu Player 仍需自行安装。

## 📥 下载与安装

普通用户请前往 [GitHub Releases](https://github.com/jackson10222/MuMu-GPS-Controller/releases/latest) 下载最新的 **`MuMu-GPS-Controller-Setup.exe`**。

1. 双击运行 `MuMu-GPS-Controller-Setup.exe`。
2. 选择软件安装目录。
3. 选择是否创建桌面快捷方式；安装程序也会创建开始菜单快捷方式。
4. 完成安装后，可以从桌面或开始菜单启动软件。
5. 打开软件设置，配置 MuMu 管理器路径和模拟器实例编号。

安装包不包含 MuMu Player，用户需要自行安装 MuMu Player。

## ⚙️ 配置 MuMu 模拟器

1. 启动 MuMu Player，并打开 MuMu 多开器。
2. 在本软件中打开 **设置 → 模拟器设置（Emulator Settings）**。
3. 检查自动识别的 **MuMuManager Path**。如果路径为空或不正确，点击 **Browse…**，手动选择 `MuMuManager.exe`。
4. 添加需要控制的模拟器实例编号。编号就是 MuMu 多开器中显示的实例编号；它不是自动枚举当前运行中的模拟器。
5. 点击 **Save Emulator Settings** 保存设置。
6. 点击 **Test Connection**，检查 API 是否能够选择这些实例。该测试只确认 API 配置和实例选择，不代表模拟器一定正在运行。

默认实例编号为 `0`，可以在设置中添加或删除编号。例如添加 `1`、`2`、`3`、`4`，即可同时向这四个实例发送相同的 GPS 更新。若批量调用失败，程序会尝试逐个实例诊断，并报告成功或失败的编号。


### 🔌 通过 ADB 端口确认模拟器编号（重要）

本软件「模拟器实例编号」输入框需要填写的是 **MuMu 多开器中的实例索引（Index）**，**不是 ADB 端口号**。

**MuMu Player 12 查看 ADB 端口的方法：**

1. 查看主模拟器：打开模拟器窗口右上角菜单，选择 **问题诊断／诊断信息（Troubleshooting / Diagnostics）**，找到 **ADB 调试端口（ADB debugging port）**。
2. 查看多开模拟器：打开 **MuMu 多开器 12**，找到正在运行的模拟器，在该实例所在行点击 **ADB 图标**，即可查看它的 ADB 端口。
3. 记下对应端口。要确认本软件应该填写哪个编号，请查看 MuMu 多开器列表中该模拟器名称最前面的数字。MuMu API 作者说明，列表最前面的数字就是 `select(index)` 使用的模拟器索引。

**通过 API 核对「编号 ↔ ADB 端口」：**

MuMu API 提供 `adb.get_connect_info()`，可以查询指定实例编号对应的 ADB IP 和端口：

```python
from mumu.mumu import Mumu

mumu = Mumu(r"C:\\Program Files\\Netease\\MuMu Player 12\\shell\\MuMuManager.exe")
print(mumu.select([0, 1, 2, 3]).adb.get_connect_info())
```

输出示例（以下端口仅为示例，实际端口可能不同）：

```python
{
    "0": ("127.0.0.1", 16384),
    "1": ("127.0.0.1", 16416),
    "2": ("127.0.0.1", 16448),
    "3": ("127.0.0.1", 16480),
}
```

将 MuMu 界面显示的 ADB 端口与输出结果对照，就能确认它对应哪个实例编号。

**注意：本软件要填写匹配的实例编号（例如 `3`），不是 ADB 端口（例如 `16480`）。** ADB 端口会因 MuMu 版本及本机端口占用情况而变化，不要只依赖固定端口公式。

MuMu Player 6 的 ADB 端口显示位置可能因版本不同而有所差异，可以在模拟器的诊断／设置页面或多开器中查看；本软件要填写的仍然是 MuMu 多开器中显示的实例编号。

## 🧭 GPS 功能使用方法

### 📍 手动 GPS 定位

1. 打开 **GPS Location（GPS 定位）**。
2. 输入纬度和经度，粘贴 Google Maps 链接，或解析 `纬度,经度` 格式的坐标。
3. 可以选择启用 Random Walk，并设置持续时间和移动半径。
4. 点击 **Set Virtual Location（设置虚拟定位）**。

MuMu API 的调用顺序是 `androidEvent.location(longitude, latitude)`。**第一个参数是经度，第二个参数是纬度**，不要交换顺序。

如果准备发送的坐标已经存在于定位历史中，程序会先询问是否再次定位，并显示上次记录时间。

### 🚶 随机移动（Random Walk）

在 GPS 定位页面启用 Random Walk 后再执行定位。程序会在设定的时间内，围绕起始点并限制在指定半径内移动。正常完成后会尝试返回起始位置；手动停止时则保留最后位置。

### 🗺️ 路线行走（Route Walk）

1. 打开 **Route Walk（路线行走）**。
2. 每个 Stop 输入一组坐标或一个 Google Maps 链接。至少需要两个有效地点。
3. 设置移动速度和更新间隔。
4. 开始路线行走，可以使用暂停／继续或停止控制。

路线移动是在用户提供的地点之间进行坐标插值，并不是道路导航功能，不会沿真实道路自动规划路线。

## 🔒 数据保存与隐私

软件配置和用户数据与程序安装目录分开保存。对于打包后的 EXE，通常保存于：

```text
%LOCALAPPDATA%\\MuMu GPS Controller\\
```

其中可能包含：

- `gps_config.json`：MuMuManager 路径和模拟器实例编号。
- `gps_locations.json`：收藏地点、定位历史、路线历史，以及输入草稿／缓存。
- `gps_theme.json`：主题偏好设置。

直接运行 Python 源码时，数据文件保存在 Python 脚本所在目录。卸载程序时不会主动删除用户数据目录，重新安装后仍可继续使用。

🚫 **请不要把这些个人数据文件上传到 GitHub。** 它们可能包含个人位置和本机路径。项目中的 `.gitignore` 已默认排除这些文件。

## 🧑‍💻 从源码运行

```powershell
git clone https://github.com/jackson10222/MuMu-GPS-Controller.git
cd MuMu-GPS-Controller
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python gps_controller_qt.py
```

如果 PowerShell 阻止虚拟环境启用，可以使用命令提示符（CMD）：

```bat
.venv\\Scripts\\activate.bat
```

## 🛠️ 编译 Windows 程序

请在 64 位 Windows 电脑的项目根目录运行以下脚本。每个脚本都会自动安装 `requirements.txt` 中的依赖和 PyInstaller。

| 脚本 | 输出位置 | 发布时需要提供什么 |
| --- | --- | --- |
| `build_portable.bat` | `dist\\MuMu-GPS-Controller-Portable\\` | 必须提供**整个文件夹**，不能只提供 EXE。 |
| `build_windows.bat` | `dist\\MuMu-GPS-Controller.exe` | 提供单一 EXE 文件。 |
| `build_installer.bat` | `dist\\installer\\MuMu-GPS-Controller-Setup.exe` | 需要 Inno Setup 6，生成普通 Windows 安装程序。 |

安装程序允许用户选择安装目录，创建开始菜单快捷方式，提供默认勾选的桌面快捷方式，注册 Windows 卸载入口，并可在安装结束后启动软件。安装配置文件为 `MuMu-GPS-Controller-Setup.iss`。

中文安装界面的语言文件已放在 `Languages/` 中，制作安装包时不需要另外在 Inno Setup 安装目录里安装中文语言文件。尚未翻译的部分安装提示会回退显示英文。

## 🧯 常见问题

| 问题 | 建议检查方式 |
| --- | --- |
| 找不到 `MuMuManager.exe` | 打开设置，手动选择实际安装目录中的 `MuMuManager.exe`。 |
| 某个实例的 Test Connection 失败 | 检查 MuMu 多开器中的实例编号和管理器路径，并启动对应模拟器。 |
| 一个或多个实例 GPS 更新失败 | 根据错误信息检查具体实例编号。API 选择成功不代表模拟器正在运行或一定接受定位。 |
| GPS 位置没有变化 | 确认 MuMu Player 已启动、实例编号正确，并检查 MuMu API 与管理器之间的通信。 |
| 软件无法启动 | Portable 版本必须从完整文件夹运行，不能把 EXE 单独复制出来；也可以尝试重新运行安装程序。 |

## 📚 更多文档

- [🛠️ Windows 编译说明](docs/BUILDING.md)
- [🚀 GitHub 发布说明](docs/GITHUB_PUBLISHING.md)
- [📝 v1.0.0 版本发布说明](docs/RELEASE_NOTES_v1.0.0.md)

## 🧾 第三方组件

本项目使用 PySide6、Requests、OpenCC 和 `mumu-python-api-wlkjyy` 及其依赖。各第三方组件仍遵循其各自的许可证；请查看对应项目或软件包页面。

## 📄 许可证

本项目源代码采用 [MIT License](LICENSE)。MIT 允许他人使用、复制、修改、合并、发布、分发、再授权或销售本项目代码，但需要保留原有版权声明和许可证文本。具体法律条款以 `LICENSE` 文件为准。此许可证不会改变第三方库、图标素材或其他资源各自的许可证。
