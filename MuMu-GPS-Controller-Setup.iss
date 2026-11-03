#define MyAppName "MuMu GPS Controller"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MuMu GPS Controller"
#define MyAppExeName "MuMu-GPS-Controller-Portable.exe"

[Setup]
; Keep the same AppId for future upgrades of this application.
AppId={{8E2A71F4-5C9B-4D31-9A67-2B7E6F0A4C91}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MuMu GPS Controller
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\gps-location-icon.ico
OutputDir=dist\installer
OutputBaseFilename=MuMu-GPS-Controller-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableDirPage=no
SetupLogging=yes
Uninstallable=yes
VersionInfoVersion=1.0.0.0
VersionInfoProductName={#MyAppName}
VersionInfoDescription=MuMu Android emulator GPS controller

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl,Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Default.isl,Languages\ChineseTraditional.isl"

[CustomMessages]
english.AdditionalShortcuts=Additional shortcuts:
chinesesimplified.AdditionalShortcuts=附加快捷方式：
chinesetraditional.AdditionalShortcuts=附加捷徑：
english.CreateDesktopIcon=Create a desktop shortcut
chinesesimplified.CreateDesktopIcon=创建桌面快捷方式
chinesetraditional.CreateDesktopIcon=建立桌面捷徑
english.LaunchAfterSetup=Launch MuMu GPS Controller
chinesesimplified.LaunchAfterSetup=安装完成后启动 MuMu GPS Controller
chinesetraditional.LaunchAfterSetup=安裝完成後啟動 MuMu GPS Controller

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalShortcuts}"; Flags: checkedonce

[Files]
Source: "dist\MuMu-GPS-Controller-Portable\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchAfterSetup}"; Flags: nowait postinstall skipifsilent

; Deliberately do not add UninstallDelete rules for %LOCALAPPDATA%.
; User settings, bookmarks, route history, and emulator configuration must survive uninstall.
