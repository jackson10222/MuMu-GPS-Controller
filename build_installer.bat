@echo off
setlocal
cd /d "%~dp0"

if not exist "Languages\ChineseSimplified.isl" (
    echo Missing bundled language file: Languages\ChineseSimplified.isl
    goto :failed
)
if not exist "Languages\ChineseTraditional.isl" (
    echo Missing bundled language file: Languages\ChineseTraditional.isl
    goto :failed
)

echo Installing project dependencies...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :failed

python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :failed

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    where ISCC.exe >nul 2>nul
    if not errorlevel 1 set "ISCC=ISCC.exe"
)

if not defined ISCC (
    echo.
    echo Inno Setup 6 compiler was not found.
    echo Install Inno Setup 6, then run this script again.
    echo https://jrsoftware.org/isinfo.php
    goto :failed
)

echo.
echo Building the application folder for the installer...
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name "MuMu-GPS-Controller-Portable" ^
  --icon "assets\gps-location-icon.ico" ^
  --add-data "assets\gps-location-icon.png;assets" ^
  --collect-all mumu ^
  gps_controller_qt.py
if errorlevel 1 goto :failed

if not exist "dist\MuMu-GPS-Controller-Portable\MuMu-GPS-Controller-Portable.exe" (
    echo.
    echo The PyInstaller output executable was not found.
    goto :failed
)

echo.
echo Compiling the Windows installer...
"%ISCC%" "MuMu-GPS-Controller-Setup.iss"
if errorlevel 1 goto :failed

if not exist "dist\installer\MuMu-GPS-Controller-Setup.exe" (
    echo.
    echo The setup executable was not created.
    goto :failed
)

echo.
echo Installer created successfully:
echo dist\installer\MuMu-GPS-Controller-Setup.exe
pause
exit /b 0

:failed
echo.
echo Build failed. Review the error messages above.
pause
exit /b 1