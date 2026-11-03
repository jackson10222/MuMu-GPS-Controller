# 📍 MuMu GPS Controller

[简体中文说明](README.zh-CN.md) · **English**

A Windows desktop application for controlling GPS locations on **MuMu Player 6 and MuMu Player 12**. It supports manual teleportation, random walking, multi-stop route walking, saved locations, location history, and simultaneous control of multiple emulator instances.

> ⚠️ **Important:** This is a community project, not an official MuMu / NetEase product. MuMu Player must be installed separately. Compatibility depends on the installed MuMu version, `MuMuManager.exe`, and the third-party MuMu Python API.

---

## ✨ Features

- 📍 **Manual GPS teleport** — enter latitude/longitude, paste a Google Maps link, or parse a coordinate pair.
- 🖥️ **Multi-instance control** — configure multiple MuMu instance indexes and send GPS updates to all configured instances.
- 🚶 **Random walking** — optionally move around the starting point within a configured radius and duration.
- 🗺️ **Route walking** — add multiple stops, interpolate movement between them, monitor progress, pause/resume, and stop.
- ⭐ **Saved locations** — save, organize, and quickly reuse favourite places.
- 🕘 **Location and route history** — keep a record of previous location and route operations.
- 🔁 **Duplicate-location confirmation** — before manually sending a coordinate already in location history, see its last recorded time and confirm.
- 🌐 **Three UI languages** — Simplified Chinese, Traditional Chinese, and English.
- 🎨 **Themes** — choose a built-in colour theme or customize interface colours.
- 🔎 **Manager-path discovery** — check common MuMu installation folders without scanning the entire disk; manual browsing is available.
- 🪟 **Windows integration** — application/taskbar icon, installer, Start Menu shortcut, optional Desktop shortcut, and uninstaller.
- 🫥 **Reduced console flashing** — apply a scoped Windows no-console launch patch to the MuMu API command runner when supported by the installed API layout.

## 🧩 Supported environment

- Windows 10 or Windows 11 (64-bit).
- MuMu Player 6 or MuMu Player 12.
- A valid `MuMuManager.exe` from the installed MuMu Player package.
- For running from source: Python compatible with the pinned PySide6 release in `requirements.txt`.
- For building Windows executables: PyInstaller (installed automatically by the supplied `.bat` scripts).
- For building the installer: Inno Setup 6.

The project has been built in a Windows environment with PySide6 6.12.0. Runtime compatibility should be verified with the user's installed MuMu version and emulator instances. End users do **not** need Python when using a packaged build.

## 📥 Download and install

For normal users, download the latest **`MuMu-GPS-Controller-Setup.exe`** from [GitHub Releases](https://github.com/jackson10222/MuMu-GPS-Controller/releases/latest).

1. Run `MuMu-GPS-Controller-Setup.exe`.
2. Choose the installation directory.
3. Choose whether to create a Desktop shortcut. A Start Menu shortcut is also created.
4. Finish setup and launch the application from the Desktop or Start Menu.
5. Open **Settings** and configure the MuMu manager path and emulator instance indexes.

MuMu Player itself is not included in this installer and must be installed separately.

## ⚙️ Configure MuMu Player

1. Start MuMu Player and open its Multi-instance Manager.
2. In the application, open **Settings → Emulator Settings**.
3. Check the detected **MuMuManager Path**. If it is incorrect or empty, click **Browse…** and select `MuMuManager.exe`.
4. Add the instance indexes you want to control. An index is the number shown by MuMu's Multi-instance Manager; it is not an automatic list of currently running emulators.
5. Click **Save Emulator Settings**.
6. Use **Test Connection** to check that the API can select the configured indexes. This test does not prove that every emulator is currently running.

You can add or remove indexes in Settings. For example, configure `1`, `2`, `3`, and `4` to control those four instances together. All configured indexes receive the same GPS update. If an update fails, the application attempts per-index diagnostics and reports which indexes succeeded or failed.

## 🧭 Use GPS features

### 📍 Manual GPS teleport

1. Open **GPS Location**.
2. Enter latitude and longitude, paste a Google Maps link, or parse a `latitude,longitude` pair.
3. Optionally enable Random Walk and configure its duration and radius.
4. Click **Set Virtual Location**.

The MuMu API call uses `androidEvent.location(longitude, latitude)`. **Longitude is the first argument; latitude is the second.**

If the same coordinate is already recorded in location history, the app asks whether you want to send it again and displays the previous record time.

### 🚶 Random Walk

Enable Random Walk on the GPS Location page before teleporting. The app moves around the starting point within the configured radius for the selected duration. When it finishes normally, it sends the location back to the starting point. Stopping the task keeps the last position.

### 🗺️ Route Walk

1. Open **Route Walk**.
2. Enter a coordinate pair or Google Maps link for each stop. At least two valid stops are required.
3. Set the movement speed and update interval.
4. Start the route. Use **Pause / Resume** or **Stop** as needed.

Route movement is interpolated between the supplied points. It is not a road-navigation service and does not follow real streets.

## 🔒 Data and privacy

The application stores configuration and user data separately from the installation directory. For packaged builds, the normal data directory is:

```text
%LOCALAPPDATA%\\MuMu GPS Controller\\
```

Files may include:

- `gps_config.json` — MuMuManager path and emulator instance indexes.
- `gps_locations.json` — saved locations, location history, route history, and input caches.
- `gps_theme.json` — theme preferences.

When running the source code directly, data files are stored beside the Python script. The installer does not intentionally delete the user data directory during uninstall, so preferences can remain available if the app is installed again.

🚫 **Do not commit these JSON files to GitHub.** They can contain personal locations and machine-specific paths. The included `.gitignore` excludes them.

## 🧑‍💻 Run from source

```powershell
git clone https://github.com/jackson10222/MuMu-GPS-Controller.git
cd MuMu-GPS-Controller
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python gps_controller_qt.py
```

If PowerShell blocks virtual-environment activation, use Command Prompt:

```bat
.venv\\Scripts\\activate.bat
```

## 🛠️ Build for Windows

Run the scripts from the project root on a 64-bit Windows build computer. Each script installs the Python requirements and PyInstaller before building.

| Script | Output | What to distribute |
| --- | --- | --- |
| `build_portable.bat` | `dist\\MuMu-GPS-Controller-Portable\\` | Distribute the **entire folder**, not just the EXE. |
| `build_windows.bat` | `dist\\MuMu-GPS-Controller.exe` | Distribute the single EXE. |
| `build_installer.bat` | `dist\\installer\\MuMu-GPS-Controller-Setup.exe` | Requires Inno Setup 6; creates a normal Windows installer. |

The installer lets users select the destination folder, creates a Start Menu shortcut, offers an optional Desktop shortcut, registers an uninstall entry, and can launch the app after setup. The installation recipe is `MuMu-GPS-Controller-Setup.iss`.

The Chinese installer message files are bundled in `Languages/`; the build does not depend on Chinese language files being installed in the Inno Setup program directory. Some untranslated installer messages fall back to English.

## 🧯 Troubleshooting

| Issue | Suggested check |
| --- | --- |
| `MuMuManager.exe` is not found | Open Settings and browse to the actual `MuMuManager.exe` file. |
| Test Connection fails for an index | Check the index shown in MuMu Multi-instance Manager and verify the manager path. Start the intended emulator instance. |
| One or more instances fail GPS updates | Check each reported index. Successful API selection does not guarantee that the emulator is running or accepting location updates. |
| GPS does not move | Confirm MuMu Player is running, the selected instance is correct, and the MuMu API can communicate with the manager. |
| A CMD window flashes | The app applies a scoped no-console patch to the MuMu API command runner. If it still flashes, report the MuMu Player version, API version, and steps that trigger it. |
| The application does not start | Run the packaged app from its complete Portable folder, or reinstall using the Setup program. Do not copy only the Portable EXE away from its `_internal` folder. |

## 📚 Documentation

- [🛠️ Windows build guide](docs/BUILDING.md)
- [🚀 GitHub publishing guide](docs/GITHUB_PUBLISHING.md)
- [📝 v1.0.0 release notes](docs/RELEASE_NOTES_v1.0.0.md)
- [🇨🇳 完整简体中文说明](README.zh-CN.md)

## 🧾 Third-party components

This project uses PySide6, Requests, OpenCC, and `mumu-python-api-wlkjyy` (plus their dependencies). Each third-party component remains under its own license. See the corresponding project/package pages for details.

## 📄 License

The project source code is released under the [MIT License](LICENSE). Third-party libraries and assets are not relicensed by this statement.
