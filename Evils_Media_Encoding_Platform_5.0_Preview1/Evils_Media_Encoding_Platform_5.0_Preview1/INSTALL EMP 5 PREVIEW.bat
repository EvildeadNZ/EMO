@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0EMP Preview Installer.ps1"
endlocal
pause