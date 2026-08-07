# Migration Guide

If you have existing data from the old structure, follow these steps to migrate:

## Database Migration

If you have an existing `telegram_data.db` in the project root:

```bash
# Create database directory if it doesn't exist
mkdir -p database

# Move the database file
mv telegram_data.db database/telegram_data.db
```

## Session Data Migration

If you have an existing `telegram_web_session` directory in the project root:

```bash
# Move session directory to crawler
mv telegram_web_session crawler/telegram_web_session
```

## Verify Migration

After migration, verify the new structure:

```bash
# Check database location
ls -lh database/telegram_data.db

# Check session location
ls -d crawler/telegram_web_session
```

## New Structure

```
taladata/
├── database/
│   └── telegram_data.db          # Shared SQLite database
├── crawler/
│   └── telegram_web_session/      # Browser session (crawler only)
├── api/
│   ├── app.py                     # Uses database/telegram_data.db
│   └── parser.py                  # Uses database/telegram_data.db
└── ...
```

Both the API and crawler now use the same database file at `database/telegram_data.db`.

