# Trading Data API Documentation

Flask REST API for querying and visualizing trading data.

## Setup

```bash
# Install dependencies
pip install flask flask-cors

# Run the API server
python api.py
```

Server will start at: `http://localhost:5000`

## API Endpoints

### Health Check

```
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-01-06T12:00:00"
}
```

### Get Trades

```
GET /api/trades?transaction_type=خرید&limit=50
```

**Query Parameters:**
- `transaction_type`: Filter by type (`خرید`, `فروش`, `معامله`)
- `transfer_method`: Filter by method (`باحواله`, `بدون حواله`)
- `delivery_time`: Filter by delivery (`امروزی`, `فردا`)
- `min_price`: Minimum price
- `max_price`: Maximum price
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `limit`: Max results (default 100)
- `offset`: Pagination offset

**Response:**
```json
{
  "success": true,
  "total": 150,
  "limit": 50,
  "offset": 0,
  "data": [
    {
      "id": 1,
      "message_id": "4294967341",
      "price": 70650.0,
      "transaction_type": "خرید",
      "transfer_method": "باحواله",
      "delivery_time": "امروزی",
      "timestamp": 1767688389,
      "date": "2026-01-06T12:03:09"
    }
  ]
}
```

### Get Statistics

```
GET /api/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_trades": 150,
    "by_type": [
      {"type": "خرید", "count": 65},
      {"type": "فروش", "count": 60}
    ],
    "by_transfer": [
      {"method": "باحواله", "count": 130}
    ],
    "price": {
      "min": 70000,
      "max": 71500,
      "avg": 70625.50
    }
  }
}
```

## Chart Endpoints

All chart endpoints return data formatted for Chart.js/react-chartjs-2.

### 1. Price Trend

```
GET /api/chart/price-trend?days=1&interval=minute
```

**Parameters:**
- `days`: Number of days to look back (default 1)
- `transaction_type`: Filter by type
- `transfer_method`: Filter by method
- `interval`: `minute`, `hour`, or `day` (auto-selected based on days if not specified:
  - ≤1 day: minute
  - ≤7 days: hour
  - >7 days: day)

**Response (minute interval):**
```json
{
  "success": true,
  "data": {
    "labels": ["2026-01-06 12:00", "2026-01-06 12:01", "2026-01-06 12:02"],
    "datasets": [
      {
        "label": "Average Price",
        "data": [70500, 70550, 70650],
        "borderColor": "rgb(75, 192, 192)"
      }
    ],
    "volume": [15, 18, 22]
  }
}
```

**Use in React:**
```jsx
import { Line } from 'react-chartjs-2';

<Line data={response.data.data} />
```

### 2. Transaction Distribution (Pie Chart)

```
GET /api/chart/transaction-distribution?days=7
```

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["خرید", "فروش", "معامله"],
    "datasets": [{
      "label": "Transaction Types",
      "data": [65, 60, 25],
      "backgroundColor": [
        "rgb(54, 162, 235)",
        "rgb(255, 99, 132)",
        "rgb(75, 192, 192)"
      ]
    }]
  }
}
```

**Use in React:**
```jsx
import { Pie } from 'react-chartjs-2';

<Pie data={response.data.data} />
```

### 3. Transfer Method Distribution

```
GET /api/chart/transfer-distribution?days=7
```

Similar to transaction distribution but for transfer methods.

### 4. Volume by Hour

```
GET /api/chart/volume-by-hour?days=7
```

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["00:00", "01:00", "02:00"],
    "datasets": [
      {
        "label": "Volume",
        "data": [10, 5, 3],
        "backgroundColor": "rgba(54, 162, 235, 0.5)",
        "yAxisID": "y"
      },
      {
        "label": "Avg Price",
        "data": [70500, 70600, 70550],
        "type": "line",
        "borderColor": "rgb(255, 99, 132)",
        "yAxisID": "y1"
      }
    ]
  }
}
```

**Use in React (Mixed Chart):**
```jsx
import { Bar } from 'react-chartjs-2';

<Bar
  data={response.data.data}
  options={{
    scales: {
      y: { type: 'linear', position: 'left' },
      y1: { type: 'linear', position: 'right' }
    }
  }}
/>
```

### 5. Price Range Distribution (Histogram)

```
GET /api/chart/price-range?days=1&bins=10
```

**Parameters:**
- `days`: Number of days (default 1)
- `bins`: Number of bins/buckets (default 10)

### 6. Buy vs Sell Comparison

```
GET /api/chart/buy-sell-comparison?days=1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["2026-01-01", "2026-01-02"],
    "datasets": [
      {
        "label": "Buy (خرید)",
        "data": [70500, 70550],
        "borderColor": "rgb(54, 162, 235)"
      },
      {
        "label": "Sell (فروش)",
        "data": [70600, 70700],
        "borderColor": "rgb(255, 99, 132)"
      }
    ]
  }
}
```

## Example Usage with React

### Setup React Project

```bash
npx create-react-app trading-dashboard
cd trading-dashboard
npm install react-chartjs-2 chart.js axios
```

### Example Component

```jsx
import React, { useEffect, useState } from 'react';
import { Line, Pie, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import axios from 'axios';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const API_BASE = 'http://localhost:5000/api';

function TradingDashboard() {
  const [priceTrend, setPriceTrend] = useState(null);
  const [transactionDist, setTransactionDist] = useState(null);
  const [buySellComp, setBuySellComp] = useState(null);

  useEffect(() => {
    // Fetch price trend
    axios.get(`${API_BASE}/chart/price-trend?days=7`)
      .then(res => setPriceTrend(res.data.data))
      .catch(err => console.error(err));

    // Fetch transaction distribution
    axios.get(`${API_BASE}/chart/transaction-distribution?days=7`)
      .then(res => setTransactionDist(res.data.data))
      .catch(err => console.error(err));

    // Fetch buy/sell comparison
    axios.get(`${API_BASE}/chart/buy-sell-comparison?days=7`)
      .then(res => setBuySellComp(res.data.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="dashboard">
      <h1>Trading Dashboard</h1>

      <div className="chart-container">
        <h2>Price Trend (Last 7 Days)</h2>
        {priceTrend && <Line data={priceTrend} />}
      </div>

      <div className="chart-container">
        <h2>Transaction Types</h2>
        {transactionDist && <Pie data={transactionDist} />}
      </div>

      <div className="chart-container">
        <h2>Buy vs Sell Comparison</h2>
        {buySellComp && <Line data={buySellComp} />}
      </div>
    </div>
  );
}

export default TradingDashboard;
```

### With Filters

```jsx
function FilteredChart() {
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({
    days: 7,
    transactionType: '',
    transferMethod: ''
  });

  const fetchData = () => {
    const params = new URLSearchParams();
    if (filters.days) params.append('days', filters.days);
    if (filters.transactionType) params.append('transaction_type', filters.transactionType);
    if (filters.transferMethod) params.append('transfer_method', filters.transferMethod);

    axios.get(`${API_BASE}/chart/price-trend?${params}`)
      .then(res => setData(res.data.data))
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchData();
  }, [filters]);

  return (
    <div>
      <div className="filters">
        <select onChange={(e) => setFilters({...filters, transactionType: e.target.value})}>
          <option value="">All Types</option>
          <option value="خرید">Buy (خرید)</option>
          <option value="فروش">Sell (فروش)</option>
          <option value="معامله">Trade (معامله)</option>
        </select>

        <select onChange={(e) => setFilters({...filters, transferMethod: e.target.value})}>
          <option value="">All Methods</option>
          <option value="باحواله">With Transfer</option>
          <option value="بدون حواله">Without Transfer</option>
        </select>

        <input
          type="number"
          value={filters.days}
          onChange={(e) => setFilters({...filters, days: e.target.value})}
          placeholder="Days"
        />
      </div>

      {data && <Line data={data} />}
    </div>
  );
}
```

## CORS

CORS is enabled for all origins. In production, restrict to your frontend domain:

```python
from flask_cors import CORS

# Only allow specific origin
CORS(app, resources={r"/api/*": {"origins": "https://yourdomain.com"}})
```

## Error Handling

All endpoints return standard error format:

```json
{
  "success": false,
  "error": "Error message here"
}
```

HTTP status codes:
- `200` - Success
- `500` - Server error

