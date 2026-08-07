"""
Flask API for Trading Data
Provides endpoints for querying trades and generating chart data
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .parser import TradingMessageParser

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Get project root directory (parent of api directory)
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / "database" / "telegram_data.db")
# Ensure database directory exists
Path(PROJECT_ROOT / "database").mkdir(exist_ok=True)
parser = TradingMessageParser(DB_PATH)


def get_db():
    """Get database connection, ensuring required tables exist."""
    # Recreate trades schema if DB was wiped/recreated by the crawler
    parser._init_timeseries_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route('/api/trades', methods=['GET'])
def get_trades():
    """
    Get trades with optional filters

    Query parameters:
    - transaction_type: خرید, فروش, معامله
    - transfer_method: باحواله, بدون حواله
    - delivery_time: امروزی, فردا
    - min_price: minimum price
    - max_price: maximum price
    - start_date: start date (YYYY-MM-DD)
    - end_date: end date (YYYY-MM-DD)
    - limit: max results (default 100)
    - offset: pagination offset
    """
    try:
        # Get query parameters
        transaction_type = request.args.get('transaction_type')
        transfer_method = request.args.get('transfer_method')
        delivery_time = request.args.get('delivery_time')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)

        conn = get_db()
        cursor = conn.cursor()

        # Build query
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

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Add pagination
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
            "data": trades
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    try:
        stats = parser.get_stats()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chart/price-trend', methods=['GET'])
def price_trend():
    """
    Get price trend over time for charts

    Query parameters:
    - days: number of days to look back (default 1)
    - transaction_type: filter by type
    - transfer_method: filter by method
    - interval: minute, hour, day (default minute for <=1 day, hour for <=7 days, day otherwise)
    """
    try:
        days = request.args.get('days', default=1, type=int)
        transaction_type = request.args.get('transaction_type')
        transfer_method = request.args.get('transfer_method')
        interval = request.args.get('interval')

        # Auto-select interval based on days if not specified
        if not interval:
            if days <= 1:
                interval = 'minute'
            elif days <= 7:
                interval = 'hour'
            else:
                interval = 'day'

        conn = get_db()
        cursor = conn.cursor()

        # Calculate cutoff date
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Build query based on interval
        if interval == 'minute':
            time_format = "%Y-%m-%d %H:%M:00"
            group_by = "strftime('%Y-%m-%d %H:%M', date)"
        elif interval == 'hour':
            time_format = "%Y-%m-%d %H:00:00"
            group_by = "strftime('%Y-%m-%d %H', date)"
        else:  # day
            time_format = "%Y-%m-%d"
            group_by = "DATE(date)"

        query = f"""
            SELECT
                {group_by} as time_bucket,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                COUNT(*) as count
            FROM trades
            WHERE date >= ?
        """
        params = [cutoff]

        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)

        if transfer_method:
            query += " AND transfer_method = ?"
            params.append(transfer_method)

        query += f" GROUP BY {group_by} ORDER BY time_bucket"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        # Format for chart.js
        labels = []
        avg_prices = []
        min_prices = []
        max_prices = []
        volumes = []

        for row in results:
            labels.append(row['time_bucket'])
            avg_prices.append(round(row['avg_price'], 2) if row['avg_price'] else 0)
            min_prices.append(round(row['min_price'], 2) if row['min_price'] else 0)
            max_prices.append(round(row['max_price'], 2) if row['max_price'] else 0)
            volumes.append(row['count'])

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Average Price",
                        "data": avg_prices,
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)"
                    },
                    {
                        "label": "Min Price",
                        "data": min_prices,
                        "borderColor": "rgb(255, 99, 132)",
                        "backgroundColor": "rgba(255, 99, 132, 0.2)"
                    },
                    {
                        "label": "Max Price",
                        "data": max_prices,
                        "borderColor": "rgb(54, 162, 235)",
                        "backgroundColor": "rgba(54, 162, 235, 0.2)"
                    }
                ],
                "volume": volumes
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chart/transaction-distribution', methods=['GET'])
def transaction_distribution():
    """Get distribution of transaction types for pie/doughnut chart"""
    try:
        days = request.args.get('days', type=int)

        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT transaction_type, COUNT(*) as count
            FROM trades
        """
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " WHERE date >= ?"
            params.append(cutoff)

        query += " GROUP BY transaction_type ORDER BY count DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        labels = []
        data = []
        colors = {
            'خرید': 'rgb(54, 162, 235)',  # Blue
            'فروش': 'rgb(255, 99, 132)',  # Red
            'معامله': 'rgb(75, 192, 192)',  # Green
            'نامشخص': 'rgb(201, 203, 207)'  # Gray
        }
        background_colors = []

        for row in results:
            labels.append(row['transaction_type'])
            data.append(row['count'])
            background_colors.append(colors.get(row['transaction_type'], 'rgb(201, 203, 207)'))

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Transaction Types",
                    "data": data,
                    "backgroundColor": background_colors
                }]
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chart/transfer-distribution', methods=['GET'])
def transfer_distribution():
    """Get distribution of transfer methods for pie/doughnut chart"""
    try:
        days = request.args.get('days', type=int)

        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT transfer_method, COUNT(*) as count
            FROM trades
        """
        params = []

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " WHERE date >= ?"
            params.append(cutoff)

        query += " GROUP BY transfer_method ORDER BY count DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        labels = []
        data = []

        for row in results:
            labels.append(row['transfer_method'])
            data.append(row['count'])

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Transfer Methods",
                    "data": data,
                    "backgroundColor": [
                        'rgb(255, 205, 86)',
                        'rgb(153, 102, 255)',
                        'rgb(201, 203, 207)'
                    ]
                }]
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chart/volume-by-hour', methods=['GET'])
def volume_by_hour():
    """Get trading volume by hour of day"""
    try:
        days = request.args.get('days', default=1, type=int)

        conn = get_db()
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        query = """
            SELECT
                strftime('%H', date) as hour,
                COUNT(*) as count,
                AVG(price) as avg_price
            FROM trades
            WHERE date >= ?
            GROUP BY hour
            ORDER BY hour
        """

        cursor.execute(query, [cutoff])
        results = cursor.fetchall()
        conn.close()

        labels = [f"{int(row['hour']):02d}:00" for row in results]
        volumes = [row['count'] for row in results]
        avg_prices = [round(row['avg_price'], 2) if row['avg_price'] else 0 for row in results]

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Volume",
                        "data": volumes,
                        "backgroundColor": "rgba(54, 162, 235, 0.5)",
                        "yAxisID": "y"
                    },
                    {
                        "label": "Avg Price",
                        "data": avg_prices,
                        "type": "line",
                        "borderColor": "rgb(255, 99, 132)",
                        "yAxisID": "y1"
                    }
                ]
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chart/price-range', methods=['GET'])
def price_range():
    """Get price distribution (histogram)"""
    try:
        days = request.args.get('days', default=1, type=int)
        bins = request.args.get('bins', default=10, type=int)

        conn = get_db()
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Get min and max prices
        cursor.execute("""
            SELECT MIN(price) as min_price, MAX(price) as max_price
            FROM trades
            WHERE date >= ?
        """, [cutoff])

        result = cursor.fetchone()
        min_price = result['min_price']
        max_price = result['max_price']

        if not min_price or not max_price:
            return jsonify({
                "success": True,
                "data": {"labels": [], "datasets": []}
            })

        # Calculate bin size
        bin_size = (max_price - min_price) / bins

        # Get all prices
        cursor.execute("""
            SELECT price
            FROM trades
            WHERE date >= ?
            ORDER BY price
        """, [cutoff])

        prices = [row['price'] for row in cursor.fetchall()]
        conn.close()

        # Create bins
        labels = []
        data = []

        for i in range(bins):
            bin_start = min_price + (i * bin_size)
            bin_end = bin_start + bin_size
            count = sum(1 for p in prices if bin_start <= p < bin_end)

            labels.append(f"{int(bin_start)}-{int(bin_end)}")
            data.append(count)

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Price Distribution",
                    "data": data,
                    "backgroundColor": "rgba(75, 192, 192, 0.6)"
                }]
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/chart/buy-sell-comparison', methods=['GET'])
def buy_sell_comparison():
    """Compare buy vs sell prices over time"""
    try:
        days = request.args.get('days', default=1, type=int)

        conn = get_db()
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        query = """
            SELECT
                DATE(date) as day,
                transaction_type,
                AVG(price) as avg_price,
                COUNT(*) as count
            FROM trades
            WHERE date >= ? AND transaction_type IN ('خرید', 'فروش')
            GROUP BY day, transaction_type
            ORDER BY day
        """

        cursor.execute(query, [cutoff])
        results = cursor.fetchall()
        conn.close()

        # Organize data
        days_set = set()
        buy_data = {}
        sell_data = {}

        for row in results:
            day = row['day']
            days_set.add(day)

            if row['transaction_type'] == 'خرید':
                buy_data[day] = round(row['avg_price'], 2)
            elif row['transaction_type'] == 'فروش':
                sell_data[day] = round(row['avg_price'], 2)

        labels = sorted(days_set)
        buy_prices = [buy_data.get(day, None) for day in labels]
        sell_prices = [sell_data.get(day, None) for day in labels]

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Buy (خرید)",
                        "data": buy_prices,
                        "borderColor": "rgb(54, 162, 235)",
                        "backgroundColor": "rgba(54, 162, 235, 0.2)",
                        "fill": False
                    },
                    {
                        "label": "Sell (فروش)",
                        "data": sell_prices,
                        "borderColor": "rgb(255, 99, 132)",
                        "backgroundColor": "rgba(255, 99, 132, 0.2)",
                        "fill": False
                    }
                ]
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Trading Data API Server")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/trades")
    print("  GET  /api/stats")
    print("  GET  /api/chart/price-trend")
    print("  GET  /api/chart/transaction-distribution")
    print("  GET  /api/chart/transfer-distribution")
    print("  GET  /api/chart/volume-by-hour")
    print("  GET  /api/chart/price-range")
    print("  GET  /api/chart/buy-sell-comparison")
    print("\n" + "=" * 60)
    print("Starting server on http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

