@echo off
setlocal

cd /d "%~dp0"

echo ==================================================
echo Clean Trading Data (start fresh)
echo ==================================================
echo.
echo This will DELETE:
echo   database\telegram_data.db
echo.
echo Crawl and parse again afterward to reload data.
echo.

if not exist "database\telegram_data.db" (
    echo [INFO] No database found. Already clean.
    echo.
    goto :done
)

set /p CONFIRM="Type YES to delete the database: "
if /I not "%CONFIRM%"=="YES" (
    echo.
    echo Cancelled. Nothing deleted.
    echo.
    goto :done
)

del /f /q "database\telegram_data.db"
if exist "database\telegram_data.db" (
    echo.
    echo [ERROR] Could not delete database\telegram_data.db
    echo Stop the API window first, then run clean.bat again.
    echo.
    exit /b 1
)

echo.
echo [OK] database\telegram_data.db deleted.
echo.

:done
echo Next steps (optional):
echo   1. Crawl:  .venv\Scripts\python.exe -m crawler.web_crawler crawl-manual --hours 1
echo   2. Parse:  .venv\Scripts\python.exe -m api.parser parse
echo   3. Start:  start.bat
echo.
endlocal
