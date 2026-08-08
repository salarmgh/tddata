"""
Flask API for Trading Data
Provides endpoints for querying trades and generating chart data
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from .parser import TradingMessageParser

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / "database" / "telegram_data.db")
Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)
parser = TradingMessageParser(DB_PATH)


def get_db():
    """Get database connection, ensuring required tables exist."""
    parser._init_timeseries_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _datetime_local_to_iso(value: str) -> str:
    """Convert HTML datetime-local (YYYY-MM-DDTHH:MM) to comparable ISO string."""
    if not value:
        return value
    value = value.strip()
    if "T" in value and len(value) == 16:
        return value + ":00"
    return value


def resolve_time_bounds():
    """
    Resolve start/end from query args.
    Prefers start_datetime/end_datetime; falls back to days lookback.
    """
    start = request.args.get("start_datetime") or request.args.get("start_date")
    end = request.args.get("end_datetime") or request.args.get("end_date")
    days = request.args.get("days", type=int)

    start = _datetime_local_to_iso(start) if start else None
    end = _datetime_local_to_iso(end) if end else None

    if not start and not end and days:
        start = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

    return start, end, days


def append_common_filters(query: str, params: list, *, include_time: bool = True) -> tuple:
    """Append shared trade filters from request args."""
    transaction_type = request.args.get("transaction_type")
    transfer_method = request.args.get("transfer_method")
    delivery_time = request.args.get("delivery_time")
    weight = request.args.get("weight")
    min_weight_kg = request.args.get("min_weight_kg", type=float)
    max_weight_kg = request.args.get("max_weight_kg", type=float)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    if include_time:
        start, end, _ = resolve_time_bounds()
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)

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

    return query, params


def pick_interval(start: str, end: str, days: int, explicit: str = None) -> str:
    if explicit:
        return explicit
    if start and end:
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            span_days = max((end_dt - start_dt).total_seconds() / 86400, 0)
        except ValueError:
            span_days = days or 1
    else:
        span_days = days or 1

    if span_days <= 1:
        return "minute"
    if span_days <= 7:
        return "hour"
    return "day"


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route("/api/trades", methods=["GET"])
def get_trades():
    """
    Get trades with optional filters

    Query parameters:
    - transaction_type, transfer_method, delivery_time, weight
    - min_price, max_price, min_weight_kg, max_weight_kg
    - start_datetime / end_datetime (or start_date / end_date)
    - days: lookback if no explicit range
    - limit, offset
    """
    try:
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)

        conn = get_db()
        cursor = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        query, params = append_common_filters(query, params)

        count_query = query.replace("SELECT *", "SELECT COUNT(*)", 1)
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": trades,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Overall or filtered statistics (supports same filters as /api/trades)."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        base = "FROM trades WHERE 1=1"
        params: list = []
        filtered, params = append_common_filters(base, params)

        cursor.execute(f"SELECT COUNT(*) as total_trades, COALESCE(SUM(weight_kg), 0) as total_weight_kg {filtered}", params)
        totals = cursor.fetchone()

        cursor.execute(f"""
            SELECT transaction_type, COUNT(*) as count,
                   COALESCE(SUM(weight_kg), 0) as total_kg
            {filtered}
            GROUP BY transaction_type
            ORDER BY count DESC
        """, params)
        transaction_types = [
            {"type": r["transaction_type"], "count": r["count"], "total_kg": round(r["total_kg"] or 0, 4)}
            for r in cursor.fetchall()
        ]

        cursor.execute(f"""
            SELECT transfer_method, COUNT(*) as count,
                   COALESCE(SUM(weight_kg), 0) as total_kg
            {filtered}
            GROUP BY transfer_method
            ORDER BY count DESC
        """, params)
        transfer_methods = [
            {"method": r["transfer_method"], "count": r["count"], "total_kg": round(r["total_kg"] or 0, 4)}
            for r in cursor.fetchall()
        ]

        cursor.execute(f"""
            SELECT delivery_time, COUNT(*) as count,
                   COALESCE(SUM(weight_kg), 0) as total_kg
            {filtered}
            AND delivery_time IS NOT NULL
            GROUP BY delivery_time
            ORDER BY count DESC
        """, params)
        delivery_times = [
            {"time": r["delivery_time"], "count": r["count"], "total_kg": round(r["total_kg"] or 0, 4)}
            for r in cursor.fetchall()
        ]

        cursor.execute(f"""
            SELECT weight, COUNT(*) as count, COALESCE(SUM(weight_kg), 0) as total_kg
            {filtered}
            AND weight IS NOT NULL
            GROUP BY weight
            ORDER BY count DESC
            LIMIT 20
        """, params)
        weights = [
            {"weight": r["weight"], "count": r["count"], "total_kg": round(r["total_kg"] or 0, 4)}
            for r in cursor.fetchall()
        ]

        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "total_trades": totals["total_trades"] or 0,
                "total_weight_kg": round(totals["total_weight_kg"] or 0, 4),
                "transaction_types": transaction_types,
                "transfer_methods": transfer_methods,
                "delivery_times": delivery_times,
                "weights": weights,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/filters/weights", methods=["GET"])
def list_weights():
    """Distinct weight values for filter dropdowns."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT weight, COUNT(*) as count
            FROM trades
            WHERE weight IS NOT NULL
            GROUP BY weight
            ORDER BY count DESC, weight
        """)
        rows = [{"weight": r["weight"], "count": r["count"]} for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/price-trend", methods=["GET"])
def price_trend():
    try:
        start, end, days = resolve_time_bounds()
        if not start and not end:
            days = days or 1
            start = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

        interval = pick_interval(start, end, days or 1, request.args.get("interval"))

        if interval == "minute":
            group_by = "strftime('%Y-%m-%d %H:%M', date)"
        elif interval == "hour":
            group_by = "strftime('%Y-%m-%d %H', date)"
        else:
            group_by = "DATE(date)"

        conn = get_db()
        cursor = conn.cursor()

        query = f"""
            SELECT
                {group_by} as time_bucket,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                COUNT(*) as count,
                COALESCE(SUM(weight_kg), 0) as total_weight_kg
            FROM trades
            WHERE 1=1
        """
        params = []
        query, params = append_common_filters(query, params)
        query += f" GROUP BY {group_by} ORDER BY time_bucket"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        labels = []
        avg_prices = []
        min_prices = []
        max_prices = []
        volumes = []
        weight_volumes = []

        for row in results:
            labels.append(row["time_bucket"])
            avg_prices.append(round(row["avg_price"], 2) if row["avg_price"] else 0)
            min_prices.append(round(row["min_price"], 2) if row["min_price"] else 0)
            max_prices.append(round(row["max_price"], 2) if row["max_price"] else 0)
            volumes.append(row["count"])
            weight_volumes.append(round(row["total_weight_kg"] or 0, 4))

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Average Price",
                        "data": avg_prices,
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    },
                    {
                        "label": "Min Price",
                        "data": min_prices,
                        "borderColor": "rgb(255, 99, 132)",
                        "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    },
                    {
                        "label": "Max Price",
                        "data": max_prices,
                        "borderColor": "rgb(54, 162, 235)",
                        "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    },
                ],
                "volume": volumes,
                "weight_kg": weight_volumes,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/transaction-distribution", methods=["GET"])
def transaction_distribution():
    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT transaction_type, COUNT(*) as count,
                   COALESCE(SUM(weight_kg), 0) as total_weight_kg
            FROM trades
            WHERE 1=1
        """
        params = []
        query, params = append_common_filters(query, params)
        query += " GROUP BY transaction_type ORDER BY count DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        colors = {
            "خرید": "rgb(54, 162, 235)",
            "فروش": "rgb(255, 99, 132)",
            "معامله": "rgb(75, 192, 192)",
            "نامشخص": "rgb(201, 203, 207)",
        }

        labels = []
        data = []
        background_colors = []
        for row in results:
            labels.append(row["transaction_type"])
            data.append(row["count"])
            background_colors.append(colors.get(row["transaction_type"], "rgb(201, 203, 207)"))

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Transaction Types",
                    "data": data,
                    "backgroundColor": background_colors,
                }],
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/weight-by-transaction-type", methods=["GET"])
def weight_by_transaction_type():
    """Total weight (kg) grouped by transaction type."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT transaction_type,
                   COUNT(*) as count,
                   COALESCE(SUM(weight_kg), 0) as total_weight_kg
            FROM trades
            WHERE 1=1
        """
        params = []
        query, params = append_common_filters(query, params)
        query += " GROUP BY transaction_type ORDER BY total_weight_kg DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        colors = {
            "خرید": "rgba(54, 162, 235, 0.8)",
            "فروش": "rgba(255, 99, 132, 0.8)",
            "معامله": "rgba(75, 192, 192, 0.8)",
            "نامشخص": "rgba(201, 203, 207, 0.8)",
        }
        border_colors = {
            "خرید": "rgb(54, 162, 235)",
            "فروش": "rgb(255, 99, 132)",
            "معامله": "rgb(75, 192, 192)",
            "نامشخص": "rgb(201, 203, 207)",
        }

        labels = []
        weights = []
        counts = []
        background_colors = []
        borders = []
        for row in results:
            labels.append(row["transaction_type"])
            weights.append(round(row["total_weight_kg"] or 0, 4))
            counts.append(row["count"])
            background_colors.append(colors.get(row["transaction_type"], "rgba(201, 203, 207, 0.8)"))
            borders.append(border_colors.get(row["transaction_type"], "rgb(201, 203, 207)"))

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Weight (kg)",
                        "data": weights,
                        "backgroundColor": background_colors,
                        "borderColor": borders,
                        "borderWidth": 1,
                    }
                ],
                "trade_counts": counts,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/transfer-distribution", methods=["GET"])
def transfer_distribution():
    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT transfer_method, COUNT(*) as count
            FROM trades
            WHERE 1=1
        """
        params = []
        query, params = append_common_filters(query, params)
        query += " GROUP BY transfer_method ORDER BY count DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        labels = [row["transfer_method"] for row in results]
        data = [row["count"] for row in results]

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Transfer Methods",
                    "data": data,
                    "backgroundColor": [
                        "rgb(255, 205, 86)",
                        "rgb(153, 102, 255)",
                        "rgb(201, 203, 207)",
                    ],
                }],
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/volume-by-hour", methods=["GET"])
def volume_by_hour():
    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT
                strftime('%H', date) as hour,
                COUNT(*) as count,
                COALESCE(SUM(weight_kg), 0) as total_weight_kg,
                AVG(price) as avg_price
            FROM trades
            WHERE 1=1
        """
        params = []
        query, params = append_common_filters(query, params)
        query += " GROUP BY hour ORDER BY hour"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        labels = [f"{int(row['hour']):02d}:00" for row in results]
        volumes = [round(row["total_weight_kg"] or 0, 4) for row in results]
        trade_counts = [row["count"] for row in results]
        avg_prices = [round(row["avg_price"], 2) if row["avg_price"] else 0 for row in results]

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Weight (kg)",
                        "data": volumes,
                        "backgroundColor": "rgba(54, 162, 235, 0.5)",
                        "yAxisID": "y",
                    },
                    {
                        "label": "Avg Price",
                        "data": avg_prices,
                        "type": "line",
                        "borderColor": "rgb(255, 99, 132)",
                        "yAxisID": "y1",
                    },
                ],
                "trade_counts": trade_counts,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/price-range", methods=["GET"])
def price_range():
    try:
        bins = request.args.get("bins", default=10, type=int)

        conn = get_db()
        cursor = conn.cursor()

        base = "FROM trades WHERE 1=1"
        params = []
        filtered, params = append_common_filters(base, params)

        cursor.execute(f"SELECT MIN(price) as min_price, MAX(price) as max_price {filtered}", params)
        result = cursor.fetchone()
        min_price = result["min_price"]
        max_price = result["max_price"]

        if not min_price or not max_price:
            conn.close()
            return jsonify({"success": True, "data": {"labels": [], "datasets": []}})

        bin_size = (max_price - min_price) / bins if bins else 1
        cursor.execute(f"SELECT price {filtered} ORDER BY price", params)
        prices = [row["price"] for row in cursor.fetchall()]
        conn.close()

        labels = []
        data = []
        for i in range(bins):
            bin_start = min_price + (i * bin_size)
            bin_end = bin_start + bin_size
            count = sum(1 for p in prices if bin_start <= p < bin_end or (i == bins - 1 and p == bin_end))
            labels.append(f"{int(bin_start)}-{int(bin_end)}")
            data.append(count)

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Price Distribution",
                    "data": data,
                    "backgroundColor": "rgba(75, 192, 192, 0.6)",
                }],
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chart/buy-sell-comparison", methods=["GET"])
def buy_sell_comparison():
    try:
        start, end, days = resolve_time_bounds()
        if not start and not end:
            days = days or 1
            start = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

        interval = pick_interval(start, end, days or 1, request.args.get("interval"))
        if interval == "minute":
            group_by = "strftime('%Y-%m-%d %H:%M', date)"
        elif interval == "hour":
            group_by = "strftime('%Y-%m-%d %H', date)"
        else:
            group_by = "DATE(date)"

        conn = get_db()
        cursor = conn.cursor()

        query = f"""
            SELECT
                {group_by} as bucket,
                transaction_type,
                AVG(price) as avg_price,
                COUNT(*) as count,
                COALESCE(SUM(weight_kg), 0) as total_weight_kg
            FROM trades
            WHERE transaction_type IN ('خرید', 'فروش')
        """
        params = []
        query, params = append_common_filters(query, params)
        query += f" GROUP BY bucket, transaction_type ORDER BY bucket"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        buckets = set()
        buy_data = {}
        sell_data = {}

        for row in results:
            bucket = row["bucket"]
            buckets.add(bucket)
            if row["transaction_type"] == "خرید":
                buy_data[bucket] = round(row["avg_price"], 2)
            elif row["transaction_type"] == "فروش":
                sell_data[bucket] = round(row["avg_price"], 2)

        labels = sorted(buckets)
        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Buy (خرید)",
                        "data": [buy_data.get(day) for day in labels],
                        "borderColor": "rgb(54, 162, 235)",
                        "backgroundColor": "rgba(54, 162, 235, 0.2)",
                        "fill": False,
                    },
                    {
                        "label": "Sell (فروش)",
                        "data": [sell_data.get(day) for day in labels],
                        "borderColor": "rgb(255, 99, 132)",
                        "backgroundColor": "rgba(255, 99, 132, 0.2)",
                        "fill": False,
                    },
                ],
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 60)
    print("Trading Data API Server")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/trades")
    print("  GET  /api/stats")
    print("  GET  /api/filters/weights")
    print("  GET  /api/chart/price-trend")
    print("  GET  /api/chart/transaction-distribution")
    print("  GET  /api/chart/weight-by-transaction-type")
    print("  GET  /api/chart/transfer-distribution")
    print("  GET  /api/chart/volume-by-hour")
    print("  GET  /api/chart/price-range")
    print("  GET  /api/chart/buy-sell-comparison")
    print("\n" + "=" * 60)
    print("Starting server on http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
