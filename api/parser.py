"""
Parser for extracting structured data from Telegram trading messages
Extracts prices, weights, transaction types, and other tags for time series analysis
"""

import re
import sqlite3
from typing import Optional, Dict, List

# Persian / Arabic-Indic digits -> ASCII
_DIGIT_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

# Examples: 1کیلو, 3 کیلو, ۱۰۰گرم, 500 میلی
_WEIGHT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(کیلوگرم|کيلوگرم|کیلو|کيلو|گرم|میلی‌?گرم|میلی|ميلي)",
    re.UNICODE,
)


def normalize_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def weight_to_kg(value: float, unit: str) -> float:
    unit = unit.replace("‌", "").replace(" ", "")
    if unit.startswith("کیلو") or unit.startswith("كیلو") or unit.startswith("کيلو"):
        return value
    if unit.startswith("میلی") or unit.startswith("ميلي"):
        return value / 1_000_000
    if unit.startswith("گرم"):
        return value / 1000
    return value


class TradingMessageParser:
    """Parser for trading channel messages"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            from pathlib import Path
            PROJECT_ROOT = Path(__file__).parent.parent
            db_path = str(PROJECT_ROOT / "database" / "telegram_data.db")
            Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)
        self.db_path = db_path
        self._init_timeseries_table()

    def _init_timeseries_table(self):
        """Create time series table with tags"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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
                weight_kg REAL,
                timestamp INTEGER,
                date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id),
                FOREIGN KEY (message_id) REFERENCES messages(message_id)
            )
        """)

        # Migrate older DBs that lack weight_kg
        cursor.execute("PRAGMA table_info(trades)")
        columns = {row[1] for row in cursor.fetchall()}
        if "weight_kg" not in columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN weight_kg REAL")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_price ON trades(price)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_type ON trades(transaction_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_transfer ON trades(transfer_method)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_weight ON trades(weight)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_weight_kg ON trades(weight_kg)")

        conn.commit()
        conn.close()

    def parse_message(self, text: str) -> Optional[Dict]:
        """
        Parse a trading message and extract structured data.

        Example inputs:
          82,900🔵خرید⏳باحواله 1کیلو
          82,950🔴فروش⏳باحواله 3کیلو
        """
        if not text:
            return None

        text = normalize_digits(text)
        result = {}

        # Price is the leading number (may include thousands separators)
        price_match = re.search(r"([\d,]+)", text)
        if price_match:
            price_str = price_match.group(1).replace(",", "")
            try:
                result["price"] = float(price_str)
            except ValueError:
                return None
        else:
            return None

        if "خرید" in text or "🔵" in text:
            result["transaction_type"] = "خرید"
        elif "فروش" in text or "🔴" in text:
            result["transaction_type"] = "فروش"
        elif "معامله" in text or "✅" in text:
            result["transaction_type"] = "معامله"
        else:
            result["transaction_type"] = "نامشخص"

        if "باحواله" in text or "با حواله" in text or "با‌حواله" in text or "⏳" in text:
            result["transfer_method"] = "باحواله"
        elif "بدون حواله" in text or "بدون‌حواله" in text or "❌" in text:
            result["transfer_method"] = "بدون حواله"
        else:
            result["transfer_method"] = "نامشخص"

        if "امروزی" in text or "🔆" in text:
            result["delivery_time"] = "امروزی"
        elif "فردا" in text or "نقدی فردا" in text or "نقدی‌فردا" in text:
            result["delivery_time"] = "فردا"
        else:
            result["delivery_time"] = None

        desc_match = re.search(r"شرح:\s*(.+)", text)
        result["description"] = desc_match.group(1).strip() if desc_match else None

        weight_match = _WEIGHT_RE.search(text)
        if weight_match:
            raw_value = weight_match.group(1).replace(",", ".")
            unit = weight_match.group(2)
            value = float(raw_value)
            unit_clean = unit.replace("‌", "").replace(" ", "")
            if unit_clean.startswith(("کیلو", "كیلو", "کيلو")):
                display_unit = "کیلو"
            elif unit_clean.startswith("گرم"):
                display_unit = "گرم"
            else:
                display_unit = "میلی"
            display_value = int(value) if value == int(value) else value
            result["weight"] = f"{display_value}{display_unit}"
            result["weight_kg"] = weight_to_kg(value, unit_clean)
        else:
            result["weight"] = None
            result["weight_kg"] = None

        return result

    def _upsert_trade(self, cursor, msg_id, channel, parsed, timestamp, date):
        cursor.execute("""
            INSERT INTO trades (
                message_id, channel_name, price, transaction_type,
                transfer_method, delivery_time, description,
                weight, weight_kg, timestamp, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                channel_name=excluded.channel_name,
                price=excluded.price,
                transaction_type=excluded.transaction_type,
                transfer_method=excluded.transfer_method,
                delivery_time=excluded.delivery_time,
                description=excluded.description,
                weight=excluded.weight,
                weight_kg=excluded.weight_kg,
                timestamp=excluded.timestamp,
                date=excluded.date
        """, (
            msg_id, channel, parsed["price"], parsed["transaction_type"],
            parsed["transfer_method"], parsed["delivery_time"],
            parsed["description"], parsed["weight"], parsed["weight_kg"],
            timestamp, date,
        ))

    def parse_and_store_all(self, reparse: bool = False):
        """Parse messages into trades. If reparse=True, refresh existing rows too."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if reparse:
            cursor.execute("""
                SELECT m.message_id, m.channel_name, m.text, m.timestamp, m.date
                FROM messages m
                WHERE m.text IS NOT NULL
            """)
        else:
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
                    self._upsert_trade(cursor, msg_id, channel, parsed, timestamp, date)
                    parsed_count += 1
                except Exception as e:
                    print(f"Error inserting trade for message {msg_id}: {e}")
            else:
                skipped_count += 1

        conn.commit()
        conn.close()

        action = "Reparsed" if reparse else "Parsed"
        print(f"✓ {action} {parsed_count} trades")
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} unparseable messages")

        return parsed_count

    def get_trades(
        self,
        transaction_type: str = None,
        transfer_method: str = None,
        delivery_time: str = None,
        weight: str = None,
        min_weight_kg: float = None,
        max_weight_kg: float = None,
        min_price: float = None,
        max_price: float = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = None,
    ) -> List[Dict]:
        """Query trades with filters"""
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

        if weight:
            query += " AND weight = ?"
            params.append(weight)

        if min_weight_kg is not None:
            query += " AND weight_kg >= ?"
            params.append(min_weight_kg)

        if max_weight_kg is not None:
            query += " AND weight_kg <= ?"
            params.append(max_weight_kg)

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

        cursor.execute("SELECT COUNT(*) FROM trades")
        stats["total_trades"] = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(weight_kg), 0) FROM trades")
        stats["total_weight_kg"] = round(cursor.fetchone()[0] or 0, 4)

        cursor.execute("""
            SELECT transaction_type, COUNT(*) as count
            FROM trades
            GROUP BY transaction_type
            ORDER BY count DESC
        """)
        stats["transaction_types"] = [{"type": t, "count": c} for t, c in cursor.fetchall()]

        cursor.execute("""
            SELECT transfer_method, COUNT(*) as count
            FROM trades
            GROUP BY transfer_method
            ORDER BY count DESC
        """)
        stats["transfer_methods"] = [{"method": m, "count": c} for m, c in cursor.fetchall()]

        cursor.execute("""
            SELECT delivery_time, COUNT(*) as count
            FROM trades
            WHERE delivery_time IS NOT NULL
            GROUP BY delivery_time
            ORDER BY count DESC
        """)
        stats["delivery_times"] = [{"time": t, "count": c} for t, c in cursor.fetchall()]

        cursor.execute("""
            SELECT weight, COUNT(*) as count, COALESCE(SUM(weight_kg), 0) as total_kg
            FROM trades
            WHERE weight IS NOT NULL
            GROUP BY weight
            ORDER BY count DESC
            LIMIT 20
        """)
        stats["weights"] = [
            {"weight": w, "count": c, "total_kg": round(kg, 4)}
            for w, c, kg in cursor.fetchall()
        ]

        conn.close()
        return stats


def main():
    """CLI interface for parser"""
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent
    DB_PATH = str(PROJECT_ROOT / "database" / "telegram_data.db")
    Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)

    parser = TradingMessageParser(DB_PATH)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m api.parser parse      - Parse all unparsed messages")
        print("  python -m api.parser reparse    - Re-parse all messages (refresh weights)")
        print("  python -m api.parser stats      - Show trade statistics")
        print("  python -m api.parser query      - Query trades with filters")
        return

    command = sys.argv[1].lower()

    if command == "parse":
        print("Parsing messages...")
        parser.parse_and_store_all()

    elif command == "reparse":
        print("Re-parsing all messages...")
        parser.parse_and_store_all(reparse=True)

    elif command == "stats":
        stats = parser.get_stats()
        print("\n" + "=" * 60)
        print("Trade Statistics")
        print("=" * 60)
        print(f"Total trades: {stats['total_trades']}")
        print(f"Total weight: {stats['total_weight_kg']} kg")

        print("\nBy transaction type:")
        for item in stats["transaction_types"]:
            print(f"  {item['type']}: {item['count']}")

        print("\nBy transfer method:")
        for item in stats["transfer_methods"]:
            print(f"  {item['method']}: {item['count']}")

        if stats["delivery_times"]:
            print("\nBy delivery time:")
            for item in stats["delivery_times"]:
                print(f"  {item['time']}: {item['count']}")

        if stats["weights"]:
            print("\nBy weight:")
            for item in stats["weights"]:
                print(f"  {item['weight']}: {item['count']} trades ({item['total_kg']} kg)")
        print("=" * 60)

    elif command == "query":
        trades = parser.get_trades(transaction_type="خرید", limit=10)
        print(f"\nFound {len(trades)} trades:")
        for trade in trades:
            weight = trade.get("weight") or "-"
            print(
                f"  {trade['price']:,.0f} - {trade['transaction_type']} - "
                f"{trade['transfer_method']} - {weight} - {trade['date']}"
            )


if __name__ == "__main__":
    main()

