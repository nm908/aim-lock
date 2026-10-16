@echo off
setlocal
cd /d "%~dp0"
title Build ADB Easy Installer
echo ==========================================
echo      BUILD ADB EASY INSTALLER
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo [LOI] Hay cai Python 3.10+ tu https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
if not exist "platform-tools\adb.exe" (
  echo [1/3] Dang tai Android Platform-Tools chinh thuc...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile 'platform-tools.zip'"
  if errorlevel 1 (
    echo [LOI] Khong tai duoc Platform-Tools. Kiem tra Internet.
    pause
    exit /b 1
  )
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force 'platform-tools.zip' '.'"
  if errorlevel 1 (
    echo [LOI] Khong giai nen duoc Platform-Tools.
    pause
    exit /b 1
  )
)
echo [2/3] Dang cai PyInstaller...
py -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo [LOI] Cai PyInstaller that bai.
  pause
  exit /b 1
)
echo [3/3] Dang build EXE...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name ADBEasyInstaller --add-data "platform-tools;platform-tools" adb_easy_installer.py
if errorlevel 1 (
  echo [LOI] Build that bai. Hay chup anh loi gui de kiem tra.
  pause
  exit /b 1
)
echo.
echo THANH CONG: "%~dp0dist\ADBEasyInstaller.exe"
pause
