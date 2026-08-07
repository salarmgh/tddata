"""
Parser for extracting structured data from Telegram trading messages
Extracts prices, transaction types, and other tags for time series analysis
"""

import re
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List


class TradingMessageParser:
    """Parser for trading channel messages"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Get project root directory (parent of api directory)
            from pathlib import Path
            PROJECT_ROOT = Path(__file__).parent.parent
            db_path = str(PROJECT_ROOT / "database" / "telegram_data.db")
            # Ensure database directory exists
            Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)
        self.db_path = db_path
        self._init_timeseries_table()

    def _init_timeseries_table(self):
        """Create time series table with tags"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create trades table for time series data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                channel_name TEXT,
                price REAL NOT NULL,
                transaction_type TEXT,
                transfer_method TEXT,
                delivery_time TEXT,
                description TEXT,
                weight TEXT,
                timestamp INTEGER,
                date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id),
                FOREIGN KEY (message_id) REFERENCES messages(message_id)
            )
        """)

        # Create indexes for fast filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_price ON trades(price)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_type ON trades(transaction_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_transfer ON trades(transfer_method)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date)")

        conn.commit()
        conn.close()

    def parse_message(self, text: str) -> Optional[Dict]:
        """
        Parse a trading message and extract structured data

        Args:
            text: Message text

        Returns:
            Dictionary with extracted data or None if not parseable
        """
        if not text:
            return None

        result = {}

        # Extract price (numbers with comma separator)
        price_match = re.search(r'([\d,]+)', text)
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            try:
                result['price'] = float(price_str)
            except ValueError:
                return None
        else:
            return None

        # Transaction type
        if 'خرید' in text or '🔵' in text:
            result['transaction_type'] = 'خرید'  # Buy
        elif 'فروش' in text or '🔴' in text:
            result['transaction_type'] = 'فروش'  # Sell
        elif 'معامله' in text or '✅' in text:
            result['transaction_type'] = 'معامله'  # Trade/Deal
        else:
            result['transaction_type'] = 'نامشخص'  # Unknown

        # Transfer method
        if 'باحواله' in text or 'با حواله' in text or 'با‌حواله' in text or '⏳' in text:
            result['transfer_method'] = 'باحواله'  # With transfer
        elif 'بدون حواله' in text or 'بدون‌حواله' in text or '❌' in text:
            result['transfer_method'] = 'بدون حواله'  # Without transfer
        else:
            result['transfer_method'] = 'نامشخص'  # Unknown

        # Delivery time
        if 'امروزی' in text or '🔆' in text:
            result['delivery_time'] = 'امروزی'  # Today
        elif 'فردا' in text or 'نقدی فردا' in text or 'نقدی‌فردا' in text:
            result['delivery_time'] = 'فردا'  # Tomorrow
        else:
            result['delivery_time'] = None

        # Extract description/weight
        desc_match = re.search(r'شرح:\s*(.+)', text)
        if desc_match:
            result['description'] = desc_match.group(1).strip()
        else:
            result['description'] = None

        # Extract weight if mentioned
        weight_match = re.search(r'(\d+)\s*(گرم|کیلو|میلی)', text)
        if weight_match:
            result['weight'] = weight_match.group(0)
        else:
            result['weight'] = None

        return result

    def parse_and_store_all(self):
        """Parse all unparsed messages and store in trades table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get messages that haven't been parsed yet
        cursor.execute("""
            SELECT m.message_id, m.channel_name, m.text, m.timestamp, m.date
            FROM messages m
            LEFT JOIN trades t ON m.message_id = t.message_id
            WHERE t.id IS NULL AND m.text IS NOT NULL
        """)

        messages = cursor.fetchall()
        parsed_count = 0
        skipped_count = 0

        for msg_id, channel, text, timestamp, date in messages:
            parsed = self.parse_message(text)

            if parsed:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO trades (
                            message_id, channel_name, price, transaction_type,
                            transfer_method, delivery_time, description,
                            weight, timestamp, date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        msg_id, channel, parsed['price'], parsed['transaction_type'],
                        parsed['transfer_method'], parsed['delivery_time'],
                        parsed['description'], parsed['weight'], timestamp, date
                    ))
                    if cursor.rowcount > 0:
                        parsed_count += 1
                except Exception as e:
                    print(f"Error inserting trade for message {msg_id}: {e}")
            else:
                skipped_count += 1

        conn.commit()
        conn.close()

        print(f"✓ Parsed {parsed_count} new trades")
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} unparseable messages")

        return parsed_count

    def get_trades(
        self,
        transaction_type: str = None,
        transfer_method: str = None,
        delivery_time: str = None,
        min_price: float = None,
        max_price: float = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = None
    ) -> List[Dict]:
        """
        Query trades with filters

        Args:
            transaction_type: Filter by type (خرید, فروش, معامله)
            transfer_method: Filter by method (باحواله, بدون حواله)
            delivery_time: Filter by delivery (امروزی, فردا)
            min_price: Minimum price
            max_price: Maximum price
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of results

        Returns:
            List of trade dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)

        if transfer_method:
            query += " AND transfer_method = ?"
            params.append(transfer_method)

        if delivery_time:
            query += " AND delivery_time = ?"
            params.append(delivery_time)

        if min_price is not None:
            query += " AND price >= ?"
            params.append(min_price)

        if max_price is not None:
            query += " AND price <= ?"
            params.append(max_price)

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        """Get statistics about trades"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        stats['total_trades'] = cursor.fetchone()[0]

        # By transaction type
        cursor.execute("""
            SELECT transaction_type, COUNT(*) as count
            FROM trades
            GROUP BY transaction_type
            ORDER BY count DESC
        """)
        stats['transaction_types'] = [{"type": t, "count": c} for t, c in cursor.fetchall()]

        # By transfer method
        cursor.execute("""
            SELECT transfer_method, COUNT(*) as count
            FROM trades
            GROUP BY transfer_method
            ORDER BY count DESC
        """)
        stats['transfer_methods'] = [{"method": m, "count": c} for m, c in cursor.fetchall()]

        # By delivery time
        cursor.execute("""
            SELECT delivery_time, COUNT(*) as count
            FROM trades
            WHERE delivery_time IS NOT NULL
            GROUP BY delivery_time
            ORDER BY count DESC
        """)
        stats['delivery_times'] = [{"time": t, "count": c} for t, c in cursor.fetchall()]

        conn.close()
        return stats


def main():
    """CLI interface for parser"""
    import sys
    from pathlib import Path

    # Get project root directory (parent of api directory)
    PROJECT_ROOT = Path(__file__).parent.parent
    DB_PATH = str(PROJECT_ROOT / "database" / "telegram_data.db")
    # Ensure database directory exists
    Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)

    parser = TradingMessageParser(DB_PATH)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m api.parser parse      - Parse all unparsed messages")
        print("  python -m api.parser stats      - Show trade statistics")
        print("  python -m api.parser query      - Query trades with filters")
        return

    command = sys.argv[1].lower()

    if command == "parse":
        print("Parsing messages...")
        parser.parse_and_store_all()

    elif command == "stats":
        stats = parser.get_stats()
        print("\n" + "=" * 60)
        print("Trade Statistics")
        print("=" * 60)
        print(f"Total trades: {stats['total_trades']}")

        print("\nBy transaction type:")
        for item in stats['transaction_types']:
            print(f"  {item['type']}: {item['count']}")

        print("\nBy transfer method:")
        for item in stats['transfer_methods']:
            print(f"  {item['method']}: {item['count']}")

        if stats['delivery_times']:
            print("\nBy delivery time:")
            for item in stats['delivery_times']:
                print(f"  {item['time']}: {item['count']}")
        print("=" * 60)

    elif command == "query":
        # Example query - customize as needed
        trades = parser.get_trades(
            transaction_type="خرید",
            limit=10
        )
        print(f"\nFound {len(trades)} trades:")
        for trade in trades:
            print(f"  {trade['price']:,.0f} - {trade['transaction_type']} - {trade['transfer_method']} - {trade['date']}")


if __name__ == "__main__":
    main()

