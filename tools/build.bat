@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ==========================================
echo  RealTimeMix Windows Build Script
echo ==========================================
echo.

:: Clean previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo [1/3] Building with PyInstaller...
pyinstaller ^
  --onedir --windowed --name RealTimeMix ^
  --add-data "browser_extension;browser_extension" ^
  --add-data "native_host;native_host" ^
  --add-data "demos;demos" ^
  --add-data "README.md;." ^
  --add-data "LICENSE;." ^
  --add-data "pyproject.toml;." ^
  --hidden-import PyQt6.sip ^
  --hidden-import PyQt6.QtCore ^
  --hidden-import PyQt6.QtGui ^
  --hidden-import PyQt6.QtWidgets ^
  --hidden-import cv2 ^
  --hidden-import numpy ^
  --hidden-import mss ^
  main.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Build complete.
echo.

echo [3/3] Output location:
echo   dist\RealTimeMix\RealTimeMix.exe
echo.

:: Show output size
for %%F in ("dist\RealTimeMix\RealTimeMix.exe") do (
    echo   Size: %%~zF bytes
)

echo.
echo ==========================================
echo  Done! Test the executable:
echo    dist\RealTimeMix\RealTimeMix.exe
echo ==========================================
pause
