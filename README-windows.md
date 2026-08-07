# Trading Data Dashboard — Windows Setup

How to install and run the Python API and React frontend on Windows.

## Prerequisites

Install these first:

1. **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
  - During setup, check **Add python.exe to PATH**
2. **Node.js 18+ (LTS)** — [nodejs.org](https://nodejs.org/)
  - Includes `npm`
3. **Git** — [git-scm.com](https://git-scm.com/download/win)

Verify in **Command Prompt** or **PowerShell**:

```bat
py --version
node --version
npm --version
```

On Windows, prefer `py` (Python Launcher). If `python` says it is not installed but Python is, use `py` instead — that is normal.

## 1. Get the project

```bat
git clone https://github.com/salarmgh/tddata.git
cd tddata
```

## 2. Python API (backend)

Open a terminal in the project root (`tddata`).

### Create and activate a virtual environment

**Command Prompt:**

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

**PowerShell:**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

After activation, `python` and `pip` work inside the venv.

### Install dependencies

```bat
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### (Optional) Crawl and parse data

Only needed if you do not already have `database\telegram_data.db` with trades:

```bat
python -m crawler.web_crawler login
python -m crawler.web_crawler crawl-manual --hours 1
python -m api.parser parse
```

## 3. Run both (recommended)

After setup is done once, double-click `start.bat` or run:

```bat
start.bat
```

This opens two windows:

- API → http://localhost:5000
- Frontend → http://localhost:3000

`start.bat` uses `.venv\Scripts\python.exe` directly, so it does not need `python` on PATH.

## 4. Run separately (optional)

**API** (venv activated):

```bat
python -m api.app
```

Or without activating:

```bat
.venv\Scripts\python.exe -m api.app
```

**Frontend** (second terminal):

```bat
cd frontend
npm install
npm start
```

## Quick reference

| Service  | Command (after setup)                    | URL                   |
| -------- | ---------------------------------------- | --------------------- |
| Both     | `start.bat`                              | ports 5000 and 3000   |
| API      | `.venv\Scripts\python.exe -m api.app`    | http://localhost:5000 |
| Frontend | `cd frontend` → `npm start`              | http://localhost:3000 |

## Stop services

Close the API/frontend windows, or press `Ctrl+C` in each.

## Troubleshooting

### `python` is not installed / not found (but Python is installed)

Windows often does not put `python` on PATH. Use the launcher:

```bat
py --version
py -m venv .venv
```

If `py` also fails:

1. Reinstall from [python.org/downloads](https://www.python.org/downloads/)
2. Check **Add python.exe to PATH** on the first installer screen
3. Close and reopen Command Prompt
4. Avoid the Microsoft Store “Install Python” stub if you already installed from python.org

You can also create the venv with a full path, for example:

```bat
"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
```

(Adjust the version folder to match your install.)

`Activate.ps1` **is disabled**  
Use Command Prompt with `.venv\Scripts\activate.bat`, or set the PowerShell execution policy as shown above.

**Frontend cannot reach API**  
Confirm the API terminal is still running and open [http://localhost:5000/api/health](http://localhost:5000/api/health) in a browser.

**Empty dashboard**  
Crawl and parse data first (see optional steps above), then restart the API.

**Port already in use**  
Close whatever is using port `5000` (API) or `3000` (frontend), or reboot and try again.

## Related docs

- Main README: `README.md`
- API details: `API_DOCS.md`
- Filters: `FILTERS.md`

