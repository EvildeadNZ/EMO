@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0EMP Preview Installer.ps1"
if errorlevel 1 (
  echo.
  echo EMP installer stopped with an error.
  pause
)
endlocal
