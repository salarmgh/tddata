# Filterable Tags and Time Series Data

## Database Schema

### `trades` Table (Time Series Data)

Structured data extracted from trading messages with the following fields:

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `id` | INTEGER | Primary key | 1, 2, 3... |
| `message_id` | TEXT | Link to original message | "4294967341" |
| `channel_name` | TEXT | Channel name | "Secret ta daste" |
| `price` | REAL | Trading price | 70650.0, 70780.0 |
| `transaction_type` | TEXT | Type of transaction | See below |
| `transfer_method` | TEXT | Transfer method | See below |
| `delivery_time` | TEXT | Delivery timing | See below |
| `description` | TEXT | Additional description | "۱۰۰گرم" |
| `weight` | TEXT | Weight if mentioned | "100 گرم" |
| `timestamp` | INTEGER | Unix timestamp | 1767688389 |
| `date` | TEXT | ISO date | "2026-01-06T12:03:09" |

## Filterable Tags

### 1. Transaction Type (`transaction_type`)

Type of trading transaction:

- **`خرید`** - Buy (🔵 blue circle emoji)
- **`فروش`** - Sell (🔴 red circle emoji)
- **`معامله`** - Trade/Deal (✅ checkmark emoji)
- **`نامشخص`** - Unknown/Other

### 2. Transfer Method (`transfer_method`)

How the transaction is transferred:

- **`باحواله`** - With transfer/remittance (⏳ hourglass emoji)
- **`بدون حواله`** - Without transfer (❌ cross mark emoji)
- **`نامشخص`** - Unknown/Other

### 3. Delivery Time (`delivery_time`)

When the transaction will be delivered:

- **`امروزی`** - Today (🔆 sun emoji)
- **`فردا`** - Tomorrow / Next day cash
- **`NULL`** - Not specified

### 4. Price (`price`)

Numeric value for price filtering:

- Use `min_price` and `max_price` for range queries
- Example: 70,000 to 71,000

### 5. Date/Time (`date`, `timestamp`)

Temporal filtering:

- `date` - ISO format date string
- `timestamp` - Unix timestamp for time series analysis
- Use `start_date` and `end_date` for range queries

## Usage Examples

### Parse Messages

```bash
# Parse all unparsed messages and store in trades table
python parser.py parse
```

### View Statistics

```bash
# Show overview of all trades
python parser.py stats
```

Output:
```
==============================================================
Trade Statistics
==============================================================
Total trades: 150

By transaction type:
  خرید: 65
  فروش: 60
  معامله: 25

By transfer method:
  باحواله: 130
  بدون حواله: 20

By delivery time:
  امروزی: 30
  فردا: 15

Price range:
  Min: 70,000
  Max: 71,500
  Avg: 70,625.50
==============================================================
```

### Query with Filters (Python)

```python
from parser import TradingMessageParser

parser = TradingMessageParser()

# Get all buy orders with transfer
buys_with_transfer = parser.get_trades(
    transaction_type="خرید",
    transfer_method="باحواله",
    limit=100
)

# Get sells above 70,500
expensive_sells = parser.get_trades(
    transaction_type="فروش",
    min_price=70500,
    limit=50
)

# Get today's deliveries
today_deliveries = parser.get_trades(
    delivery_time="امروزی"
)

# Get trades in date range
recent_trades = parser.get_trades(
    start_date="2026-01-01",
    end_date="2026-01-06",
    limit=100
)

# Combined filters
specific_trades = parser.get_trades(
    transaction_type="خرید",
    transfer_method="بدون حواله",
    min_price=70000,
    max_price=71000,
    delivery_time="امروزی"
)
```

### SQL Queries

```sql
-- Get all buy orders
SELECT * FROM trades WHERE transaction_type = 'خرید';

-- Get trades without transfer
SELECT * FROM trades WHERE transfer_method = 'بدون حواله';

-- Get trades by price range
SELECT * FROM trades WHERE price BETWEEN 70000 AND 71000;

-- Get today's deliveries
SELECT * FROM trades WHERE delivery_time = 'امروزی';

-- Average price by transaction type
SELECT transaction_type, AVG(price) as avg_price, COUNT(*) as count
FROM trades
GROUP BY transaction_type;

-- Price trend over time
SELECT DATE(date) as trade_date, AVG(price) as avg_price, COUNT(*) as count
FROM trades
GROUP BY DATE(date)
ORDER BY trade_date DESC;

-- Trades by hour
SELECT strftime('%H', date) as hour, COUNT(*) as count
FROM trades
GROUP BY hour
ORDER BY hour;

-- Most common combinations
SELECT transaction_type, transfer_method, COUNT(*) as count
FROM trades
GROUP BY transaction_type, transfer_method
ORDER BY count DESC;
```

## Complete Filter Combinations

All possible filter parameters for `get_trades()`:

```python
parser.get_trades(
    transaction_type="خرید|فروش|معامله",  # Transaction type
    transfer_method="باحواله|بدون حواله",  # Transfer method
    delivery_time="امروزی|فردا",          # Delivery timing
    min_price=70000,                       # Minimum price
    max_price=71000,                       # Maximum price
    start_date="2026-01-01",               # Start date
    end_date="2026-01-06",                 # End date
    limit=100                              # Max results
)
```

## Workflow

1. **Crawl messages** from Telegram
   ```bash
   python web_crawler.py crawl-manual --days 7
   ```

2. **Parse messages** into structured data
   ```bash
   python parser.py parse
   ```

3. **View statistics**
   ```bash
   python parser.py stats
   ```

4. **Query and analyze** using Python or SQL
   ```python
   from parser import TradingMessageParser
   parser = TradingMessageParser()
   trades = parser.get_trades(transaction_type="خرید")
   ```

