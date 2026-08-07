# Trading Data Dashboard

A complete system for crawling Telegram trading channels and visualizing the data.

## Project Structure

```
taladata/
├── api/                    # Flask REST API
│   ├── requirements.txt    # API dependencies
│   ├── app.py             # Flask application
│   └── parser.py          # Message parser
├── crawler/                # Telegram web crawler
│   ├── requirements.txt    # Crawler dependencies
│   ├── web_crawler.py     # Playwright-based crawler
│   └── telegram_web_session/  # Browser session data
├── database/               # SQLite database
│   └── telegram_data.db   # Shared database
├── frontend/               # React TypeScript dashboard
└── requirements.txt        # All dependencies (root)
```

## Setup

### 1. Install Python Dependencies

**Option A: Install all dependencies (recommended)**
```bash
pip install -r requirements.txt
```

**Option B: Install separately**
```bash
# Install crawler dependencies
pip install -r crawler/requirements.txt
playwright install chromium

# Install API dependencies
pip install -r api/requirements.txt
```

### 2. Setup Crawler

```bash
# Login to Telegram Web (first time only)
python -m crawler.web_crawler login

# Crawl a channel
python -m crawler.web_crawler crawl-manual --hours 1
```

### 3. Parse Messages

```bash
# Parse crawled messages into trades table
python -m api.parser parse

# View statistics
python -m api.parser stats
```

### 4. Start API Server

```bash
python -m api.app
```

API will be available at: `http://localhost:5000`

### 5. Start Frontend

```bash
cd frontend
npm install
npm start
```

Frontend will be available at: `http://localhost:3000`

## Quick Start

Use the provided start script:

```bash
./start.sh
```

This will start both the API and frontend.

## Usage

### Crawler Commands

```bash
# Login (first time)
python -m crawler.web_crawler login

# Crawl public channel by username
python -m crawler.web_crawler crawl <channel_username>

# Crawl private channel manually
python -m crawler.web_crawler crawl-manual

# Crawl with scrolling (last 1 hour, or last 7 days)
python -m crawler.web_crawler crawl-manual --hours 1
python -m crawler.web_crawler crawl-manual --days 7

# View database statistics
python -m crawler.web_crawler stats
```

### Parser Commands

```bash
# Parse all unparsed messages
python -m api.parser parse

# View trade statistics
python -m api.parser stats

# Query trades (example)
python -m api.parser query
```

### API Endpoints

See `API_DOCS.md` for complete API documentation.

Main endpoints:
- `GET /api/health` - Health check
- `GET /api/trades` - Get trades with filters
- `GET /api/stats` - Get statistics
- `GET /api/chart/*` - Chart data endpoints

## Dependencies

### Crawler
- `playwright` - Browser automation

### API
- `flask` - Web framework
- `flask-cors` - CORS support

### Frontend
- React with TypeScript
- Chart.js / react-chartjs-2
- Axios

## Database

The SQLite database is stored at `database/telegram_data.db` and is shared between:
- **Crawler**: Writes messages to `messages` table
- **API**: Reads from `trades` table (parsed by parser)

## Development

### Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Project Organization

- **Crawler**: Independent module, only needs `playwright`
- **API**: Independent module, only needs `flask` and `flask-cors`
- **Database**: Shared SQLite file in `database/` directory
- **Session**: Browser session stored in `crawler/telegram_web_session/`

## License

MIT

