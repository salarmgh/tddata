@echo off
setlocal

cd /d "%~dp0"

echo ==================================================
echo Starting Trading Data Dashboard
echo ==================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run: py -m venv .venv
    echo Then: .venv\Scripts\activate.bat ^&^& python -m pip install -r requirements.txt
    echo.
    echo Note: on Windows use "py" if "python" is not recognized.
    exit /b 1
)

if not exist "frontend\node_modules\" (
    echo [ERROR] Frontend dependencies not installed.
    echo Run: cd frontend ^&^& npm install
    exit /b 1
)

if not exist "database\telegram_data.db" (
    echo [WARN] database\telegram_data.db not found.
    echo Crawl data first with:
    echo   .venv\Scripts\python.exe -m crawler.web_crawler crawl-manual
    echo.
)

echo Starting Flask API on http://localhost:5000 ...
start "TalaData API" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m api.app"

timeout /t 3 /nobreak >nul

echo Starting React frontend on http://localhost:3000 ...
start "TalaData Frontend" /D "%~dp0frontend" cmd /k "npm start"

echo.
echo ==================================================
echo Dashboard is starting
echo ==================================================
echo.
echo Frontend: http://localhost:3000
echo API:      http://localhost:5000/api/health
echo.
echo Two new windows were opened for API and frontend.
echo Close those windows or press Ctrl+C in each to stop.
echo.
endlocal
