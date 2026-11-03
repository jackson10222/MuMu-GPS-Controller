@echo off
setlocal
cd /d "%~dp0"

echo Installing project dependencies...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto :failed

python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :failed

echo.
echo Building single-file EXE...
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name "MuMu-GPS-Controller" ^
  --icon "assets\gps-location-icon.ico" ^
  --add-data "assets\gps-location-icon.png;assets" ^
  --collect-all mumu ^
  gps_controller_qt.py
if errorlevel 1 goto :failed

echo.
echo Single-file build complete:
echo dist\MuMu-GPS-Controller.exe
pause
exit /b 0

:failed
echo.
echo Build failed. Review the error messages above.
pause
exit /b 1