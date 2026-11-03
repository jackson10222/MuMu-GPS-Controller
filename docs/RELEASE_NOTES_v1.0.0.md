# 🎉 MuMu GPS Controller v1.0.0 — Initial Public Release

## 🇬🇧 English

The public Windows release of MuMu GPS Controller for MuMu Player 6 and MuMu Player 12.

### ✨ Features

- 📍 Manual GPS teleport using coordinates or Google Maps links.
- 🖥️ Multi-instance GPS updates for configured MuMu emulator indexes.
- 🚶 Optional Random Walk with duration and radius controls.
- 🗺️ Multi-stop Route Walk with progress, pause/resume, and stop controls.
- ⭐ Saved locations, favourites, location history, and route history.
- 🔁 Confirmation before manually sending a coordinate already present in location history.
- 🌐 Simplified Chinese, Traditional Chinese, and English interface.
- 🎨 Customizable colour themes.
- 💾 Manual coordinates and Route Walk drafts are saved and restored on relaunch. A fresh installation starts with empty coordinate fields and two empty Route Walk stops.

### 🛠️ Reliability fixes included

- Route history is saved only after the starting GPS update succeeds.
- Location history records the route start and each stop only after the corresponding GPS update is accepted; future stops are not pre-recorded.
- False or empty MuMu API results are treated as failures instead of successful updates.
- Closing the application requests cancellation and waits for active worker threads to finish before destroying the window.
- JSON user data is written atomically and a valid previous copy is retained as a backup; a backup can be restored if the primary data file is damaged.

### 📥 Installation

Download `MuMu-GPS-Controller-Setup.exe`, run it, choose an installation directory, and configure the MuMuManager path and instance indexes in application Settings.

MuMu Player is not included and must be installed separately.

### ⚠️ Notes

This is a community project and is not an official MuMu / NetEase application. Runtime compatibility should be verified with the installed MuMu Player version and emulator instances.

---

## 🇨🇳 简体中文

这是 MuMu GPS Controller 面向 Windows 用户的公开版本，适用于 MuMu Player 6 和 MuMu Player 12。

### ✨ 功能介绍

- 📍 支持输入坐标或粘贴 Google Maps 链接进行 GPS 虚拟定位。
- 🖥️ 支持同时向多个已配置的 MuMu 模拟器实例发送 GPS 更新。
- 🚶 支持设置持续时间和半径的 Random Walk（随机移动）。
- 🗺️ 支持多站点 Route Walk（路线行走），显示进度并支持暂停、继续和停止。
- ⭐ 支持收藏地点、常用地点、定位历史和路线历史。
- 🔁 再次发送已经存在于定位历史中的手动坐标前，会先询问用户是否继续。
- 🌐 支持简体中文、繁体中文和英文界面。
- 🎨 支持预设颜色主题及自定义颜色。
- 💾 手动坐标和 Route Walk 草稿会保存，并在下次启动时恢复。全新安装且没有缓存时，手动坐标为空白，路线显示两个空白 Stop。

### 🛠️ 稳定性修复

- 只有路线起点 GPS 设置成功后，才会保存路线历史。
- 定位历史只记录成功设置的路线起点和实际到达的 Stop，不再提前把尚未到达的后续地点写入历史。
- MuMu API 返回 False 或空结果时按失败处理，不再误报定位成功。
- 关闭软件时会请求停止任务，并等待后台工作线程结束后再销毁窗口。
- 用户 JSON 数据采用原子写入，并保留有效的上一份备份；主数据文件损坏时可以尝试从备份恢复。

### 📥 安装方式

下载 `MuMu-GPS-Controller-Setup.exe`，运行安装程序并选择安装目录。安装完成后，在软件设置中配置 MuMuManager 路径和需要控制的模拟器实例编号。

安装包不包含 MuMu Player，用户需要自行安装。

### ⚠️ 说明

本项目为社区开发工具，并非 MuMu／网易官方应用。实际兼容性需要结合用户安装的 MuMu Player 版本及模拟器实例进行验证。
