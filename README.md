# MuMu GPS Controller

A desktop GPS controller for MuMu Android emulators. It provides manual GPS
teleportation, optional local random walking, saved locations, route walking,
location history, Simplified Chinese / Traditional Chinese / English UI, and
customizable colour themes.

The interface is implemented with PySide6 and keeps emulator configuration
separate from personal saved locations and theme preferences. The supplied
blue location-pin artwork is used as the application window icon and as the
Windows executable icon when rebuilt with the included build script.

## Features

- Teleport to a latitude/longitude pair or a Google Maps link.
- Optional nearby random walk after teleport, with configurable duration and
  radius.
- Multi-stop route walking with progress, pause/resume, speed, and update
  interval controls.
- Saved locations, favourites, location history, and route history.
- Duplicate-location confirmation: when a coordinate already exists in location history, the app shows its last recorded time and elapsed time before sending it again.
- Simplified Chinese, Traditional Chinese, and English UI.
- Built-in colour templates plus custom background, card, and accent colours.
- Automatic, limited-scope discovery of `MuMuManager.exe`; no full-disk scan.
- Persistent MuMuManager path and configurable multi-instance control with concurrent GPS updates.
- A test action that verifies API configuration and instance selection without
  claiming the emulator is running.

## Supported MuMu versions

The application searches the standard manager locations for both **MuMu Player
12** and **MuMu Player 6**, including 64-bit and `Program Files (x86)` paths.
It also checks a small set of common Netease/Global installation layouts. A
manual selection is always available in Settings.

The underlying API is
[`mumu-python-api-wlkjyy`](https://github.com/u-wlkjyy/mumu-python-api). Its
documentation describes `Mumu(path).select(index)` and specifies that the
index is the MuMu Multi-instance Manager number. Actual Player 6 and Player 12
runtime testing still depends on an installed emulator and is not implied by
path detection alone.

## Requirements

- Windows
- Python 3.10 or later
- MuMu Player 6 or MuMu Player 12
- `MuMuManager.exe` from that installation
- The dependencies in `requirements.txt`
- PyInstaller (only if building the EXE yourself)

## Installation

```powershell
git clone https://github.com/YOUR-ACCOUNT/MuMu-GPS-Controller.git
cd MuMu-GPS-Controller
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the command in Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

## Run

```powershell
python gps_controller_qt.py
```

## Configure MuMuManager.exe

1. Open **Settings** from the application header.
2. In **Emulator Settings**, check the displayed **MuMuManager Path**. On the
   first launch, the app will have checked only the usual MuMu installation
   folders.
3. If no path was found, click **Browse…** and select `MuMuManager.exe`.
4. In the instance list, keep the emulator indexes you want to control. Use
   **Add Instance** to add more indexes and the row's **Delete** button to remove
   one. For example, enter `1`, `2`, `3`, and `4` to control four emulator
   instances together.
5. Click **Save Emulator Settings**. Use **Test Connection** to check that
   each configured index can be selected by the API.

When the source is run directly, the manager path and configured instance
index list are stored in `gps_config.json` beside the script. The packaged EXE
stores that file in
`%LOCALAPPDATA%\MuMu GPS Controller` so data survives PyInstaller's temporary
single-file extraction. Saved locations and colour themes are kept in their own
files and are also ignored by Git.

## Select multiple emulator instances

The default configuration contains instance `0`. In Settings, use **Add
Instance** to configure more indexes. For example, add `1`, `2`, `3`, and `4`
to send the same GPS coordinate to all four instances concurrently. The index
is the number shown by MuMu's Multi-instance Manager; it is not an automatic
lookup of running emulators. The manager executable path is shared by all
configured indexes.

Manual teleport, the optional random walk, and every Route Walk GPS update are
broadcast to all configured instances. Each instance receives the same
latitude/longitude update in parallel. The application creates a fresh `Mumu`
API object and calls `select(index)` inside each worker thread; no selected API
object is shared between threads. If any configured instance fails an update,
the task reports the successful and failed indexes rather than silently
ignoring a partial failure.

## GPS teleport

1. Open **GPS Location**.
2. Paste a Google Maps share URL, or type `latitude,longitude` and select
   **Parse Link / Coordinates**. You can also enter the fields manually.
3. Optionally enable random walking and choose its duration and radius.
4. Click **Set Virtual Location**.

The controller calls the MuMu API as
`androidEvent.location(longitude, latitude)`. The parameter order is
intentional: longitude comes first.

## Route walking

1. Open **Route Walk**.
2. Enter one coordinate pair or Google Maps link per route stop. At least two
   stops are required.
3. Validate the stops, select a speed and update interval, then start the
   route.
4. Pause/resume or stop the route with the existing controls.


## Windows console-window behavior

The application patches the MuMu API command runner in `mumu.utils` to pass
Windows `CREATE_NO_WINDOW` / `STARTF_USESHOWWINDOW` flags when it launches
`MuMuManager.exe`. This prevents a CMD window from flashing for every GPS
update. The patch is scoped to the MuMu API module and does not modify Python's
global `subprocess` module.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `MuMuManager.exe` was not found | Select it manually in Settings. The selected filename must be exactly `MuMuManager.exe`. |
| The API is not installed | Activate the project environment and run `python -m pip install -r requirements.txt`. |
| Test Connection fails on an instance | Verify the Multi-instance Manager number and the manager path. The test confirms API setup and `select(index)` only; it does not confirm the emulator process is currently running. |
| GPS request fails | Start the intended emulator instance, re-check its index, and inspect MuMu/API permissions or error output. |
| Language or theme changes are not retained | Check that the project folder is writable; theme and emulator configuration are stored separately. |

## Privacy and repository hygiene

Do not commit `gps_config.json`, `gps_locations.json`, or `gps_theme.json`.
They can contain machine-specific paths and personal locations. The included
`.gitignore` excludes them by default.

## License

Released under the [MIT License](LICENSE).

## Build a Windows EXE

The project includes the supplied location-pin icon in both PNG and Windows
ICO formats. To rebuild a one-file Windows executable with the icon embedded,
run `build_windows.bat` from the project directory. The script installs the
project dependencies and PyInstaller, then writes
`dist\MuMu-GPS-Controller.exe`. The PNG is bundled as a Qt runtime asset so
the title bar and taskbar use the same icon.

## CMD window behavior

The MuMu API launches `MuMuManager.exe` through `subprocess.run()` when it
changes the emulator location. On Windows, this project applies a narrowly
scoped subprocess wrapper to the API utility module, adding
`CREATE_NO_WINDOW` and hidden startup flags. This is intended to prevent a
console window from flashing for each GPS update, without changing the
process-wide Python `subprocess` module or modifying the third-party package.

## Build Windows executables

Use 64-bit Windows and a Python version supported by the selected PySide6 release. This project pins PySide6 6.12.0, which has been used in the current development environment.

- Run `build_portable.bat` to create `dist\MuMu-GPS-Controller-Portable\`. Distribute the entire folder.
- Run `build_windows.bat` to create `dist\MuMu-GPS-Controller.exe` as a single-file executable.

Both scripts install the dependencies from `requirements.txt` and PyInstaller before building. Test the resulting build on a clean Windows account or PC before publishing. The app still requires MuMu Player and its `MuMuManager.exe`; Python does not need to be installed on the end user's PC.

### Saved input cache

The app stores the last submitted manual GPS coordinate pair and the current Route Walk draft in `gps_locations.json`. The manual coordinate cache is a single replaceable value (not an accumulating list). The route draft stores each stop input, including blank rows, and its row count; adding, removing, or editing stops updates the saved draft. Existing bookmarks, location history, and completed route history remain separate.
Example cache fields in `gps_locations.json`:

```json
{
  "last_manual_location": {"lat": 4.0, "lon": 4.0},
  "route_draft": {
    "stop_count": 3,
    "stops": ["4,4", "4.001,4.001", ""]
  }
}
```

## Multi-instance GPS control

The Emulator Settings screen lets you add, remove, and save multiple MuMu instance indexes. For example, configure `1`, `2`, `3`, and `4` to send every GPS update to all four instances concurrently. Each update creates a fresh MuMu API client per instance in its own worker thread. The same fan-out is used by manual teleport, optional random walk, and Route Walk. The MuMuManager executable path is shared by the configured instances.

The settings JSON stores `instance_indices` as a list. Existing configurations that only contain `instance_index` are migrated automatically to a one-item list. Duplicate indexes are rejected.


### Multi-instance GPS updates

The app uses the MuMu API native multi-index selection (`select([index1, index2, ...])`) for one GPS update. If the batch call fails, it retries each configured index sequentially to identify unavailable instances and reports per-index errors.

## Install like a regular Windows application

To create a Windows setup program, first install **Inno Setup 6** on the build
computer: https://jrsoftware.org/isinfo.php. Then run `build_installer.bat`
from the project folder. The script builds the current one-folder PyInstaller
application and compiles `MuMu-GPS-Controller-Setup.iss`.

The resulting installer is:

```text
dist\installer\MuMu-GPS-Controller-Setup.exe
```

During setup, users can choose the destination folder. The installer creates
a Start Menu shortcut and offers an optional Desktop shortcut (selected by
default). It also registers a normal Windows uninstall entry and can launch
the application when setup finishes. The installed application does not need
Python on the target computer; the user does still need MuMu Player 6 or 12
for emulator GPS control.

Application settings, saved locations, themes, and emulator configuration are
stored under `%LOCALAPPDATA%\MuMu GPS Controller`, separately from the
installation folder. The installer intentionally does not remove this user
data when the application is uninstalled, so it is available if the app is
installed again for the same Windows account.

The installer itself is compiled on Windows by Inno Setup 6. This repository
contains its `.iss` recipe and build script, not a precompiled installer.

## Build the Windows installer

1. Install Inno Setup 6.
2. Run `build_installer.bat` from this project folder.
3. The script builds the application with PyInstaller and compiles the setup
   program into `dist\installer\MuMu-GPS-Controller-Setup.exe`.

The installer language overrides are bundled in `Languages/`, so the build
**does not depend on Chinese language files being installed in the Inno Setup
program directory**. Inno Setup's built-in `Default.isl` is loaded first, and
project-local Simplified/Traditional Chinese overrides are layered on top.

The bundled Chinese translations are partial message overrides; any untranslated
installer messages fall back to English. The application UI itself remains
fully multilingual as before.
