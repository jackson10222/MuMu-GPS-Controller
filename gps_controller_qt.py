"""PySide6 port of gps_controller.py (the CustomTkinter file is the reference)."""

from __future__ import annotations

import importlib
import json
import math
import os
import random
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# PyInstaller normally configures DLL search paths itself.  Register the
# bundled Qt folder explicitly as well, so a machine-wide Qt installation
# cannot supply an incompatible Qt6Core.dll to PySide6.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _bundle_dir = Path(sys._MEIPASS)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(_bundle_dir))
        os.add_dll_directory(str(_bundle_dir / "PySide6"))

import requests
from PySide6.QtCore import QObject, QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QIntValidator, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
try:
    from mumu.mumu import Mumu
    MUMU_API_IMPORT_ERROR = None
except Exception as exc:
    # A missing package and a broken optional API installation must not prevent
    # the settings screen from opening so the user can see a clear remedy.
    Mumu = None
    MUMU_API_IMPORT_ERROR = str(exc)


class _NoConsoleSubprocessProxy:
    """Proxy the MuMu API's subprocess module and hide Windows child consoles."""

    def __init__(self, subprocess_module):
        self._subprocess = subprocess_module

    def __getattr__(self, name):
        return getattr(self._subprocess, name)

    def run(self, *popenargs, **kwargs):
        # MuMu's AndroidEvent.location() calls mumu.utils.utils.run_command(),
        # which uses subprocess.run() to launch MuMuManager.exe. On Windows,
        # console-subsystem children can otherwise flash a CMD window for every
        # GPS update. Patch only the MuMu utility module's subprocess reference;
        # do not mutate Python's process-wide subprocess module.
        if os.name == "nt":
            kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | self._subprocess.CREATE_NO_WINDOW
            startupinfo = kwargs.get("startupinfo")
            if startupinfo is None:
                startupinfo = self._subprocess.STARTUPINFO()
            startupinfo.dwFlags |= self._subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = self._subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo
        return self._subprocess.run(*popenargs, **kwargs)


def _install_mumu_no_console_patch():
    """Hide MuMuManager child consoles in the module used by mumu-python-api.

    Current mumu-python-api-wlkjyy releases implement the command runner in
    ``mumu/utils.py`` (import path ``mumu.utils``), not ``mumu.utils.utils``.
    The old import path silently failed and left subprocess.run unpatched,
    which caused a CMD window to flash on every GPS update.
    """
    if os.name != "nt" or Mumu is None:
        return False

    # Current API releases use mumu.utils. Keep the legacy package path as a
    # compatibility fallback in case an older distribution exposes it.
    for module_name in ("mumu.utils", "mumu.utils.utils"):
        try:
            api_utils_module = importlib.import_module(module_name)
        except ImportError:
            continue

        if getattr(api_utils_module, "_gps_no_console_patch_installed", False):
            return True

        original_subprocess = getattr(api_utils_module, "subprocess", None)
        if original_subprocess is None or not hasattr(original_subprocess, "run"):
            continue

        api_utils_module.subprocess = _NoConsoleSubprocessProxy(original_subprocess)
        api_utils_module._gps_no_console_patch_installed = True
        return True

    # A changed API internal layout should not prevent the main GUI from
    # opening. Returning False allows diagnostics to explain that the patch
    # could not be installed rather than silently pretending it succeeded.
    return False


MUMU_NO_CONSOLE_PATCH_INSTALLED = _install_mumu_no_console_patch()

APP_TITLE = "MuMu GPS Controller"


def application_data_dir() -> Path:
    """Keep EXE settings out of PyInstaller's temporary extraction folder."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent
    try:
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_TITLE
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    except OSError:
        # A portable folder is a usable fallback if LocalAppData is unavailable.
        return Path(sys.executable).resolve().parent


APP_DATA_DIR = application_data_dir()
DATA_FILE = APP_DATA_DIR / "gps_locations.json"
THEME_FILE = APP_DATA_DIR / "gps_theme.json"
CONFIG_FILE = APP_DATA_DIR / "gps_config.json"


def save_json_atomically(path: Path, data, keep_backup=True):
    """Write JSON via os.replace and preserve the last valid file as .bak."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    backup = path.with_suffix(path.suffix + ".bak")
    try:
        encoded = json.dumps(data, ensure_ascii=False, indent=2)
        with temporary.open("w", encoding="utf-8", newline="\\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

        if keep_backup and path.exists():
            try:
                # Never replace a good backup with an already-corrupt primary.
                json.loads(path.read_text(encoding="utf-8"))
                backup_temp = backup.with_name(backup.name + ".tmp")
                backup_temp.write_bytes(path.read_bytes())
                os.replace(backup_temp, backup)
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass

        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def resource_path(relative_path: str) -> Path:
    """Resolve bundled assets in source, one-folder, and one-file builds."""
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root / relative_path


APP_ICON_PATH = resource_path("assets/gps-location-icon.png")

BG, SURFACE, SURFACE_ALT = "#F3F6FC", "#FFFFFF", "#F7F9FD"
TEXT, MUTED, BORDER = "#172B4D", "#718096", "#E2E8F0"
BLUE, BLUE_HOVER, GREEN, RED, ORANGE = "#3478F6", "#2464D8", "#159B68", "#D64545", "#C98220"
LANGUAGE_CHOICES = (("中文(简体)", "zh"), ("中文(繁体)", "zh-tw"), ("English", "en"))

THEMES = {
    "蓝色": {"name": "蓝色", "bg": "#F3F6FC", "surface": "#FFFFFF", "accent": "#3478F6", "hover": "#2464D8", "text": "#172B4D", "muted": "#718096", "border": "#E2E8F0"},
    "红色": {"name": "红色", "bg": "#FCF4F5", "surface": "#FFFFFF", "accent": "#E56B78", "hover": "#CC5261", "text": "#542B35", "muted": "#8C6870", "border": "#F0DDE0"},
    "绿色": {"name": "绿色", "bg": "#F2F8F4", "surface": "#FFFFFF", "accent": "#42A477", "hover": "#31865F", "text": "#1E3B2D", "muted": "#6F897B", "border": "#DCEAE0"},
    "黄色": {"name": "黄色", "bg": "#FCF8EC", "surface": "#FFFFFF", "accent": "#D6A52E", "hover": "#B98B1E", "text": "#4A3B1B", "muted": "#8D805E", "border": "#EEE5CC"},
    "紫色": {"name": "紫色", "bg": "#F6F3FB", "surface": "#FFFFFF", "accent": "#9270D6", "hover": "#7656BC", "text": "#33264D", "muted": "#817493", "border": "#E6DFF1"},
    "粉色": {"name": "粉色", "bg": "#FCF3F8", "surface": "#FFFFFF", "accent": "#D66FA8", "hover": "#B9538D", "text": "#4A2D40", "muted": "#8B7181", "border": "#F0DDE8"},
}

# Source language for every UI string is Simplified Chinese.  This makes
# retranslation deterministic and leaves editable user text untouched.
EN = {
    "GPS 定位": "GPS Location", "收藏地点": "Saved Location", "路线行走": "Route Walk",
    "COORDINATE  ·  OPTIONAL SHORT WALK  ·  ROUTE WALK": "COORDINATES  ·  OPTIONAL SHORT WALK  ·  ROUTE WALK",
    "Google Maps 链接": "Google Maps Link", "粘贴 Google Maps 分享链接或输入 纬度,经度": "Paste a Google Maps share link or enter latitude,longitude",
    "解析链接 / 坐标": "Parse Link / Coordinates", "清空": "Clear", "手动坐标": "Manual Coordinates",
    "纬度 Latitude": "Latitude", "经度 Longitude": "Longitude", "传送后原地随机走动": "Random Walk After Teleport",
    "可选功能：在目标附近移动一段时间，然后返回起点。": "Optional: move around the target for a while, then return to the starting point.",
    "启用随机走动": "Enable Random Walk", "持续时间（秒）": "Duration (seconds)", "活动范围半径（米）": "Movement Radius (meters)",
    "时间 1–600 秒 · 半径 1–100 米": "Duration: 1–600 sec · Radius: 1–100 m", "◎   设置虚拟定位": "⌖   Set Virtual Location",
    "停止当前任务": "Stop Current Task", "定位历史": "Location History", "暂无定位历史": "No location history", "使用": "Use",
    "我的定位收藏": "Saved Locations", "保存常用地点，设置图标和颜色；星标地点可以置顶。": "Save frequent locations with custom icons and colors; favorite locations can be pinned.",
    "＋ 添加地点": "＋ Add Location", "编辑": "Edit", "删除": "Delete", "★ 星标": "★ Favorite", "置顶": "Move to Top", "上移": "Move Up", "下移": "Move Down",
    "◎   传送到选中地点": "⌖   Teleport to Selected Location", "双击地点卡片也可以快速传送。": "Double-click a location card to teleport quickly.",
    "还没有收藏地点": "No saved locations yet", "传送": "Teleport", "路线地点": "Route Stops",
    "一个地点一行输入：纬度,经度 或 Google Maps 链接。至少需要两个地点。": "Enter one stop per row: latitude,longitude or a Google Maps link. At least two stops are required.",
    "检查路线点": "Validate Route Stops", "路线进度 Progress": "Route Progress", "等待开始路线": "Waiting to start", "移动参数": "Movement Settings",
    "速度（km/h）": "Speed (km/h)", "更新间隔（秒）": "Update Interval (seconds)", "开始路线": "Start Route", "暂停 / 继续": "Pause / Resume", "停止": "Stop",
    "纬度,经度 / Google Maps URL": "Latitude,longitude / Google Maps URL", "运行状态": "Status", "待机": "Idle",
    "待机 · 输入坐标后即可设置虚拟定位。": "Idle · Enter coordinates to set a virtual location.", "地点名称": "Location Name", "选择图标": "Choose Icon", "选择颜色": "Choose Color",
    "蓝色": "Blue", "紫色": "Purple", "粉色": "Pink", "红色": "Red", "橙色": "Orange", "绿色": "Green", "青色": "Cyan", "金色": "Gold",
    "设为收藏": "Save as Favorite", "保存地点": "Save Location", "添加收藏地点": "Add Saved Location", "编辑收藏地点": "Edit Saved Location",
    "⚙ 设置": "⚙ Settings", "设置": "Settings", "语言": "Language", "主题颜色": "Theme", "主题模板": "Theme Templates", "自定义颜色": "Custom Colors",
    "背景": "Background", "卡片": "Card", "主色": "Accent", "应用自定义颜色": "Apply Custom Colors", "关闭": "Close", "自定义": "Custom",
    "蓝色": "Blue", "红色": "Red", "绿色": "Green", "黄色": "Yellow", "紫色": "Purple", "粉色": "Pink",
    "模拟器设置": "Emulator Settings", "MuMuManager 路径": "MuMuManager Path", "浏览…": "Browse…", "模拟器实例编号": "Emulator Instance Index",
    "已添加的实例（定位会同时发送到所有实例）": "Configured instances (GPS updates are sent to all instances simultaneously)",
    "添加实例": "Add Instance", "实例编号不能为空。": "Instance index cannot be empty.",
    "至少需要添加一个模拟器实例。": "Add at least one emulator instance.",
    "实例编号重复：{indices}": "Duplicate instance indices: {indices}",
    "实例 {index} 选择成功。": "Instance {index} selected successfully.",
    "以下实例选择失败：{details}": "The following instances failed: {details}",
    "已选择 {count} 个实例：{indices}。配置检查完成；这不会确认模拟器当前正在运行。": "Configured {count} instances: {indices}. Configuration check completed; this does not confirm that the emulators are currently running.",
    "定位已发送到实例：{indices}。": "GPS location sent to instances: {indices}.",
    "部分实例定位失败。成功：{success}；失败：{failed}": "GPS update partially failed. Successful: {success}; failed: {failed}",
    "测试连接": "Test Connection", "保存模拟器设置": "Save Emulator Settings", "保存成功": "Saved", "保存失败": "Save Failed", "测试成功": "Test Successful", "测试失败": "Test Failed",
    "设置已保存。": "Settings saved.", "路径无效。请选择 MuMuManager.exe。": "The path is invalid. Select MuMuManager.exe.",
    "实例编号必须是非负整数。": "The instance index must be a non-negative integer.",
    "MuMu API 未安装。请运行：pip install mumu-python-api-wlkjyy": "MuMu API is not installed. Run: pip install mumu-python-api-wlkjyy",
    "未找到 MuMuManager.exe。请在设置中手动选择。": "MuMuManager.exe was not found. Choose it manually in Settings.",
    "MuMu API 配置和实例选择成功。这不会确认模拟器当前正在运行。": "MuMu API configuration and instance selection succeeded. This does not confirm that the emulator is currently running.",
    "提示": "Notice", "确认": "Confirm", "确认删除": "Confirm Delete", "重复定位确认": "Repeat Location Confirmation",
    "这个坐标已经在定位历史中出现过。\n上次记录时间：{time}\n距离上次定位：{elapsed}\n\n仍然要再次传送到这个位置吗？": "This coordinate is already in your location history.\nLast recorded: {time}\nTime since the last location: {elapsed}\n\nDo you want to set this location again?",
    "时间未知": "Time unknown", "刚刚": "Just now", "秒前": "seconds ago", "分钟前": "minutes ago", "小时前": "hours ago", "天前": "days ago",
    "输入错误": "Input Error", "坐标错误": "Coordinate Error", "路线错误": "Route Error", "解析失败": "Parsing Failed",
    "正在运行": "Already Running", "停止路线": "Stop Route", "重新开始路线": "Restart Route",
    "请粘贴 Google Maps 链接或输入 纬度,经度。": "Paste a Google Maps link or enter latitude,longitude.",
    "不是可识别的 Google Maps 链接或坐标。": "This is not a recognized Google Maps link or coordinate pair.",
    "链接已打开，但没有找到经纬度。请尝试使用 Google Maps 的分享链接。": "The link opened, but no coordinates were found. Try a Google Maps share link.",
    "路线至少需要保留两个地点。": "At least two route stops are required.", "路线至少需要两个地点。": "At least two route stops are required.",
    "请输入地点名称。": "Please enter a location name.", "坐标范围不正确。": "Coordinates are out of range.", "当前坐标无效。": "Current coordinates are invalid.",
    "请先选择一个收藏地点。": "Please select a saved location first.", "确定清空定位历史和路线历史吗？": "Are you sure you want to clear location and route history?",
    "确定要停止当前路线行走吗？": "Are you sure you want to stop the current route walk?", "请先停止当前任务。": "Please stop the current task first.",
    "当前路线已完成 {percent:.1f}%。重新开始会从第一个地点重新走，确定继续吗？": "The current route is {percent:.1f}% complete. Restarting will begin from the first stop. Continue?",
    "模拟器编号必须是非负整数。": "The emulator instance number must be a non-negative integer.", "纬度范围 -90 至 90，经度范围 -180 至 180。": "Latitude must be between -90 and 90; longitude between -180 and 180.",
    "随机走动持续时间必须在 1–600 秒之间。": "Random walk duration must be between 1–600 seconds.", "随机走动半径必须在 1–100 米之间。": "Random walk radius must be between 1–100 meters.",
    "速度需大于 0 且不超过 100 km/h。": "Speed must be greater than 0 and no more than 100 km/h.", "更新间隔需在 1–10 秒之间。": "Update interval must be between 1–10 seconds.",
    "正在解析链接……": "Parsing link…", "解析失败。": "Link parsing failed.", "正在设置虚拟定位……": "Setting virtual location…", "正在解析路线……": "Preparing route…", "正在停止任务……": "Stopping task…",
    "随机走动完成，已返回起点。": "Random walk completed; returned to the starting point.", "随机走动已停止，保留最后位置。": "Random walk stopped; keeping the last position.",
    "路线行走已停止，保留最后位置。": "Route Walk stopped; keeping the last position.", "路线行走已完成。": "Route Walk completed.", "继续运行。": "Resuming.",
    "已暂停 · 点击「暂停 / 继续」恢复。": "Paused · Click Pause / Resume to continue.", "MuMu API 返回失败。": "MuMu API request failed.",
    "结束后返回起点失败。": "Failed to return to the starting point.", "MuMu 未接受路线起点。": "MuMu did not accept the route start point.", "MuMu API 返回失败，路线移动停止。": "MuMu API request failed; route stopped.",
}


def darken_color(value: str, factor: float = .84) -> str:
    rgb = value.lstrip("#")
    channels = [max(0, min(255, int(int(rgb[i:i + 2], 16) * factor))) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(channels)


def valid_coordinates(lat: float, lon: float) -> bool:
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def parse_coordinate_pair(text: str):
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None
    lat, lon = map(float, match.groups())
    return (lat, lon) if valid_coordinates(lat, lon) else None


def extract_coordinates(text: str):
    text = unquote(text.strip())
    for pattern in (r"@(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)", r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)"):
        match = re.search(pattern, text)
        if match:
            lat, lon = map(float, match.groups())
            if valid_coordinates(lat, lon):
                return lat, lon
    try:
        for key in ("q", "query", "center", "destination", "origin"):
            for value in parse_qs(urlparse(text).query).get(key, []):
                if pair := parse_coordinate_pair(value):
                    return pair
    except Exception:
        pass
    return None


def resolve_maps_or_pair(text: str):
    text = text.strip()
    if pair := parse_coordinate_pair(text):
        return pair
    if direct := extract_coordinates(text):
        return direct
    host = (urlparse(text).hostname or "").lower()
    if not (host in {"maps.app.goo.gl", "goo.gl", "google.com", "google.co.jp"} or host.endswith(".google.com") or host.endswith(".google.co.jp")):
        raise ValueError("不是可识别的 Google Maps 链接或坐标。")
    response = requests.get(text, allow_redirects=True, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    if result := extract_coordinates(response.url) or extract_coordinates(response.text[:2_000_000]):
        return result
    raise ValueError("链接已打开，但没有找到经纬度。请尝试使用 Google Maps 的分享链接。")


def haversine_m(a, b) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6_371_000 * math.asin(min(1, math.sqrt(h)))


def destination_point(origin, north_m, east_m):
    lat, lon = origin
    new_lat = lat + math.degrees(north_m / 6_371_000)
    new_lon = lon + math.degrees(east_m / (6_371_000 * max(1e-8, abs(math.cos(math.radians(lat))))))
    return new_lat, (new_lon + 180) % 360 - 180


def interpolate_great_circle(start, end, fraction):
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    delta = haversine_m(start, end) / 6_371_000
    if delta < 1e-12:
        return end
    a, b = math.sin((1 - fraction) * delta) / math.sin(delta), math.sin(fraction * delta) / math.sin(delta)
    x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
    y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
    z = a * math.sin(lat1) + b * math.sin(lat2)
    return math.degrees(math.atan2(z, math.sqrt(x * x + y * y))), math.degrees(math.atan2(y, x))


class MumuBackend:
    """Persistent MuMu settings and concurrent, per-instance API calls."""

    DEFAULT_CONFIG = {"manager_path": "", "instance_indices": ["0"], "instance_index": "0"}
    MAX_INSTANCES = 64

    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load_config()

    @staticmethod
    def _is_manager(path: str | Path) -> bool:
        candidate = Path(path) if path else None
        return bool(candidate and candidate.is_file() and candidate.name.lower() == "mumumanager.exe")

    @classmethod
    def common_manager_paths(cls):
        program_roots = [
            os.environ.get("ProgramW6432", ""),
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramFiles(x86)", ""),
            r"C:\Program Files",
            r"C:\Program Files (x86)",
        ]
        roots = []
        for root in program_roots:
            if root and root not in roots:
                roots.append(root)
        relative_paths = (
            Path("Netease") / "MuMu Player 12" / "shell" / "MuMuManager.exe",
            Path("Netease") / "MuMu Player 6" / "shell" / "MuMuManager.exe",
            Path("Netease") / "MuMu" / "nx_main" / "MuMuManager.exe",
            Path("Netease") / "MuMuPlayerGlobal-12.0" / "shell" / "MuMuManager.exe",
            Path("Netease") / "MuMuPlayerGlobal-6.0" / "shell" / "MuMuManager.exe",
        )
        return [Path(root) / relative for root in roots for relative in relative_paths]

    @classmethod
    def detect_manager_path(cls) -> str:
        for candidate in cls.common_manager_paths():
            if cls._is_manager(candidate):
                return str(candidate)
        return ""

    @staticmethod
    def normalize_instance(value) -> str:
        text = str(value).strip()
        if not text.isdigit():
            raise ValueError("实例编号必须是非负整数。")
        return str(int(text))

    @classmethod
    def normalize_instances(cls, values) -> list[str]:
        if isinstance(values, str):
            raw_values = re.split(r"[,，;；\s]+", values.strip()) if values.strip() else []
        elif isinstance(values, (list, tuple, set)):
            raw_values = list(values)
        else:
            raw_values = []
        normalized = []
        seen = set()
        for value in raw_values:
            if str(value).strip() == "":
                continue
            index = cls.normalize_instance(value)
            if index not in seen:
                normalized.append(index)
                seen.add(index)
        if not normalized:
            raise ValueError("至少需要添加一个模拟器实例。")
        if len(normalized) > cls.MAX_INSTANCES:
            raise ValueError(f"最多支持同时配置 {cls.MAX_INSTANCES} 个模拟器实例。")
        return normalized

    def _load_config(self):
        saved = self.DEFAULT_CONFIG.copy()
        try:
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                saved["manager_path"] = str(data.get("manager_path", "")).strip()
                # New format stores a list; old single-index config is migrated automatically.
                raw_indices = data.get("instance_indices", data.get("instance_index", "0"))
                try:
                    saved["instance_indices"] = self.normalize_instances(raw_indices)
                except ValueError:
                    saved["instance_indices"] = ["0"]
                saved["instance_index"] = saved["instance_indices"][0]
        except Exception:
            pass
        if not self._is_manager(saved["manager_path"]):
            saved["manager_path"] = self.detect_manager_path()
        return saved

    def save(self, manager_path: str, instance_indices) -> None:
        path = str(manager_path).strip()
        indices = self.normalize_instances(instance_indices)
        if not self._is_manager(path):
            raise FileNotFoundError("路径无效。请选择 MuMuManager.exe。")
        payload = {
            "manager_path": path,
            "instance_indices": indices,
            # Keep the old key for downgrade compatibility; it points to the first configured instance.
            "instance_index": indices[0],
        }
        save_json_atomically(self.config_file, payload)
        self.config = payload

    def configured_indices(self) -> list[str]:
        values = self.config.get("instance_indices")
        if not values:
            values = [self.config.get("instance_index", "0")]
        return self.normalize_instances(values)

    def selected_instance(self, instance_index):
        if Mumu is None:
            detail = f" ({MUMU_API_IMPORT_ERROR})" if MUMU_API_IMPORT_ERROR else ""
            raise RuntimeError("MuMu API 未安装。请运行：pip install mumu-python-api-wlkjyy" + detail)
        path = self.config.get("manager_path", "")
        if not self._is_manager(path):
            raise FileNotFoundError("未找到 MuMuManager.exe。请在设置中手动选择。")
        index = int(self.normalize_instance(instance_index))
        # Each call gets its own selected client in the thread that uses it.
        return Mumu(path).select(index)

    @staticmethod
    def _format_api_error(exc: Exception) -> str:
        detail = str(exc).strip()
        if not detail:
            detail = repr(exc)
        return f"{type(exc).__name__}: {detail}"

    def _send_to_instance(self, instance_index: str, lat: float, lon: float):
        """Sequential diagnostic fallback for a single emulator index."""
        manager = self.selected_instance(instance_index)
        result = manager.androidEvent.location(lon, lat)  # API order: longitude, latitude.
        if not result:
            raise RuntimeError(f"MuMu API did not confirm location for instance {instance_index} (returned {result!r}).")
        return instance_index

    def broadcast_location(self, lat: float, lon: float) -> list[str]:
        """Use MuMu's native multi-index selection, then diagnose per index if needed.

        The API officially supports Mumu.select([1, 2, 3]).androidEvent.location(...).
        This avoids launching several MuMuManager.exe processes concurrently.
        """
        indices = self.configured_indices()
        if Mumu is None:
            detail = f" ({MUMU_API_IMPORT_ERROR})" if MUMU_API_IMPORT_ERROR else ""
            raise RuntimeError("MuMu API 未安装。请运行：pip install mumu-python-api-wlkjyy" + detail)
        path = self.config.get("manager_path", "")
        if not self._is_manager(path):
            raise FileNotFoundError("未找到 MuMuManager.exe。请在设置中手动选择。")

        batch_error = None
        try:
            client = Mumu(path).select([int(index) for index in indices])
            result = client.androidEvent.location(lon, lat)  # API order: longitude, latitude.
            if result:
                return indices
            batch_error = f"批量定位调用未确认成功（返回 {result!r}）"
        except Exception as exc:
            batch_error = self._format_api_error(exc)

        # The batch command can fail as a whole if one configured index is
        # unavailable. Retry sequentially to identify exactly which indexes
        # are reachable and still update the working instances.
        succeeded, errors = [], {}
        for index in indices:
            try:
                self._send_to_instance(index, lat, lon)
                succeeded.append(index)
            except Exception as exc:
                errors[index] = self._format_api_error(exc)

        if errors:
            success_text = ", ".join(succeeded) if succeeded else "无"
            failed_text = "；".join(f"实例 {index}: {message}" for index, message in errors.items())
            raise RuntimeError(
                f"定位未能发送到所有实例。成功：{success_text}；失败：{failed_text}。"
                f"批量调用原因：{batch_error}"
            )
        return indices

    def test_connection(self, manager_path: str, instance_indices) -> str:
        path = str(manager_path).strip()
        indices = self.normalize_instances(instance_indices)
        if not self._is_manager(path):
            raise FileNotFoundError("路径无效。请选择 MuMuManager.exe。")
        if Mumu is None:
            detail = f"\n{MUMU_API_IMPORT_ERROR}" if MUMU_API_IMPORT_ERROR else ""
            raise RuntimeError("MuMu API 未安装。请运行：pip install mumu-python-api-wlkjyy" + detail)
        failures = []
        for index in indices:
            try:
                Mumu(path).select(int(index))
            except Exception as exc:
                failures.append(f"实例 {index}: {exc}")
        if failures:
            raise RuntimeError("以下实例选择失败：" + "；".join(failures))
        joined = ", ".join(indices)
        return f"已选择 {len(indices)} 个实例：{joined}。配置检查完成；这不会确认模拟器当前正在运行。"


class ClickableFrame(QFrame):
    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class FavoriteCheckBox(QCheckBox):
    """A 14 px, tick-only control; its label is intentionally separate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(18, 18)

    def paintEvent(self, event):  # noqa: N802 - Qt API name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        indicator = QRect(2, 2, 14, 14)
        is_checked = self.isChecked()
        is_hovered = self.underMouse()
        painter.setPen(QPen(QColor(BLUE if is_checked or is_hovered else "#CBD5E1"), 1.5))
        painter.setBrush(QColor("#E8EEF8" if is_hovered and not is_checked else "#FFFFFF"))
        painter.drawRoundedRect(indicator, 4, 4)
        if is_checked:
            painter.setPen(QPen(QColor(BLUE), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(indicator.left() + 3, indicator.top() + 7, indicator.left() + 6, indicator.top() + 10)
            painter.drawLine(indicator.left() + 6, indicator.top() + 10, indicator.left() + 11, indicator.top() + 4)


class Worker(QThread):
    status = Signal(str, str)
    progress = Signal(float, float, float, int, int, bool)
    record_location = Signal(float, float, str)
    save_manual_location = Signal(float, float)
    record_route = Signal(object)
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent: QObject | None = None):
        super().__init__(parent)
        self.fn = fn

    def run(self):  # noqa: N802
        try:
            result = self.fn(self)
            if result is not None:
                self.result.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class GPSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        if APP_ICON_PATH.is_file():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(850, 900)
        self.setMinimumSize(570, 620)
        self.language = "zh"
        self.translatables = []
        self.bookmarks, self.location_history, self.route_history = [], [], []
        # Single-value manual GPS cache and editable Route Walk draft.
        # These are separate from the append-only location/route history.
        self.last_manual_location = None
        self.manual_input_cache = {"lat": "", "lon": ""}
        self.route_draft = None
        self._data_recovered = False
        self._data_load_error = None
        self._restoring_route_draft = False
        self.history_lock = threading.Lock()
        self.selected_bookmark = None
        self.bookmark_cards, self.route_rows, self.background_workers = [], [], []
        self.route_progress_value, self.current_position, self.mode = 0.0, None, None
        self._route_progress_state = None
        self.worker = None
        self._closing_requested = False
        self._close_ready = False
        self.stop_event, self.pause_event = threading.Event(), threading.Event()
        self.pause_event.set()
        self._status_source_text, self._status_color = "待机 · 输入坐标后即可设置虚拟定位。", MUTED
        self.backend = MumuBackend()
        self.theme = self._load_theme()
        self._set_theme_globals(self.theme)
        self._load_bookmarks()
        self._build_ui()
        self._apply_style()
        self._refresh_bookmarks()
        self._refresh_location_history()
        self._set_status(self._status_source_text, MUTED)
        if self._data_recovered:
            self._set_status("已从备份恢复定位数据。", ORANGE)
        elif self._data_load_error:
            QMessageBox.warning(self, self._t("数据读取警告"), self._t("定位数据文件无法读取，已保留原文件且使用空白数据启动。请检查文件及其 .bak 备份。\n") + str(self._data_load_error))

    # ---- language -----------------------------------------------------
    def _to_traditional(self, text: str) -> str:
        try:
            from opencc import OpenCC
            return OpenCC("s2t").convert(text)
        except Exception:
            # Covers all built-in UI text when OpenCC is not installed.
            src = "后发里这为经纬路线地点收藏设置颜色选择暂停继续运行时间间隔速度开始结束确认删除保存添加清空使用图标名称输入坐标移动范围随机走动状态选项实侧点个总线与错误请标签双击还没有还贴链并历暂无等备联国复双验启兑组间换县币输见让载仅处务页现别条数记话该误总历觉码开实发来进询读验败级构项时则达装单卫门风厅签画吴宽负质转导尽签择标释杨欢击纸极台术队齐费网闻听备续计须现冲杂极参识费样应议价请现为准续与两万云关书买争产优会伤伦体余侣偿儿党兰兴养兽内冈册写军农冯况冻净凄减凑几凤凭凯击刍划刘则刚创删别剂剧劝办励劲劳势勋医华协卖卢卫却厅历厉压厌厕县双发变叙叠叶号叹听启吴员团园围图圆场坏块坚坛坝坠垄垒垦墙壮声壳处备复够头夹夺奋奖奥妆妇妈娱娄娇婴孙学宁宝实宠审宫宽宾寝对寻导寿将尔尘尝尧尸尽层属屡岁岂岗岛岭岳峡峦币帅师帐帘帜带帮常干并广庄庆庐库应庙庞废开异弃张弥弦弯弹强归当录彻径忆忧怀态总恋恳恶惊惧惨惯愤愿懒戏战户扑执扩扫扬扰抚抛抢护报担拟拢拣拥拦拨择挂挚挛挠挡挣挤挥捞损捡换据掳掷掸揽搀搁搂搅携摄摆摇摊撑撵撷取数斗断无旧时旷昼显晋晒晓晕暂暧术朴机杀杂权条来杨杰松板构枢枪枫柜柠查栅标栈栋栏树栖样档桥桦桨桩梦检楼榄榆槛樱橱欢欧欲歼残殴毁毕毙气汇汉汤沟没沥沦沧沪泞泪泻泼泽洁洒洼浅浆浇浊测济浏浑浓涛涝涟涡涣涤润涧涨涩淀渐渔温湾湿溃溅滚满滤滥滨滩灭灯灵灾灿炉炼烁烂烦烧烨烩烫热焕爱爷牵牺犊状犹狈独狭狮狱猎猪猫献玛环现电画畅疗疟疠疡疮疯痒痨痪瘫瘾癞皑皱盏盐监盖盗盘着睁睐睑瞒瞩矫矿码砖砚砾础硕确碍碎礼祷祸禄离秃种积称秽稳穑穗穷窃窍窑窜窝窥竖竞笃笔笺笼筛筝筹签简篮篱类粮紧纠纡红纣纤约级纪纬纯纱纲纳纵纷纸纹纺纽线练组细织终绊绍经绑绒结绕绘给络绝统绢绣继绩绪续绮绯绰绳维绵绶绷绸综绽绾绿缀缄缅缆缉缎缓缔缕编缘缚缝缠缡缨缩缴网罗罚罢羁翘耸耻聂聋职联聪肃肠肤肾肿胀胁胆胜胶脉脏脑脸腊腌腾舆舰舱艰艳艺节芜芦苏苇苍范茎荆荐荚荛荜荞荟荠荡荣荤荧药莱莲莳莴获莹莺萝萤营萦萧萨葱蒋蒌蓝蓟蔷蔹蔺蕴薮藓虏虑虚虫虽虾蚀蚁蚂蚕蛊蛎蛏蛮蛰蛱蜕蜗蝇蝉蝼螨蟒袅补装裤见观规觅视览觉触誉计订认讥讨让训议讯记讲讳讴讶许讹论讼讽设访诀证评识诈诉诊词译试诗诚诛话诞诡询该详诫诬语误诱诲说诵请诸诺读课谁调谅谈谊谋谎谏谐谑谓谒谕谗谘谙谚谜谢谣谤谦谨谩谪谬谭谱谴谷贝贞负贡财责贤败账货质贩贪贫贬购贮贯贰贱贴贵贷贸费贺贻贼贿赁赂赃资赈赊赋赌赎赏赐赔赖赘赚赛赞赠赵赶趋跃践踊踌踪蹑蹒躏车轧轨轩转轮软轰轴轻载较辅辆辈辉辊辐辑输辙辕辖辗轿辩辞辫边辽达迁过迈运还这进远违连迟迩迹适选逊递逻遗邮邻郑酝酱酿采释里鉴钉针钓钠钢钱铁铃铜铝银铺链销锁锅锈锋锐锤锦键锯镇镜镰长门闪闭问闯闲间闷闸闹闻闽阁阅阀阂阄阆阈阉阊阋阌阍阎阏阐阔阕阖阗阙队阳阴阵阶际陆陈险随隐难雏雳雾霁静韩页顶顷项顺须顽顾顿颁颂预领颇颈颉颊颌颍颏颐频颓颖颗题颜额颠颤风飞饥饭饮饱饰饼饺饿馁馄馆馈馋馍馏馒马驭驮驯驰驱驳驴驻驼驶驹骂骄骅骆骇骈骊骋验骏骑骗骚鱼鲁鲂鲅鲆鲇鲈鲋鲍鲎鲐鲑鲒鲔鲕鲚鲛鲜鲞鲟鲠鲡鲢鲣鲤鲥鲦鲧鲨鲩鲫鲭鲮鲰鲱鲲鲳鲴鲵鲶鲷鲸鲺鲻鲼鲽鳃鳄鳅鳆鳇鳊鳋鳌鳍鳎鳏鳐鳓鳔鳕鳗鳘鳙鳜鳝鳞鸟鸠鸡鸢鸣鸥鸦鸨鸩鸪鸫鸬鸭鸮鸯鸱鸲鸳鸵鸶鸷鸸鸹鸺鸽鸾鸿鹅鹆鹇鹈鹉鹊鹌鹏鹑鹕鹗鹘鹚鹛鹜鹞鹣鹦鹧鹨鹩鹪鹫鹬鹭鹮鹯鹰鹾麦麸黄齐齿龄龙龟"
            dst = "後發裏這為經緯路線地點收藏設置顏色選擇暫停繼續運行時間間隔速度開始結束確認刪除保存添加清空使用圖標名稱輸入座標移動範圍隨機走動狀態選項實側點個總線與錯誤請標籤雙擊還沒有還貼鏈並歷暫無等備聯國復雙驗啟兌組間換縣幣輸見讓載僅處務頁現別條數記話該誤總歷覺碼開實發來進詢讀驗敗級構項時則達裝單衛門風廳簽畫吳寬負質轉導盡簽擇標釋楊歡擊紙極臺術隊齊費網聞聽備續計須現沖雜極參識費樣應議價請現為準續與兩萬雲關書買爭產優會傷倫體餘侶償兒黨蘭興養獸內岡冊寫軍農馮況凍淨淒減湊幾鳳憑凱擊芻劃劉則剛創刪別劑劇勸辦勵勁勞勢勳醫華協賣盧衛卻廳歷厲壓厭廁縣雙發變敘疊葉號嘆聽啟吳員團園圍圖圓場壞塊堅壇壩墜壟壘墾牆壯聲殼處備復夠頭夾奪奮獎奧妝婦媽娛婁嬌嬰孫學寧寶實寵審宮寬賓寢對尋導壽將爾塵嘗堯屍盡層屬屢歲豈崗島嶺嶽峽巒幣帥師帳簾幟帶幫常幹並廣莊慶廬庫應廟龐廢開異棄張彌弦彎彈強歸當錄徹徑憶憂懷態總戀懇惡驚懼慘慣憤願懶戲戰戶撲執擴掃揚擾撫拋搶護報擔擬攏揀擁攔撥擇掛摯攣撓擋掙擠揮撈損撿換據擄擲撣攬攙擱摟攪攜攝擺搖攤撐攆撷取數鬥斷無舊時曠晝顯晉曬曉暈暫曖術樸機殺雜權條來楊傑松板構樞槍楓櫃檸查柵標棧棟欄樹棲樣檔橋樺槳樁夢檢樓欖榆檻櫻櫥歡歐欲殲殘毆毀畢斃氣匯漢湯溝沒瀝淪滄滬濘淚瀉潑澤潔灑窪淺漿澆濁測濟瀏渾濃濤澇漣渦渙滌潤澗漲澀澱漸漁溫灣濕潰濺滾滿濾濫濱灘滅燈靈災燦爐煉爍爛煩燒燁燴燙熱煥愛爺牽犧犢狀猶狽獨狹獅獄獵豬貓獻瑪環現電畫暢療瘧癘瘍瘡瘋癢癆瘓癱癮癩皚皺盞鹽監蓋盜盤著睜睞瞼瞞矚矯礦碼磚硯礫礎碩確礙碎禮禱禍祿離禿種積稱穢穩穡穗窮竊竅窯竄窩窺豎競篤筆箋籠篩箏籌簽簡籃籬類糧緊糾紆紅紂纖約級紀緯純紗綱納縱紛紙紋紡紐線練組細織終絆紹經綁絨結繞繪給絡絕統絹繡繼績緒續綺緋綽繩維綿綬繃綢綜綻綰綠綴緘緬纜緝緞緩締縷編緣縛縫纏縭纓縮繳網羅罰罷羈翹聳恥聶聾職聯聰肅腸膚腎腫脹脅膽勝膠脈臟腦臉臘醃騰輿艦艙艱艷藝節蕪蘆蘇葦蒼範莖荊薦莢蕘蓽蕎薈薺蕩榮葷熒藥萊蓮蒔萵獲瑩鶯蘿螢營縈蕭薩蔥蔣蔞藍薊薔蘞藺蘊藪蘚虜慮虛蟲雖蝦蝕蟻螞蠶蠱蠣蟶蠻蟄蛺蛻蝸蠅蟬螻蟎蟒裊補裝褲見觀規覓視覽覺觸譽計訂認譏討讓訓議訊記講諱謳訝許訛論訟諷設訪訣證評識詐訴診詞譯試詩誠誅話誕詭詢該詳誡誣語誤誘誨說誦請諸諾讀課誰調諒談誼謀謊諫諧謔謂謁諭讒諮諳諺謎謝謠謗謙謹謾謫謬譚譜譴穀貝貞負貢財責賢敗賬貨質販貪貧貶購貯貫貳賤貼貴貸貿費賀貽賊賄賃賂贓資賑賒賦賭贖賞賜賠賴贅賺賽贊贈趙趕趨躍踐踴躊蹤躡蹣躪車軋軌軒轉輪軟轟軸輕載較輔輛輩輝輥輻輯輸轍轅轄輾轎辯辭辮邊遼達遷過邁運還這進遠違連遲邇跡適選遜遞邏遺郵鄰鄭醞醬釀採釋裏鑑釘針釣鈉鋼錢鐵鈴銅鋁銀鋪鏈銷鎖鍋鏽鋒銳錘錦鍵鋸鎮鏡鐮長門閃閉問闖閒間悶閘鬧聞閩閣閱閥閡鬮閬閾閹閶鬩閿閽閻閼闡闊闋闔闐闕隊陽陰陣階際陸陳險隨隱難雛靂霧霽靜韓頁頂頃項順須頑顧頓頒頌預領頗頸頡頰頜潁頦頤頻頹穎顆題顏額顛顫風飛飢飯飲飽飾餅餃餓餒餛館饋饞饃餾饅馬馭馱馴馳驅駁驢駐駝駛駒罵驕驊駱駭駢驪騁驗駿騎騙騷魚魯魴鮁鮃鯰鱸鮒鮑鱟鮐鮭鰈鮪鮐鯡鮫鮮鯗鱘鯁鱺鰱鰹鯉鰣鰷鯀鯊鯇鯽鯖鯪鯫鯡鯤鯧鯝鯢鯰鯛鯨鯴鯔鯴鰈鰓鱷鰍鰒鰉鯿鰠鰲鰭鰨鰥鰩鰳鰾鱈鰻鰲鱅鱖鱔鱗鳥鳩雞鳶鳴鷗鴉鴨鴆鴣鶇鸕鴨鴞鴦鴟鴝鴛鴕鷥鷙鴯鴝鵂鴿鸞鴻鵝鵒鷳鵜鵡鵲鵪鵬鶉鶘鶚鶻鶿鶥鶩鷂鶼鸚鷓鷚鷯鷦鷲鷸鷺鶴鷯鷹鹺麥麩黃齊齒齡龍龜"
            # Use a safe per-character table here: the long strings above are
            # kept as a broad reference set, while this avoids a bad optional
            # fallback should an uncommon mapping ever be duplicated.
            fallback = {
                "后": "後", "发": "發", "里": "裏", "这": "這", "为": "為", "经": "經", "纬": "緯", "路": "路", "线": "線", "地": "地", "点": "點",
                "收": "收", "藏": "藏", "设": "設", "置": "置", "颜": "顏", "色": "色", "选": "選", "择": "擇", "暂": "暫", "停": "停", "继": "繼", "续": "續",
                "运": "運", "行": "行", "时": "時", "间": "間", "速": "速", "度": "度", "开": "開", "始": "始", "结": "結", "束": "束", "确": "確", "认": "認",
                "删": "刪", "除": "除", "保": "保", "存": "存", "添": "添", "加": "加", "清": "清", "空": "空", "使": "使", "用": "用", "图": "圖", "标": "標",
                "名": "名", "称": "稱", "输": "輸", "入": "入", "坐": "坐", "标": "標", "移": "移", "动": "動", "范": "範", "围": "圍", "随": "隨", "机": "機",
                "状": "狀", "态": "態", "历": "歷", "史": "史", "无": "無", "还": "還", "没": "沒", "请": "請", "错": "錯", "误": "誤", "链": "鏈", "贴": "貼",
                "并": "並", "双": "雙", "击": "擊", "个": "個", "总": "總", "与": "與", "实": "實", "际": "際", "验": "驗", "证": "證", "启": "啟", "关": "關",
            }
            return "".join(fallback.get(char, char) for char in text)

    def _t(self, text: str) -> str:
        return EN.get(text, text) if self.language == "en" else self._to_traditional(text) if self.language == "zh-tw" else text

    def _load_theme(self):
        try:
            theme = json.loads(THEME_FILE.read_text(encoding="utf-8"))
            if all(isinstance(theme.get(key), str) and theme[key].startswith("#") for key in ("bg", "surface", "accent", "hover", "text", "muted", "border")):
                theme["name"] = {"浅蓝": "蓝色", "浅红": "红色", "浅绿": "绿色", "浅黄": "黄色", "浅紫": "紫色", "浅粉": "粉色"}.get(theme.get("name"), theme.get("name", "自定义"))
                return theme
        except Exception:
            pass
        return THEMES["蓝色"].copy()

    def _save_theme(self):
        save_json_atomically(THEME_FILE, self.theme)

    @staticmethod
    def _set_theme_globals(theme):
        global BG, SURFACE, TEXT, MUTED, BORDER, BLUE, BLUE_HOVER
        BG, SURFACE = theme["bg"], theme["surface"]
        TEXT, MUTED, BORDER = theme["text"], theme["muted"], theme["border"]
        BLUE, BLUE_HOVER = theme["accent"], theme["hover"]

    def _apply_theme(self, theme):
        self.theme = theme.copy()
        self._set_theme_globals(self.theme)
        self._save_theme()
        self._apply_style()
        self.window_title_label.setStyleSheet(f"color:{TEXT};")
        self.route_progress_text.setStyleSheet(f"color:{BLUE};")
        for label in self.findChildren(QLabel):
            tone = label.property("gps_theme_tone")
            if tone == "text":
                label.setStyleSheet(f"color:{TEXT};")
            elif tone == "muted":
                label.setStyleSheet(f"color:{MUTED};")
        self._refresh_bookmarks()
        self._refresh_location_history()
        self._set_status(self._status_source_text, self._status_color)
        if self._route_progress_state:
            self._update_route_progress(*self._route_progress_state)
        else:
            self._update_route_progress_display()

    def _register(self, kind: str, widget, source: str):
        widget.setProperty("gps_translation_kind", kind)
        widget.setProperty("gps_translation_source", source)
        self.translatables.append((kind, widget, source))
        return widget

    def _language_changed(self, choice: str):
        self.language = dict(LANGUAGE_CHOICES).get(choice, "zh")
        selected = self.stack.currentIndex()
        # Translate the live widget tree instead of only a bookkeeping list.
        # This also covers controls created before a dynamic refresh and avoids
        # a partial language change if a deleted widget was once registered.
        for widget in self.findChildren(QWidget):
            kind = widget.property("gps_translation_kind")
            source = widget.property("gps_translation_source")
            if not kind or source is None:
                continue
            try:
                if kind == "placeholder":
                    widget.setPlaceholderText(self._t(source))
                else:
                    widget.setText(self._t(source))
            except RuntimeError:
                continue
        self._select_tab(selected)
        self._refresh_bookmarks()
        self._refresh_location_history()
        if self._route_progress_state:
            self._update_route_progress(*self._route_progress_state)
        else:
            self._update_route_progress_display()
        self._set_status(self._status_source_text, self._status_color)

    def _open_settings(self):
        dialog = QDialog(self)
        dialog.setObjectName("settingsDialog")
        dialog.setWindowTitle(self._t("设置"))
        dialog.setMinimumWidth(470)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title = QLabel(self._t("⚙ 设置"))
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        layout.addWidget(title)

        language_title = QLabel(self._t("语言"))
        language_title.setObjectName("settingsSectionTitle")
        layout.addWidget(language_title)
        language_row = QHBoxLayout()
        for label, code in LANGUAGE_CHOICES:
            button = QPushButton(("✓  " if self.language == code else "") + label)
            button.setObjectName("settingsChoice")
            button.setProperty("selected", self.language == code)
            button.setMinimumHeight(38)
            button.clicked.connect(lambda _, value=label: (self._language_changed(value), dialog.accept()))
            language_row.addWidget(button)
        layout.addLayout(language_row)

        template_title = QLabel(self._t("主题模板"))
        template_title.setObjectName("settingsSectionTitle")
        layout.addWidget(template_title)
        template_grid = QGridLayout()
        template_grid.setHorizontalSpacing(8)
        template_grid.setVerticalSpacing(8)
        for index, (name, theme) in enumerate(THEMES.items()):
            button = QPushButton(self._t(name))
            button.setObjectName("themeTemplate")
            button.setMinimumHeight(42)
            button.setStyleSheet(f"background:{theme['accent']};color:white;border:2px solid {'#172B4D' if self.theme.get('name') == name else theme['accent']};border-radius:10px;font-weight:700;")
            button.clicked.connect(lambda _, value=theme.copy(): (self._apply_theme(value), dialog.accept()))
            template_grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(template_grid)

        custom_title = QLabel(self._t("自定义颜色"))
        custom_title.setObjectName("settingsSectionTitle")
        layout.addWidget(custom_title)
        custom_values = {key: self.theme[key] for key in ("bg", "surface", "accent")}
        color_buttons = {}
        color_grid = QGridLayout()
        for row, (key, label) in enumerate((("bg", "背景"), ("surface", "卡片"), ("accent", "主色"))):
            name_label = QLabel(self._t(label))
            color_button = QPushButton(custom_values[key])
            color_button.setObjectName("colorPicker")
            color_button.setMinimumHeight(34)
            color_button.setStyleSheet(f"background:{custom_values[key]};color:{'#FFFFFF' if QColor(custom_values[key]).lightness() < 150 else TEXT};border:0;border-radius:9px;")
            def choose_color(_, color_key=key, button=color_button, title=label):
                selected = QColorDialog.getColor(QColor(custom_values[color_key]), dialog, self._t(title))
                if selected.isValid():
                    custom_values[color_key] = selected.name()
                    button.setText(selected.name())
                    button.setStyleSheet(f"background:{selected.name()};color:{'#FFFFFF' if selected.lightness() < 150 else TEXT};border:0;border-radius:9px;")
            color_button.clicked.connect(choose_color)
            color_buttons[key] = color_button
            color_grid.addWidget(name_label, row, 0)
            color_grid.addWidget(color_button, row, 1)
        layout.addLayout(color_grid)
        apply_custom = QPushButton(self._t("应用自定义颜色"))
        apply_custom.setObjectName("applyTheme")
        apply_custom.setMinimumHeight(40)
        def apply_custom_theme():
            custom = self.theme.copy()
            custom.update({"name": "自定义", **custom_values, "hover": darken_color(custom_values["accent"])})
            self._apply_theme(custom)
            dialog.accept()
        apply_custom.clicked.connect(apply_custom_theme)
        layout.addWidget(apply_custom)

        emulator_title = QLabel(self._t("模拟器设置"))
        emulator_title.setObjectName("settingsSectionTitle")
        layout.addWidget(emulator_title)
        emulator_grid = QGridLayout()
        emulator_grid.setHorizontalSpacing(8)
        emulator_grid.setVerticalSpacing(8)
        manager_label = QLabel(self._t("MuMuManager 路径"))
        manager_path = QLineEdit(self.backend.config.get("manager_path", ""))
        manager_path.setClearButtonEnabled(True)
        manager_path.setMinimumHeight(36)
        browse = QPushButton(self._t("浏览…"))
        browse.setObjectName("settingsChoice")
        browse.setMinimumSize(86, 36)
        def browse_manager():
            selected, _ = QFileDialog.getOpenFileName(
                dialog,
                self._t("MuMuManager 路径"),
                manager_path.text() or str(Path.home()),
                "MuMuManager.exe (MuMuManager.exe);;Executable files (*.exe)",
            )
            if selected:
                manager_path.setText(selected)
        browse.clicked.connect(browse_manager)
        emulator_grid.addWidget(manager_label, 0, 0)
        emulator_grid.addWidget(manager_path, 0, 1)
        emulator_grid.addWidget(browse, 0, 2)

        layout.addLayout(emulator_grid)
        instance_label = QLabel(self._t("已添加的实例（定位会同时发送到所有实例）"))
        instance_label.setWordWrap(True)
        layout.addWidget(instance_label)

        instance_scroll = QScrollArea(dialog)
        instance_scroll.setWidgetResizable(True)
        instance_scroll.setFrameShape(QFrame.NoFrame)
        instance_scroll.setMaximumHeight(150)
        instance_list_widget = QWidget()
        instance_rows_layout = QVBoxLayout(instance_list_widget)
        instance_rows_layout.setContentsMargins(0, 0, 0, 0)
        instance_rows_layout.setSpacing(6)
        instance_scroll.setWidget(instance_list_widget)
        layout.addWidget(instance_scroll)
        instance_rows = []

        def renumber_instance_rows():
            for row_number, row in enumerate(instance_rows, 1):
                row["label"].setText(f"{self._t('模拟器实例编号')} {row_number}")

        def remove_instance_row(row_widget):
            for row in list(instance_rows):
                if row["widget"] is row_widget:
                    instance_rows.remove(row)
                    row_widget.setParent(None)
                    row_widget.deleteLater()
                    break
            renumber_instance_rows()

        def add_instance_row(value=""):
            if len(instance_rows) >= self.backend.MAX_INSTANCES:
                QMessageBox.warning(dialog, self._t("提示"), self._t(f"最多支持同时配置 {self.backend.MAX_INSTANCES} 个模拟器实例。"))
                return
            row_widget = QWidget(instance_list_widget)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            number_label = QLabel(f"{self._t('模拟器实例编号')} {len(instance_rows) + 1}")
            number_label.setMinimumWidth(145)
            number_entry = QLineEdit(str(value))
            number_entry.setPlaceholderText("0")
            number_entry.setValidator(QIntValidator(0, 999_999, dialog))
            number_entry.setMinimumHeight(36)
            delete_button = QPushButton(self._t("删除"))
            delete_button.setObjectName("settingsChoice")
            delete_button.setMinimumSize(72, 36)
            row_layout.addWidget(number_label)
            row_layout.addWidget(number_entry, 1)
            row_layout.addWidget(delete_button)
            instance_rows_layout.addWidget(row_widget)
            row = {"widget": row_widget, "entry": number_entry, "label": number_label}
            instance_rows.append(row)
            delete_button.clicked.connect(lambda _, w=row_widget: remove_instance_row(w))
            renumber_instance_rows()

        initial_indices = self.backend.config.get("instance_indices") or [self.backend.config.get("instance_index", "0")]
        for configured_index in initial_indices:
            add_instance_row(configured_index)

        instance_buttons = QHBoxLayout()
        add_instance_button = QPushButton("＋  " + self._t("添加实例"))
        add_instance_button.setObjectName("settingsChoice")
        add_instance_button.setMinimumHeight(36)
        instance_buttons.addWidget(add_instance_button)
        instance_buttons.addStretch(1)
        layout.addLayout(instance_buttons)

        def next_instance_index():
            used = set()
            for row in instance_rows:
                value = row["entry"].text().strip()
                if value.isdigit():
                    used.add(int(value))
            candidate = 1
            while candidate in used:
                candidate += 1
            return str(candidate)

        add_instance_button.clicked.connect(lambda: add_instance_row(next_instance_index()))

        def read_instance_indices():
            raw = [row["entry"].text().strip() for row in instance_rows]
            if any(value == "" for value in raw):
                raise ValueError("实例编号不能为空。")
            normalized_raw = [self.backend.normalize_instance(value) for value in raw]
            duplicates = []
            seen = set()
            for value in normalized_raw:
                if value in seen and value not in duplicates:
                    duplicates.append(value)
                seen.add(value)
            if duplicates:
                raise ValueError("实例编号重复：" + ", ".join(duplicates))
            return self.backend.normalize_instances(normalized_raw)

        emulator_actions = QHBoxLayout()
        test_connection = QPushButton(self._t("测试连接"))
        test_connection.setObjectName("settingsChoice")
        save_emulator = QPushButton(self._t("保存模拟器设置"))
        save_emulator.setObjectName("applyTheme")
        def test_emulator():
            try:
                indices = read_instance_indices()
                message = self.backend.test_connection(manager_path.text(), indices)
                if self.language == "en":
                    message = f"Configured {len(indices)} instances: {', '.join(indices)}. Configuration check completed; this does not confirm that the emulators are currently running."
                else:
                    message = self._t(message)
                QMessageBox.information(dialog, self._t("测试成功"), message)
            except Exception as exc:
                QMessageBox.critical(dialog, self._t("测试失败"), self._t(str(exc)))
        def save_emulator_settings():
            try:
                indices = read_instance_indices()
                self.backend.save(manager_path.text(), indices)
                QMessageBox.information(dialog, self._t("保存成功"), self._t("设置已保存。"))
            except Exception as exc:
                QMessageBox.critical(dialog, self._t("保存失败"), self._t(str(exc)))
        test_connection.clicked.connect(test_emulator)
        save_emulator.clicked.connect(save_emulator_settings)
        emulator_actions.addWidget(test_connection)
        emulator_actions.addWidget(save_emulator)
        layout.addLayout(emulator_actions)
        close = QPushButton(self._t("关闭"))
        close.setMinimumHeight(36)
        close.clicked.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def _select_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        for item_index, button in enumerate(self.tab_buttons):
            button.setProperty("selected", item_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    # ---- widget factories --------------------------------------------
    def _card(self, parent=None):
        frame = QFrame(parent)
        frame.setObjectName("card")
        return frame

    def _label(self, text: str, size=13, color=TEXT, bold=False):
        label = QLabel(self._t(text))
        label.setWordWrap(True)
        label.setFont(QFont("Microsoft YaHei UI", size + 1, QFont.Bold if bold else QFont.Normal))
        if color == TEXT:
            label.setProperty("gps_theme_tone", "text")
        elif color == MUTED:
            label.setProperty("gps_theme_tone", "muted")
        else:
            label.setStyleSheet(f"color:{color};")
        return self._register("label", label, text)

    def _heading(self, text: str):
        label = self._label(text, 15, TEXT, True)
        label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        return label

    def _entry(self, placeholder="", value=""):
        entry = QLineEdit(value)
        entry.setPlaceholderText(self._t(placeholder))
        entry.setClearButtonEnabled(True)
        entry.setMinimumHeight(42)
        entry.setFont(QFont("Segoe UI", 11))
        return self._register("placeholder", entry, placeholder)

    def _button(self, text: str, command, primary=False):
        button = QPushButton(self._t(text))
        button.setProperty("primary", primary)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(40)
        button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        button.clicked.connect(command)
        return self._register("button", button, text)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                GPSWindow._clear_layout(item.layout())

    @staticmethod
    def _insert_before_stretch(layout, widget):
        layout.insertWidget(max(0, layout.count() - 1), widget)

    def _scroll_page(self):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addStretch(1)
        area.setWidget(body)
        return area, layout

    # ---- layout -------------------------------------------------------
    def _build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 20, 18, 16)
        outer.setSpacing(10)
        header = QHBoxLayout()
        header.setContentsMargins(8, 0, 8, 0)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.window_title_label = QLabel(APP_TITLE)
        self.window_title_label.setFont(QFont("Segoe UI", 30, QFont.Bold))
        self.window_title_label.setStyleSheet(f"color:{TEXT};")
        title_box.addWidget(self.window_title_label)
        title_box.addWidget(self._label("COORDINATE  ·  OPTIONAL SHORT WALK  ·  ROUTE WALK", 10, MUTED))
        header.addLayout(title_box)
        header.addStretch(1)
        self.settings_button = self._button("⚙ 设置", self._open_settings)
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(150, 38)
        self.settings_button.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        header.addWidget(self.settings_button)
        outer.addLayout(header)

        navigation = QHBoxLayout()
        navigation.setContentsMargins(0, 0, 0, 0)
        navigation.setSpacing(4)
        navigation.addStretch(1)
        self.tab_buttons = []
        self.stack = QStackedWidget()
        self.gps_area, self.gps_layout = self._scroll_page()
        self.saved_area, self.saved_layout = self._scroll_page()
        self.route_area, self.route_layout = self._scroll_page()
        for index, (name, page) in enumerate((("GPS 定位", self.gps_area), ("收藏地点", self.saved_area), ("路线行走", self.route_area))):
            button = QPushButton(self._t(name))
            button.setObjectName("navigationTab")
            button.setProperty("selected", index == 0)
            button.setFixedHeight(42)
            button.setMinimumWidth(120)
            button.setCursor(Qt.PointingHandCursor)
            button.setFont(QFont("Segoe UI", 10, QFont.Bold))
            button.clicked.connect(lambda _, value=index: self._select_tab(value))
            navigation.addWidget(button)
            self.tab_buttons.append(button)
            self._register("button", button, name)
            self.stack.addWidget(page)
        navigation.addStretch(1)
        outer.addLayout(navigation)
        self._build_gps_tab()
        self._build_saved_tab()
        self._build_route_tab()
        content_panel = self._card()
        content_panel.setObjectName("contentPanel")
        content_layout = QVBoxLayout(content_panel)
        content_layout.setContentsMargins(4, 2, 4, 4)
        content_layout.addWidget(self.stack)
        outer.addWidget(content_panel, 1)

        status = self._card()
        status_layout = QVBoxLayout(status)
        status_layout.setContentsMargins(16, 12, 16, 12)
        status_layout.setSpacing(6)
        status_head = QHBoxLayout()
        status_head.addWidget(self._label("运行状态", 12, TEXT, True))
        status_head.addStretch(1)
        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Segoe UI", 12, QFont.Bold))
        status_head.addWidget(self.status_dot)
        status_layout.addLayout(status_head)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setFont(QFont("Microsoft YaHei UI", 11))
        status_layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        status_layout.addWidget(self.progress)
        outer.addWidget(status)
        self.setCentralWidget(root)

    def _section(self, target, title: str, desc: str | None = None):
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self._heading(title))
        if desc:
            layout.addWidget(self._label(desc, 10, MUTED))
        self._insert_before_stretch(target, card)
        return layout

    def _build_gps_tab(self):
        link = self._section(self.gps_layout, "Google Maps 链接")
        self.maps_entry = self._entry("粘贴 Google Maps 分享链接或输入 纬度,经度")
        link.addWidget(self.maps_entry)
        actions = QHBoxLayout()
        actions.addWidget(self._button("解析链接 / 坐标", self._parse_gps_entry, True))
        actions.addWidget(self._button("清空", self.maps_entry.clear))
        actions.addStretch(1)
        link.addLayout(actions)

        coords = self._section(self.gps_layout, "手动坐标")
        coords.addWidget(self._label("纬度 Latitude", 10, MUTED))
        self.lat_entry = self._entry(value=self.manual_input_cache.get("lat", ""))
        coords.addWidget(self.lat_entry)
        coords.addWidget(self._label("经度 Longitude", 10, MUTED))
        self.lon_entry = self._entry(value=self.manual_input_cache.get("lon", ""))
        coords.addWidget(self.lon_entry)
        self.lat_entry.textChanged.connect(self._save_manual_inputs)
        self.lon_entry.textChanged.connect(self._save_manual_inputs)

        walk = self._section(self.gps_layout, "传送后原地随机走动", "可选功能：在目标附近移动一段时间，然后返回起点。")
        random_toggle = QHBoxLayout()
        self.random_enabled = FavoriteCheckBox()
        random_toggle.addWidget(self.random_enabled)
        random_toggle.addWidget(self._label("启用随机走动", 10, TEXT))
        random_toggle.addStretch(1)
        walk.addLayout(random_toggle)
        settings = QGridLayout()
        settings.setHorizontalSpacing(16)
        settings.addWidget(self._label("持续时间（秒）", 10, MUTED), 0, 0)
        settings.addWidget(self._label("活动范围半径（米）", 10, MUTED), 0, 1)
        self.random_duration, self.random_radius = self._entry(value="10"), self._entry(value="50")
        settings.addWidget(self.random_duration, 1, 0)
        settings.addWidget(self.random_radius, 1, 1)
        walk.addLayout(settings)
        walk.addWidget(self._label("时间 1–600 秒 · 半径 1–100 米", 9, MUTED))
        start = self._button("◎   设置虚拟定位", self._set_manual_location, True)
        start.setMinimumHeight(48)
        self._insert_before_stretch(self.gps_layout, start)
        self._insert_before_stretch(self.gps_layout, self._button("停止当前任务", self._stop))

        history = self._section(self.gps_layout, "定位历史")
        top = QHBoxLayout()
        top.addStretch(1)
        clear = self._button("清空", self._clear_location_history)
        clear.setFixedSize(90, 30)
        top.addWidget(clear)
        history.addLayout(top)
        self.history_list = QVBoxLayout()
        self.history_list.setSpacing(4)
        history.addLayout(self.history_list)

    def _build_saved_tab(self):
        saved = self._section(self.saved_layout, "我的定位收藏", "保存常用地点，设置图标和颜色；星标地点可以置顶。")
        self.bookmark_list = QVBoxLayout()
        self.bookmark_list.setSpacing(5)
        saved.addLayout(self.bookmark_list)
        actions = QGridLayout()
        actions.addWidget(self._button("＋ 添加地点", self._add_bookmark, True), 0, 0)
        actions.addWidget(self._button("编辑", self._edit_bookmark), 0, 1)
        actions.addWidget(self._button("删除", self._delete_bookmark), 0, 2)
        saved.addLayout(actions)
        order = QGridLayout()
        for index, (text, fn) in enumerate((("★ 星标", self._toggle_favorite), ("置顶", self._move_top), ("上移", lambda: self._move(-1)), ("下移", lambda: self._move(1)))):
            order.addWidget(self._button(text, fn), 0, index)
        saved.addLayout(order)
        teleport = self._button("◎   传送到选中地点", self._teleport_bookmark, True)
        teleport.setMinimumHeight(46)
        saved.addWidget(teleport)
        saved.addWidget(self._label("双击地点卡片也可以快速传送。", 9, MUTED))

    def _build_route_tab(self):
        stops = self._section(self.route_layout, "路线地点", "一个地点一行输入：纬度,经度 或 Google Maps 链接。至少需要两个地点。")
        self.route_points_layout = QVBoxLayout()
        self.route_points_layout.setSpacing(5)
        stops.addLayout(self.route_points_layout)
        # First launch: no draft exists, so show two empty rows. Once the user
        # has entered Stops, the JSON draft is restored on the next launch.
        initial_stops = self.route_draft if self.route_draft is not None else ["", ""]
        self._restoring_route_draft = True
        try:
            for value in initial_stops:
                self._add_route_row(value)
        finally:
            self._restoring_route_draft = False
        add = self._button("＋ 添加地点", self._add_route_row)
        add.setMinimumHeight(36)
        stops.addWidget(add)
        validate = self._button("检查路线点", self._validate_route)
        validate.setMinimumWidth(205)
        validate.setMinimumHeight(44)
        validate.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        stops.addWidget(validate)

        progress_card = self._card()
        progress = QVBoxLayout(progress_card)
        progress.setContentsMargins(18, 15, 18, 15)
        progress.setSpacing(9)
        heading = QHBoxLayout()
        heading.addWidget(self._heading("路线进度 Progress"))
        heading.addStretch(1)
        self.route_progress_text = QLabel("0.0%")
        self.route_progress_text.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.route_progress_text.setStyleSheet(f"color:{BLUE};")
        heading.addWidget(self.route_progress_text)
        progress.addLayout(heading)
        self.route_progress = QProgressBar()
        self.route_progress.setRange(0, 100)
        self.route_progress.setTextVisible(False)
        progress.addWidget(self.route_progress)
        self.route_progress_detail = QLabel()
        self.route_progress_detail.setWordWrap(True)
        self.route_progress_detail.setStyleSheet(f"color:{MUTED};")
        progress.addWidget(self.route_progress_detail)
        self._insert_before_stretch(self.route_layout, progress_card)

        movement = self._section(self.route_layout, "移动参数")
        parameters = QGridLayout()
        parameters.setHorizontalSpacing(16)
        parameters.addWidget(self._label("速度（km/h）", 10, MUTED), 0, 0)
        parameters.addWidget(self._label("更新间隔（秒）", 10, MUTED), 0, 1)
        self.route_speed, self.route_interval = self._entry(value="5"), self._entry(value="1")
        parameters.addWidget(self.route_speed, 1, 0)
        parameters.addWidget(self.route_interval, 1, 1)
        movement.addLayout(parameters)
        buttons = QGridLayout()
        buttons.addWidget(self._button("开始路线", self._start_route, True), 0, 0)
        buttons.addWidget(self._button("暂停 / 继续", self._toggle_pause), 0, 1)
        buttons.addWidget(self._button("停止", self._confirm_stop_route), 0, 2)
        movement.addLayout(buttons)
        self._update_route_progress_display()

    def _add_route_row(self, value=""):
        if isinstance(value, bool):
            value = ""
        translation_mark = len(self.translatables)
        row = QFrame()
        row.setObjectName("routeRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(6)
        number = QLabel()
        number.setObjectName("routeNumber")
        number.setAlignment(Qt.AlignCenter)
        number.setFixedSize(28, 28)
        number.setFont(QFont("Segoe UI", 10, QFont.Bold))
        entry = self._entry("纬度,经度 / Google Maps URL", value)
        entry.setMinimumHeight(38)
        entry.editingFinished.connect(self._save_route_draft)
        remove = self._button("×", lambda: self._remove_route_row(row))
        remove.setObjectName("routeRemove")
        remove.setFixedSize(34, 34)
        layout.addWidget(number)
        layout.addWidget(entry, 1)
        layout.addWidget(remove)
        self.route_points_layout.addWidget(row)
        self.route_rows.append({"frame": row, "number": number, "entry": entry, "translations": self.translatables[translation_mark:]})
        self._renumber_route_rows()
        if not self._restoring_route_draft:
            self._save_route_draft()

    def _remove_route_row(self, row):
        if len(self.route_rows) <= 2:
            QMessageBox.information(self, self._t("路线地点"), self._t("路线至少需要保留两个地点。"))
            return
        for item in self.route_rows[:]:
            if item["frame"] is row:
                for translation in item["translations"]:
                    if translation in self.translatables:
                        self.translatables.remove(translation)
                self.route_rows.remove(item)
                self.route_points_layout.removeWidget(row)
                row.deleteLater()
                break
        self._renumber_route_rows()
        self._save_route_draft()

    def _renumber_route_rows(self):
        for index, row in enumerate(self.route_rows, 1):
            row["number"].setText(str(index))

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow,QWidget {{ background:{BG}; color:{TEXT}; font-family:'Microsoft YaHei UI','Segoe UI'; font-size:10pt; }}
            QFrame#card,QFrame#contentPanel {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:12px; }}
            QFrame#routeRow {{ background:{SURFACE_ALT}; border:0; border-radius:10px; }}
            QLabel#routeNumber {{ background:#E4ECF8; color:{TEXT}; border-radius:8px; }}
            QLineEdit {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER}; border-radius:12px; padding:8px 10px; selection-background-color:{BLUE}; }}
            QLineEdit:focus {{ border-color:{BLUE}; }}
            QPushButton {{ background:#EAF0F8; color:#31435E; border:0; border-radius:12px; padding:8px; font-weight:600; }}
            QPushButton:hover {{ background:#DDE7F5; }} QPushButton[primary="true"] {{ background:{BLUE}; color:white; }} QPushButton[primary="true"]:hover {{ background:{BLUE_HOVER}; }}
            QPushButton#settingsButton {{ background:{BG}; color:{TEXT}; border:1px solid {BORDER}; border-radius:12px; padding:8px 10px; }}
            QPushButton#settingsButton:hover {{ background:#E8EEF8; }}
            QDialog#settingsDialog {{ background:{BG}; }} QLabel#settingsSectionTitle {{ color:{TEXT}; font-size:12pt; font-weight:700; margin-top:5px; }}
            QPushButton#settingsChoice {{ background:{SURFACE}; color:{TEXT}; border:1px solid {BORDER}; border-radius:10px; padding:7px; }}
            QPushButton#settingsChoice:hover {{ background:#E8EEF8; border-color:{BLUE}; }} QPushButton#settingsChoice[selected="true"] {{ background:{BLUE}; color:white; border-color:{BLUE}; }}
            QPushButton#applyTheme {{ background:{BLUE}; color:white; border-radius:10px; font-weight:700; }} QPushButton#applyTheme:hover {{ background:{BLUE_HOVER}; }}
            QPushButton#routeRemove {{ background:#FDECEC; color:#B83232; border-radius:9px; padding:0; }} QPushButton#routeRemove:hover {{ background:#F8D5D5; }}
            QPushButton#navigationTab {{ background:#EAF0F8; color:{TEXT}; border:0; border-radius:15px; padding:8px 18px; font-weight:700; }}
            QPushButton#navigationTab:hover {{ background:#DDE7F5; }}
            QPushButton#navigationTab[selected="true"] {{ background:{BLUE}; color:white; }}
            QPushButton#navigationTab[selected="true"]:hover {{ background:{BLUE_HOVER}; }}
            QProgressBar {{ background:#E7EDF5; border:0; border-radius:4px; height:8px; }} QProgressBar::chunk {{ background:{BLUE}; border-radius:4px; }}
            QScrollArea {{ border:0; background:transparent; }} QCheckBox {{ spacing:8px; }}
            QCheckBox::indicator {{ width:20px; height:20px; border:2px solid #CBD5E1; border-radius:6px; background:white; }} QCheckBox::indicator:checked {{ background:{BLUE}; border-color:{BLUE}; }}
            QScrollBar:vertical {{ background:transparent; width:10px; margin:4px 2px; }}
            QScrollBar::handle:vertical {{ background:#C8D4E4; min-height:38px; border-radius:5px; }}
            QScrollBar::handle:vertical:hover {{ background:#AABBD0; }}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; background:transparent; border:0; }}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {{ background:transparent; }}
            QScrollBar:horizontal {{ height:0; }}
        """)

    # ---- saved data ---------------------------------------------------
    def _load_bookmarks(self):
        try:
            if not DATA_FILE.exists():
                return
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                data = {"bookmarks": data}
            if not isinstance(data, dict):
                return

            bookmarks = data.get("bookmarks", [])
            history = data.get("history", [])
            routes = data.get("route_history", [])
            self.bookmarks = [
                x for x in bookmarks
                if isinstance(x, dict) and isinstance(x.get("name"), str)
                and isinstance(x.get("lat"), (int, float)) and isinstance(x.get("lon"), (int, float))
                and valid_coordinates(float(x["lat"]), float(x["lon"]))
            ] if isinstance(bookmarks, list) else []
            self.location_history = [
                x for x in history
                if isinstance(x, dict) and isinstance(x.get("lat"), (int, float))
                and isinstance(x.get("lon"), (int, float))
                and valid_coordinates(float(x["lat"]), float(x["lon"]))
            ][-100:] if isinstance(history, list) else []
            self.route_history = [
                x for x in routes if isinstance(x, dict) and isinstance(x.get("points"), list)
            ][-30:] if isinstance(routes, list) else []

            # Last manual location is a single replaceable cache, never a list.
            manual = data.get("last_manual_location")
            if isinstance(manual, dict):
                lat, lon = manual.get("lat"), manual.get("lon")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and valid_coordinates(float(lat), float(lon)):
                    self.last_manual_location = (float(lat), float(lon))

            # Preserve every Route Walk input row, including empty rows, so both
            # the entered values and the number of stops survive a restart.
            draft = data.get("route_draft")
            if isinstance(draft, dict) and isinstance(draft.get("stops"), list):
                stops = [str(value) for value in draft["stops"]]
                try:
                    stop_count = int(draft.get("stop_count", len(stops)))
                except (TypeError, ValueError):
                    stop_count = len(stops)
                stop_count = max(2, min(1000, stop_count))
                stops = stops[:stop_count]
                if len(stops) < stop_count:
                    stops.extend([""] * (stop_count - len(stops)))
                self.route_draft = stops
        except Exception:
            self.bookmarks, self.location_history, self.route_history = [], [], []
            self.last_manual_location, self.route_draft = None, None

    def _save_bookmarks(self):
        route_stops = [row["entry"].text() for row in getattr(self, "route_rows", [])]
        manual = None
        if self.last_manual_location is not None:
            manual = {"lat": self.last_manual_location[0], "lon": self.last_manual_location[1]}
        manual_inputs = getattr(self, "manual_input_cache", {"lat": "", "lon": ""}).copy()
        if hasattr(self, "lat_entry") and hasattr(self, "lon_entry"):
            manual_inputs = {"lat": self.lat_entry.text(), "lon": self.lon_entry.text()}
            self.manual_input_cache = manual_inputs.copy()
        data = {
            "version": 4,
            "bookmarks": self.bookmarks,
            "history": self.location_history[-100:],
            "route_history": self.route_history[-30:],
            "last_manual_location": manual,
            "manual_input": manual_inputs,
            "route_draft": {"stop_count": len(route_stops), "stops": route_stops},
        }
        save_json_atomically(DATA_FILE, data)

    def _save_manual_inputs(self, *_args):
        """Persist the visible coordinate fields, including incomplete drafts."""
        self.manual_input_cache = {"lat": self.lat_entry.text(), "lon": self.lon_entry.text()}
        self._save_bookmarks()

    def _save_route_draft(self, *_args):
        if self._restoring_route_draft:
            return
        self.route_draft = [row["entry"].text() for row in self.route_rows]
        self._save_bookmarks()

    def _save_manual_location(self, lat, lon):
        """Replace the single cached manual coordinate pair."""
        lat, lon = float(lat), float(lon)
        if not valid_coordinates(lat, lon):
            return
        self.last_manual_location = (lat, lon)
        self._save_bookmarks()

    def _record_location(self, lat, lon, source="GPS定位"):
        try:
            lat, lon = float(lat), float(lon)
            if not valid_coordinates(lat, lon):
                return
            record = {"lat": lat, "lon": lon, "source": source, "time": datetime.now().astimezone().isoformat(timespec="seconds")}
            with self.history_lock:
                if self.location_history:
                    last = self.location_history[-1]
                    if abs(float(last.get("lat", 999)) - lat) < 1e-7 and abs(float(last.get("lon", 999)) - lon) < 1e-7 and last.get("source") == source:
                        return
                self.location_history = (self.location_history + [record])[-100:]
                self._save_bookmarks()
            self._refresh_location_history()
        except Exception as exc:
            print(f"Could not save location history: {exc}")

    def _record_route(self, points):
        """Store the route itself without pretending every stop was visited."""
        clean = [{"lat": float(lat), "lon": float(lon)} for lat, lon in points if valid_coordinates(float(lat), float(lon))]
        if len(clean) < 2:
            return
        with self.history_lock:
            self.route_history = (self.route_history + [{"time": datetime.now().astimezone().isoformat(timespec="seconds"), "points": clean}])[-30:]
            self._save_bookmarks()

    # ---- history and bookmark UI -------------------------------------
    def _refresh_location_history(self):
        if not hasattr(self, "history_list"):
            return
        translation_mark = len(self.translatables)
        self._clear_layout(self.history_list)
        if not self.location_history:
            self.history_list.addWidget(self._label("暂无定位历史", 10, MUTED))
        else:
            sources = {"GPS": "GPS定位", "GPS定位": "GPS定位", "Route Walk": "路线行走", "路线行走": "路线行走"}
            for item in reversed(self.location_history[-20:]):
                row = QFrame()
                row.setObjectName("routeRow")
                layout = QHBoxLayout(row)
                layout.setContentsMargins(10, 7, 8, 7)
                info = QVBoxLayout()
                coordinate = QLabel(f'{item["lat"]:.6f}, {item["lon"]:.6f}')
                coordinate.setFont(QFont("Segoe UI", 11, QFont.Bold))
                details = QLabel(f'{self._t(sources.get(item.get("source", "GPS定位"), item.get("source", "GPS定位")))} · {str(item.get("time", "")).replace("T", " ")}')
                details.setFont(QFont("Segoe UI", 9))
                details.setStyleSheet(f"color:{MUTED};")
                info.addWidget(coordinate)
                info.addWidget(details)
                layout.addLayout(info, 1)
                use = self._button("使用", lambda _, lat=item["lat"], lon=item["lon"]: self._use_history_location(lat, lon))
                use.setFixedSize(58, 30)
                layout.addWidget(use)
                self.history_list.addWidget(row)
        del self.translatables[translation_mark:]

    def _use_history_location(self, lat, lon):
        self.lat_entry.setText(str(lat))
        self.lon_entry.setText(str(lon))
        self._select_tab(0)
        self.lat_entry.setFocus()

    def _clear_location_history(self):
        if self.location_history or self.route_history:
            if QMessageBox.question(self, self._t("确认"), self._t("确定清空定位历史和路线历史吗？"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                self.location_history, self.route_history = [], []
                self._save_bookmarks()
                self._refresh_location_history()

    def _refresh_bookmarks(self):
        if not hasattr(self, "bookmark_list"):
            return
        translation_mark = len(self.translatables)
        self._clear_layout(self.bookmark_list)
        self.bookmark_cards = []
        if not self.bookmarks:
            card = self._card()
            layout = QVBoxLayout(card)
            label = self._label("还没有收藏地点", 12, MUTED)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            self.bookmark_list.addWidget(card)
        else:
            for index, item in enumerate(self.bookmarks):
                selected, color = self.selected_bookmark == index, item.get("color", BLUE)
                card = ClickableFrame()
                card.setObjectName("bookmarkCard")
                self._style_bookmark_card(card, color, selected)
                card.double_clicked.connect(lambda i=index: self._teleport_bookmark(i))
                layout = QHBoxLayout(card)
                layout.setContentsMargins(9, 8, 10, 8)
                icon = QPushButton(("★ " if item.get("favorite") else "") + item.get("icon", "📍"))
                icon.setFixedSize(52, 54)
                icon.setFont(QFont("Segoe UI Emoji", 18))
                icon.setStyleSheet(f"background:{color};color:white;border:0;border-radius:11px;")
                icon.clicked.connect(lambda _, i=index: self._select_bookmark(i))
                layout.addWidget(icon)
                info = QVBoxLayout()
                name = QLabel(item["name"])
                name.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
                details = QLabel(f'{float(item["lat"]):.6f}, {float(item["lon"]):.6f}')
                details.setStyleSheet(f"color:{MUTED};")
                info.addWidget(name)
                info.addWidget(details)
                layout.addLayout(info, 1)
                teleport = self._button("传送", lambda _, i=index: self._teleport_bookmark(i), True)
                teleport.setFixedSize(66, 34)
                layout.addWidget(teleport)
                self.bookmark_list.addWidget(card)
                self.bookmark_cards.append(card)
        del self.translatables[translation_mark:]

    @staticmethod
    def _style_bookmark_card(card, color, selected):
        card.setStyleSheet(f"QFrame#bookmarkCard {{background:{'#EEF4FF' if selected else SURFACE_ALT};border:1px solid {color if selected else BORDER};border-radius:14px;}}")

    def _select_bookmark(self, index):
        self.selected_bookmark = index
        for i, card in enumerate(self.bookmark_cards):
            self._style_bookmark_card(card, self.bookmarks[i].get("color", BLUE), i == index)

    def _selected_index(self):
        if self.selected_bookmark is None or not 0 <= self.selected_bookmark < len(self.bookmarks):
            QMessageBox.information(self, self._t("提示"), self._t("请先选择一个收藏地点。"))
            return None
        return self.selected_bookmark

    def _bookmark_editor(self, title, initial=None):
        initial = initial or {}
        translation_mark = len(self.translatables)
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t(title))
        dialog.setMinimumSize(400, 600)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.addWidget(self._heading(title))
        def field(label, value):
            layout.addWidget(self._label(label, 10, MUTED, True))
            edit = self._entry(value=value)
            layout.addWidget(edit)
            return edit
        name = field("地点名称", str(initial.get("name", "")))
        lat = field("纬度 Latitude", str(initial.get("lat", self.lat_entry.text())))
        lon = field("经度 Longitude", str(initial.get("lon", self.lon_entry.text())))
        layout.addWidget(self._heading("选择图标"))
        icon_value = [initial.get("icon", "📍")]
        icons = ["📍", "⭐", "🏠", "🏫", "🏢", "🗼", "🚉", "🍜", "☕", "🛍️", "🎮", "🌸", "❤️", "🔥", "💎"]
        icon_grid, icon_buttons = QGridLayout(), []
        def refresh_icons():
            for value, button in icon_buttons:
                button.setStyleSheet(f"background:#EEF3FA;color:{TEXT};border:{2 if icon_value[0] == value else 0}px solid #000;border-radius:10px;")
        for i, symbol in enumerate(icons):
            button = QPushButton(symbol)
            button.setFixedSize(42, 38)
            button.setFont(QFont("Segoe UI Emoji", 17))
            button.clicked.connect(lambda _, x=symbol: (icon_value.__setitem__(0, x), refresh_icons()))
            icon_buttons.append((symbol, button))
            icon_grid.addWidget(button, i // 5, i % 5)
        refresh_icons()
        layout.addLayout(icon_grid)
        layout.addWidget(self._heading("选择颜色"))
        color_value = [initial.get("color", BLUE)]
        colors = [("蓝色", "#3478F6"), ("紫色", "#805AD5"), ("粉色", "#D9468F"), ("红色", "#DC5252"), ("橙色", "#E58A35"), ("绿色", "#159B68"), ("青色", "#1597A5"), ("金色", "#C99A27")]
        color_grid, color_buttons = QGridLayout(), []
        def refresh_colors():
            for value, button in color_buttons:
                button.setStyleSheet(f"background:{darken_color(value, .68) if color_value[0].lower() == value.lower() else value};color:white;border:0;border-radius:10px;")
        for i, (label, value) in enumerate(colors):
            button = QPushButton(self._t(label))
            button.setFixedSize(76, 38)
            button.clicked.connect(lambda _, x=value: (color_value.__setitem__(0, x), refresh_colors()))
            color_buttons.append((value, button))
            color_grid.addWidget(button, i // 4, i % 4)
        refresh_colors()
        layout.addLayout(color_grid)
        favorite_row = QHBoxLayout()
        favorite = FavoriteCheckBox()
        favorite.setChecked(bool(initial.get("favorite", False)))
        favorite_row.addWidget(favorite)
        favorite_row.addWidget(self._label("设为收藏", 10, TEXT))
        favorite_row.addStretch(1)
        layout.addLayout(favorite_row)
        result = {"value": None}
        save = self._button("保存地点", lambda: None, True)
        def commit():
            try:
                label, latitude, longitude = name.text().strip(), float(lat.text()), float(lon.text())
                if not label:
                    raise ValueError("请输入地点名称。")
                if not valid_coordinates(latitude, longitude):
                    raise ValueError("坐标范围不正确。")
                result["value"] = {"name": label, "lat": latitude, "lon": longitude, "icon": icon_value[0], "color": color_value[0], "favorite": favorite.isChecked()}
                dialog.accept()
            except ValueError as exc:
                QMessageBox.critical(dialog, self._t("输入错误"), self._t(str(exc)))
        save.clicked.disconnect()
        save.clicked.connect(commit)
        layout.addWidget(save)
        accepted = dialog.exec() == QDialog.Accepted
        # Dialog-local widgets are already rendered in the active language;
        # never retain wrappers for widgets that will be destroyed with it.
        del self.translatables[translation_mark:]
        return result["value"] if accepted else None

    def _add_bookmark(self):
        try:
            lat, lon = float(self.lat_entry.text()), float(self.lon_entry.text())
            if not valid_coordinates(lat, lon):
                raise ValueError("当前坐标无效。")
        except ValueError as exc:
            QMessageBox.critical(self, self._t("坐标错误"), self._t(str(exc)))
            return
        if item := self._bookmark_editor("添加收藏地点", {"lat": lat, "lon": lon}):
            self.bookmarks.append(item)
            self.selected_bookmark = len(self.bookmarks) - 1
            self._save_bookmarks()
            self._refresh_bookmarks()

    def _edit_bookmark(self):
        if (index := self._selected_index()) is not None and (item := self._bookmark_editor("编辑收藏地点", self.bookmarks[index].copy())):
            self.bookmarks[index] = item
            self._save_bookmarks()
            self._refresh_bookmarks()

    def _delete_bookmark(self):
        if (index := self._selected_index()) is None:
            return
        name = self.bookmarks[index]["name"]
        message = f'Delete “{name}”?' if self.language == "en" else f'确定删除「{name}」吗？'
        if QMessageBox.question(self, self._t("确认删除"), message) == QMessageBox.Yes:
            del self.bookmarks[index]
            self.selected_bookmark = None
            self._save_bookmarks()
            self._refresh_bookmarks()

    def _toggle_favorite(self):
        if (index := self._selected_index()) is not None:
            self.bookmarks[index]["favorite"] = not self.bookmarks[index].get("favorite", False)
            self._save_bookmarks()
            self._refresh_bookmarks()

    def _move(self, offset):
        if (index := self._selected_index()) is not None and 0 <= index + offset < len(self.bookmarks):
            target = index + offset
            self.bookmarks[index], self.bookmarks[target] = self.bookmarks[target], self.bookmarks[index]
            self.selected_bookmark = target
            self._save_bookmarks()
            self._refresh_bookmarks()

    def _move_top(self):
        if (index := self._selected_index()) not in (None, 0):
            self.bookmarks.insert(0, self.bookmarks.pop(index))
            self.selected_bookmark = 0
            self._save_bookmarks()
            self._refresh_bookmarks()

    def _teleport_bookmark(self, index=None):
        if isinstance(index, bool) or index is None:
            index = self._selected_index()
        if index is None:
            return
        item = self.bookmarks[index]
        self.lat_entry.setText(str(item["lat"]))
        self.lon_entry.setText(str(item["lon"]))
        self._select_tab(0)
        self._set_manual_location()

    # ---- backend ------------------------------------------------------
    def _instances(self):
        return self.backend.configured_indices()

    def _api_location(self, lat, lon):
        # Fan one coordinate out concurrently to all configured emulator indexes.
        # Backend creates and selects a fresh Mumu client inside each worker thread.
        self.backend.broadcast_location(lat, lon)
        return True

    def _translate_status_message(self, message):
        text = str(message)
        if self.language == "zh-tw":
            return self._to_traditional(text)
        if self.language != "en":
            return text
        if text in EN:
            return EN[text]
        for old, new in (("任务失败：", "Task failed: "), ("定位成功\n纬度：", "Location set successfully\nLatitude: "), ("\n经度：", "\nLongitude: "), ("解析成功：", "Parsed: "), ("定位失败：", "Location failed: "), ("路线行走失败：", "Route Walk failed: "), ("附近随机走动中 · 剩余 ", "Nearby random walk · "), (" 秒 · 距起点 ", " sec remaining · "), (" 米", " m"), ("传送成功，开始附近随机走动 ", "Teleport successful; starting nearby random walk for "), (" 秒……", " seconds…"), ("路线行走开始 · ", "Route Walk started · "), (" 个路线点", " route stops"), ("路线行走 · 第 ", "Route Walk · Segment "), (" 段 · ", " · "), ("当前位置：", "Current position: "), ("路线有效：", "Route valid: "), (" 个点 · 总直线距离 ", " stops · total straight-line distance ")):
            text = text.replace(old, new)
        return text

    def _set_status(self, message, color=MUTED):
        self._status_source_text, self._status_color = str(message), color
        translated = self._translate_status_message(message)
        self.status_label.setText(translated)
        # Long multi-instance errors may be clipped in the compact status area.
        # Keep the complete message available on hover for troubleshooting.
        self.status_label.setToolTip(translated)
        self.status_label.setStyleSheet(f"color:{color};")
        self.status_dot.setStyleSheet(f"color:{color};")

    def _start_worker(self, mode, work):
        if self._closing_requested:
            return False
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, self._t("正在运行"), self._t("请先停止当前任务。"))
            return False
        self.stop_event.clear()
        self.pause_event.set()
        self.mode = mode
        worker = Worker(work, self)
        self.worker = worker
        worker.status.connect(self._set_status)
        worker.progress.connect(self._update_route_progress)
        worker.record_location.connect(self._record_location)
        worker.save_manual_location.connect(self._save_manual_location)
        worker.record_route.connect(self._record_route)
        worker.failed.connect(lambda message: self._set_status(f"任务失败：{message}", RED))
        worker.finished.connect(lambda: setattr(self, "mode", None))
        worker.start()
        return True

    def _start_background(self, work, success, failure_title):
        if self._closing_requested:
            return None
        worker = Worker(work, self)
        self.background_workers.append(worker)
        worker.result.connect(success)
        def show_background_failure(message):
            if not self._closing_requested:
                QMessageBox.critical(self, self._t(failure_title), self._t(message))
        worker.failed.connect(show_background_failure)
        worker.finished.connect(lambda: self.background_workers.remove(worker) if worker in self.background_workers else None)
        worker.start()

    def _parse_gps_entry(self):
        text = self.maps_entry.text().strip()
        if not text:
            QMessageBox.warning(self, self._t("提示"), self._t("请粘贴 Google Maps 链接或输入 纬度,经度。"))
            return
        self._set_status("正在解析链接……", BLUE)
        def done(pair):
            lat, lon = pair
            self.lat_entry.setText(str(lat))
            self.lon_entry.setText(str(lon))
            self.lat_entry.setFocus()
            self._set_status(f"解析成功：{lat}, {lon}", GREEN)
        def failed(message):
            QMessageBox.critical(self, self._t("解析失败"), self._t(message))
            self._set_status("解析失败。", RED)
        worker = Worker(lambda _: resolve_maps_or_pair(text), self)
        self.background_workers.append(worker)
        worker.result.connect(done)
        worker.failed.connect(failed)
        worker.finished.connect(lambda: self.background_workers.remove(worker) if worker in self.background_workers else None)
        worker.start()

    def _find_location_history_match(self, lat, lon):
        """Return the newest history entry matching this coordinate pair."""
        for item in reversed(self.location_history):
            try:
                item_lat = float(item.get("lat"))
                item_lon = float(item.get("lon"))
            except (TypeError, ValueError, AttributeError):
                continue
            # Histories store the exact floats sent to MuMu. This small
            # tolerance also treats harmless floating-point representation
            # differences as the same location without matching nearby places.
            if abs(item_lat - lat) <= 1e-7 and abs(item_lon - lon) <= 1e-7:
                return item
        return None

    def _format_elapsed_since(self, timestamp):
        """Format an ISO history timestamp as a localized elapsed duration."""
        try:
            recorded_at = datetime.fromisoformat(str(timestamp))
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.astimezone()
            else:
                recorded_at = recorded_at.astimezone()
            seconds = max(0, int((datetime.now().astimezone() - recorded_at).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            return self._t("时间未知")

        if seconds < 10:
            return self._t("刚刚")
        if seconds < 60:
            amount, unit = seconds, "秒前"
        elif seconds < 3600:
            amount, unit = seconds // 60, "分钟前"
        elif seconds < 86400:
            amount, unit = seconds // 3600, "小时前"
        else:
            amount, unit = seconds // 86400, "天前"

        if self.language == "en":
            english_unit = {"秒前": "second", "分钟前": "minute", "小时前": "hour", "天前": "day"}[unit]
            return f"{amount} {english_unit}{'' if amount == 1 else 's'} ago"
        return f"{amount} {self._t(unit)}"

    def _confirm_repeated_location(self, lat, lon):
        """Ask before sending a coordinate that already exists in location history."""
        previous = self._find_location_history_match(lat, lon)
        if previous is None:
            return True

        timestamp = previous.get("time")
        try:
            recorded_at = datetime.fromisoformat(str(timestamp)).astimezone()
            time_text = recorded_at.strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OverflowError):
            time_text = self._t("时间未知")
        elapsed = self._format_elapsed_since(timestamp)
        message = self._t(
            "这个坐标已经在定位历史中出现过。\n上次记录时间：{time}\n距离上次定位：{elapsed}\n\n仍然要再次传送到这个位置吗？"
        ).format(time=time_text, elapsed=elapsed)
        return QMessageBox.question(
            self,
            self._t("重复定位确认"),
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) == QMessageBox.Yes

    def _set_manual_location(self):
        try:
            lat, lon = float(self.lat_entry.text()), float(self.lon_entry.text())
            if not valid_coordinates(lat, lon):
                raise ValueError("纬度范围 -90 至 90，经度范围 -180 至 180。")
            enabled = self.random_enabled.isChecked()
            duration, radius = (float(self.random_duration.text()), float(self.random_radius.text())) if enabled else (0, 10)
            if enabled and (not math.isfinite(duration) or not 1 <= duration <= 600):
                raise ValueError("随机走动持续时间必须在 1–600 秒之间。")
            if enabled and (not math.isfinite(radius) or not 1 <= radius <= 100):
                raise ValueError("随机走动半径必须在 1–100 米之间。")
        except ValueError as exc:
            QMessageBox.critical(self, self._t("输入错误"), self._t(str(exc)))
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, self._t("正在运行"), self._t("请先停止当前任务。"))
            return
        # If this coordinate was already successfully sent and recorded, ask
        # before sending it again. Choosing No leaves cache/history untouched.
        if not self._confirm_repeated_location(lat, lon):
            return
        # Cache the last manual coordinate only after MuMu confirms success.
        # A failed API call must not become the restored "last location".
        self._set_status("正在设置虚拟定位……", BLUE)
        def work(worker):
            try:
                if not self._api_location(lat, lon):
                    raise RuntimeError("MuMu API 返回失败。")
                worker.save_manual_location.emit(lat, lon)
                self.current_position = lat, lon
                worker.record_location.emit(lat, lon, "GPS定位")
                if not enabled:
                    worker.status.emit(f"定位成功\n纬度：{lat}\n经度：{lon}", GREEN)
                    return
                worker.status.emit(f"传送成功，开始附近随机走动 {duration:g} 秒……", GREEN)
                self._random_walk(worker, (lat, lon), duration, radius)
                if self.stop_event.is_set():
                    worker.status.emit("随机走动已停止，保留最后位置。", MUTED)
                else:
                    if not self._api_location(lat, lon):
                        raise RuntimeError("结束后返回起点失败。")
                    self.current_position = lat, lon
                    worker.status.emit("随机走动完成，已返回起点。", GREEN)
            except Exception as exc:
                worker.status.emit(f"定位失败：{exc}", RED)
        self._start_worker("teleport", work)

    def _random_walk(self, worker, center, duration, radius):
        deadline, current, target = time.monotonic() + duration, center, None
        segment_start, segment_duration, origin = time.monotonic(), 1.0, current
        while time.monotonic() < deadline and not self.stop_event.is_set():
            self._wait_if_paused()
            if self.stop_event.is_set():
                break
            now = time.monotonic()
            if target is None or now >= segment_start + segment_duration:
                origin = current
                distance, angle = random.uniform(max(1.0, radius * .15), radius), random.uniform(0, 2 * math.pi)
                target = destination_point(center, distance * math.cos(angle), distance * math.sin(angle))
                segment_duration, segment_start = max(1.0, haversine_m(origin, target) / 1.2), now
            position = interpolate_great_circle(origin, target, min(1, max(0, (now - segment_start) / segment_duration)))
            if haversine_m(center, position) <= radius:
                if not self._api_location(*position):
                    raise RuntimeError("随机走动时 MuMu API 返回失败。")
                current = position
                self.current_position = current
            remaining = max(0, deadline - time.monotonic())
            worker.status.emit(f"附近随机走动中 · 剩余 {remaining:.0f} 秒 · 距起点 {haversine_m(center, current):.1f}/{radius:g} 米", GREEN)
            if self.stop_event.wait(min(1, max(0, deadline - time.monotonic()))):
                break

    # ---- route --------------------------------------------------------
    @staticmethod
    def _parse_route_lines(lines):
        lines = [line for line in lines if line]
        if len(lines) < 2:
            raise ValueError("路线至少需要两个地点。")
        points = []
        for index, line in enumerate(lines, 1):
            try:
                points.append(resolve_maps_or_pair(line))
            except Exception as exc:
                raise ValueError(f"第 {index} 个地点无法解析：{exc}") from exc
        return points

    def _route_lines(self):
        return [row["entry"].text().strip() for row in self.route_rows]

    def _validate_route(self):
        lines = self._route_lines()
        self._set_status("正在解析路线……", BLUE)
        def done(points):
            distance = sum(haversine_m(points[i], points[i + 1]) for i in range(len(points) - 1))
            self._set_status(f"路线有效：{len(points)} 个点 · 总直线距离 {distance:.1f} 米", GREEN)
        self._start_background(lambda _: self._parse_route_lines(lines), done, "路线错误")

    def _start_route(self):
        try:
            speed, interval = float(self.route_speed.text()), float(self.route_interval.text())
            if not math.isfinite(speed) or not 0 < speed <= 100:
                raise ValueError("速度需大于 0 且不超过 100 km/h。")
            if not math.isfinite(interval) or not 1 <= interval <= 10:
                raise ValueError("更新间隔需在 1–10 秒之间。")
        except ValueError as exc:
            QMessageBox.critical(self, self._t("输入错误"), self._t(str(exc)))
            return
        if self._closing_requested:
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, self._t("正在运行"), self._t("请先停止当前任务。"))
            return
        if .001 <= self.route_progress_value <= 1:
            question = self._t("当前路线已完成 {percent:.1f}%。重新开始会从第一个地点重新走，确定继续吗？").format(percent=self.route_progress_value * 100)
            if QMessageBox.question(self, self._t("重新开始路线"), question) != QMessageBox.Yes:
                return
        self._save_route_draft()
        self._set_status("正在解析路线……", BLUE)
        lines = self._route_lines()
        self._start_background(lambda _: self._parse_route_lines(lines), lambda points: self._launch_route(points, speed, interval), "路线错误")

    def _launch_route(self, points, speed, interval):
        if self._closing_requested or (self.worker and self.worker.isRunning()):
            return
        self.progress.setValue(0)
        self.route_progress_value = 0
        self._update_route_progress_display(len(points))
        def work(worker):
            total, travelled = sum(haversine_m(points[i], points[i + 1]) for i in range(len(points) - 1)), 0.0
            try:
                if not self._api_location(*points[0]):
                    raise RuntimeError("MuMu 未接受路线起点。")
                self.current_position = points[0]
                worker.record_route.emit(points)
                worker.record_location.emit(points[0][0], points[0][1], "路线行走")
                worker.status.emit(f"路线行走开始 · {len(points)} 个路线点", GREEN)
                for index, (start, end) in enumerate(zip(points, points[1:])):
                    distance = haversine_m(start, end)
                    steps = max(1, math.ceil((distance / (speed / 3.6)) / interval))
                    for step in range(1, steps + 1):
                        if self.stop_event.is_set():
                            break
                        self._wait_if_paused()
                        if self.stop_event.is_set():
                            break
                        position = interpolate_great_circle(start, end, step / steps)
                        if not self._api_location(*position):
                            raise RuntimeError("MuMu API 返回失败，路线移动停止。")
                        self.current_position = position
                        if step == steps:
                            # Record only a route stop after its location update
                            # was accepted; never pre-log future/unreached stops.
                            worker.record_location.emit(end[0], end[1], "路线行走")
                        done = travelled + distance * step / steps
                        pct = 1 if total <= 0 else min(1, done / total)
                        worker.progress.emit(pct, done, total, index, len(points) - 1, False)
                        worker.status.emit(f"路线行走 · 第 {index + 1}/{len(points) - 1} 段 · {pct * 100:.1f}%\n当前位置：{position[0]:.7f}, {position[1]:.7f}", GREEN)
                        if self.stop_event.wait(interval):
                            break
                    if self.stop_event.is_set():
                        break
                    travelled += distance
                if self.stop_event.is_set():
                    worker.status.emit("路线行走已停止，保留最后位置。", MUTED)
                else:
                    worker.progress.emit(1, total, total, len(points) - 2, len(points) - 1, True)
                    worker.status.emit("路线行走已完成。", GREEN)
            except Exception as exc:
                worker.status.emit(f"路线行走失败：{exc}", RED)
        self._start_worker("route", work)

    def _update_route_progress(self, fraction, travelled, total, segment_index, segment_count, completed=False):
        self._route_progress_state = (fraction, travelled, total, segment_index, segment_count, completed)
        fraction = max(0, min(1, fraction))
        self.route_progress_value = fraction
        self.progress.setValue(round(fraction * 100))
        self.route_progress.setValue(round(fraction * 100))
        self.route_progress_text.setText(f"{fraction * 100:.1f}%")
        if completed:
            detail = f"Route completed · {total:.1f} m" if self.language == "en" else f"路線已完成 · {total:.1f} 公尺" if self.language == "zh-tw" else f"路线已完成 · {total:.1f} 米"
        elif self.language == "en":
            detail = f"Travelled {travelled:.1f} / {total:.1f} m · Segment {segment_index + 1}/{segment_count}"
        elif self.language == "zh-tw":
            detail = f"已行走 {travelled:.1f} / {total:.1f} 公尺 · 第 {segment_index + 1}/{segment_count} 段"
        else:
            detail = f"已走 {travelled:.1f} / {total:.1f} 米 · 第 {segment_index + 1}/{segment_count} 段"
        self.route_progress_detail.setText(detail)

    def _update_route_progress_display(self, stops=None):
        if not self.route_progress_value:
            self._route_progress_state = None
        self.route_progress.setValue(round(self.route_progress_value * 100))
        self.route_progress_text.setText(f"{self.route_progress_value * 100:.1f}%")
        if self.route_progress_value <= 0:
            if stops:
                text = f"Ready · {stops} stops" if self.language == "en" else f"準備開始 · 共 {stops} 個地點" if self.language == "zh-tw" else f"准备开始 · 共 {stops} 个地点"
            else:
                text = self._t("等待开始路线")
            self.route_progress_detail.setText(text)

    def _wait_if_paused(self):
        while not self.stop_event.is_set() and not self.pause_event.wait(.2):
            pass

    def _toggle_pause(self):
        if not self.worker or not self.worker.isRunning():
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self._set_status("已暂停 · 点击「暂停 / 继续」恢复。", ORANGE)
        else:
            self.pause_event.set()
            self._set_status("继续运行。", GREEN)

    def _confirm_stop_route(self):
        if self.worker and self.worker.isRunning() and QMessageBox.question(self, self._t("停止路线"), self._t("确定要停止当前路线行走吗？")) == QMessageBox.Yes:
            self._stop()

    def _stop(self):
        self.stop_event.set()
        self.pause_event.set()
        self._set_status("正在停止任务……", ORANGE)

    def _poll_workers_before_close(self):
        """Close only after every QThread has actually finished."""
        workers = []
        if self.worker is not None:
            workers.append(self.worker)
        workers.extend(self.background_workers)
        # Keep object identity unique when a worker is referenced in two places.
        unique_workers = {id(worker): worker for worker in workers}.values()
        if any(worker.isRunning() for worker in unique_workers):
            QTimer.singleShot(100, self._poll_workers_before_close)
            return
        self._close_ready = True
        self.close()

    def closeEvent(self, event):  # noqa: N802
        if self._close_ready:
            event.accept()
            return
        event.ignore()
        if self._closing_requested:
            return
        self._closing_requested = True
        self.stop_event.set()
        self.pause_event.set()
        try:
            self._save_route_draft()
        except OSError as exc:
            print(f"Could not save route draft: {exc}")
        self._set_status("正在停止任务并等待后台操作结束……", ORANGE)
        QTimer.singleShot(100, self._poll_workers_before_close)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if APP_ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setStyle("Fusion")
    window = GPSWindow()
    window.show()
    sys.exit(app.exec())
