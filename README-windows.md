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
python --version
node --version
npm --version
```

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
python -m venv .venv
.venv\Scripts\activate.bat
```

**PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

### Install dependencies

```bat
pip install -r requirements.txt
playwright install chromium
```

### (Optional) Crawl and parse data

Only needed if you do not already have `database\telegram_data.db` with trades:

```bat
python -m crawler.web_crawler login
python -m crawler.web_crawler crawl-manual --hours 1
python -m api.parser parse
```

### Start the API

Keep the venv activated, then:

```bat
python -m api.app
```

API: [http://localhost:5000](http://localhost:5000)  
Health check: [http://localhost:5000/api/health](http://localhost:5000/api/health)

Leave this terminal open.

## 3. React frontend

Open a **second** terminal in the project root.

```bat
cd frontend
npm install
npm start
```

Frontend: [http://localhost:3000](http://localhost:3000)

It talks to the API at `http://localhost:5000/api`. Keep the API running in the first terminal.

## Quick reference

| Service   | Command (after setup)        | URL                      |
|-----------|------------------------------|--------------------------|
| API       | `python -m api.app`          | http://localhost:5000    |
| Frontend  | `cd frontend` → `npm start`  | http://localhost:3000    |

## Stop services

In each terminal, press `Ctrl+C`.

## Troubleshooting

**`python` not found**  
Reinstall Python and enable **Add to PATH**, or try `py -m venv .venv` instead of `python -m venv .venv`.

**`Activate.ps1` is disabled**  
Use Command Prompt with `.venv\Scripts\activate.bat`, or set the PowerShell execution policy as shown above.

**Frontend cannot reach API**  
Confirm the API terminal is still running and open http://localhost:5000/api/health in a browser.

**Empty dashboard**  
Crawl and parse data first (see optional steps above), then restart the API.

**Port already in use**  
Close whatever is using port `5000` (API) or `3000` (frontend), or reboot and try again.

## Related docs

- Main README: `README.md`
- API details: `API_DOCS.md`
- Filters: `FILTERS.md`
