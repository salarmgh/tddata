@echo off
setlocal

cd /d "%~dp0"

echo ==================================================
echo Stopping Trading Data Dashboard
echo ==================================================
echo.

REM Close the windows started by start.bat
taskkill /FI "WINDOWTITLE eq TalaData API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq TalaData Frontend*" /T /F >nul 2>&1

REM Also free ports in case processes were left running
call :kill_port 5000
call :kill_port 3000

echo.
echo [OK] Stopped API (port 5000) and frontend (port 3000).
echo.
endlocal
exit /b 0

:kill_port
set "PORT=%~1"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    if not "%%p"=="0" (
        echo Stopping PID %%p on port %PORT% ...
        taskkill /F /PID %%p >nul 2>&1
    )
)
exit /b 0
