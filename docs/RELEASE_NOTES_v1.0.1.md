# 🎉 MuMu GPS Controller v1.0.1 — Maintenance Release

## 🇬🇧 English

This maintenance release improves input persistence, route history accuracy, API result handling, and safe application shutdown.

### 🛠️ Fixes and improvements

- 💾 **Input persistence:** A fresh installation starts with empty manual coordinates and two empty Route Walk Stop rows. After users enter values, the latest manual coordinate and Route Walk draft are restored on the next launch.
- 🗺️ **Accurate route history:** A route is added to route history only after the first location update succeeds. Location history records the route start and each Stop only after the corresponding GPS update is accepted; future Stops are no longer pre-recorded.
- ✅ **Strict API result handling:** False or empty MuMu API results are treated as failures instead of being reported as successful updates.
- 🧵 **Safer shutdown:** Closing the application requests task cancellation and waits asynchronously until active worker threads finish before the window is destroyed.
- 🧹 **Cleanup:** Removed a duplicate attempt to install the Windows no-console subprocess patch.

### 📥 Upgrade

Download the v1.0.1 installer from GitHub Releases and run it over the existing installation. User data remains stored separately under the local application data directory.

MuMu Player is not included and must be installed separately.

---

## 🇨🇳 简体中文

这是一个维护更新版本，重点改善输入内容保存、路线历史准确性、API 返回值检查，以及软件关闭时的线程安全。

### 🛠️ 修复与改善

- 💾 **输入内容记忆：** 全新安装且没有缓存时，手动 GPS 坐标为空白，Route Walk 显示两个空白 Stop。用户输入内容后会保存最新手动坐标和路线草稿，下次启动自动恢复。
- 🗺️ **路线历史准确性：** 只有路线起点定位成功后才会保存路线记录。定位历史只记录成功设置的路线起点和实际到达的 Stop，不再提前把尚未到达的后续地点写入历史。
- ✅ **严格检查 API 返回值：** MuMu API 返回 False 或空结果时，按失败处理，不再误报定位成功。
- 🧵 **更安全的退出流程：** 关闭软件时会请求停止任务，并等待后台工作线程结束后再销毁窗口。
- 🧹 **代码清理：** 移除重复安装 Windows 隐藏控制台补丁的调用。

### 📥 更新方式

从 GitHub Releases 下载 v1.0.1 安装程序，直接覆盖安装现有版本即可。用户数据仍保存在独立的本地应用数据目录中。

安装包不包含 MuMu Player，用户需要自行安装。
