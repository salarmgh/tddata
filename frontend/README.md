# Trading Data Dashboard - Frontend

React TypeScript dashboard for visualizing trading data with interactive charts and filters.

## Features

- 📊 **6 Interactive Charts**:
  - Price Trend (Line Chart)
  - Buy vs Sell Comparison (Multi-line Chart)
  - Transaction Type Distribution (Pie Chart)
  - Transfer Method Distribution (Pie Chart)
  - Volume by Hour (Bar + Line Chart)
  - Price Range Distribution (Histogram)

- 🎛️ **Advanced Filters**:
  - Time period (days)
  - Transaction type (Buy/Sell/Trade)
  - Transfer method (With/Without Transfer)
  - Delivery time
  - Price range (min/max)

- 📈 **Real-time Statistics**:
  - Total trades
  - Transaction type breakdown
  - Transfer method breakdown
  - Delivery time breakdown

## Tech Stack

- **React** 18 with TypeScript
- **Chart.js** with **react-chartjs-2**
- **Axios** for API calls
- Fully typed with TypeScript interfaces

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Start API Server

Make sure the Flask API is running on `http://localhost:5000`:

```bash
# In the parent directory
python api.py
```

### 3. Start Frontend

```bash
npm start
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx       # Main dashboard component
│   │   └── FilterPanel.tsx     # Filter controls
│   ├── types.ts                # TypeScript interfaces
│   ├── api.ts                  # API service layer
│   ├── App.tsx                 # Root component
│   ├── App.css                 # Styles
│   └── index.tsx               # Entry point
├── public/
└── package.json
```

## Available Scripts

### `npm start`

Runs the app in development mode.
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### `npm test`

Launches the test runner in interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.
Optimized and minified for best performance.

### `npm run eject`

**Note: this is a one-way operation!**

## API Configuration

The API base URL is configured in `src/api.ts`:

```typescript
const API_BASE = 'http://localhost:5000/api';
```

To change the API endpoint, update this constant.

## Customization

### Adding New Charts

1. Add new endpoint to `api.ts`:

```typescript
charts: {
  myNewChart: async (filters) => {
    const response = await api.get<ChartResponse>('/chart/my-new-chart');
    return response.data;
  }
}
```

2. Add state in `Dashboard.tsx`:

```typescript
const [myChart, setMyChart] = useState<ChartData | null>(null);
```

3. Fetch in `fetchAllData()`:

```typescript
const myChartRes = await apiService.charts.myNewChart(filters);
setMyChart(myChartRes.data);
```

4. Render in JSX:

```tsx
{myChart && (
  <div className="chart-card">
    <h2>My New Chart</h2>
    <Line data={myChart} />
  </div>
)}
```

### Styling

All styles are in `src/App.css`. The design uses:
- Gradient backgrounds
- Card-based layout
- Responsive grid system
- Hover effects and animations

Colors:
- Primary: `#667eea` (purple-blue)
- Secondary: `#764ba2` (purple)
- Accent: gradient between primary and secondary

## Browser Support

Works on all modern browsers:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Charts are memoized and only re-render on data changes
- All API calls are batched using `Promise.all`
- Responsive design with CSS Grid and Flexbox

## Troubleshooting

### API Connection Error

Make sure:
1. Flask API is running on `http://localhost:5000`
2. CORS is enabled in the API
3. No firewall blocking localhost connections

### Charts Not Displaying

Check:
1. Browser console for errors
2. Network tab for failed API requests
3. Make sure there's data in the database

### Build Errors

Clear cache and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

## License

MIT
