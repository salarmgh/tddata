import React, { useEffect, useState, useCallback } from "react";
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
  Legend,
  Filler,
} from "chart.js";
import { Line, Pie, Bar } from "react-chartjs-2";
import { ChartData as ChartJSChartData } from "chart.js";
import { apiService } from "../api";
import { Filters, ChartData, Stats, Trade } from "../types";
import FilterPanel from "./FilterPanel";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const Dashboard: React.FC = () => {
  const [filters, setFilters] = useState<Filters>({
    days: 1,
    startDatetime: "",
    endDatetime: "",
    transactionType: "",
    transferMethod: "",
    deliveryTime: "",
    weight: "",
    minPrice: "",
    maxPrice: "",
  });

  const [stats, setStats] = useState<Stats | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [priceTrend, setPriceTrend] = useState<ChartData | null>(null);
  const [transactionDist, setTransactionDist] = useState<ChartData | null>(
    null
  );
  const [transferDist, setTransferDist] = useState<ChartData | null>(null);
  const [buySellComp, setBuySellComp] = useState<ChartData | null>(null);
  const [volumeByHour, setVolumeByHour] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatTimeLabels = (labels: string[]): string[] => {
    return labels.map((label) => {
      if (label.includes(":")) {
        const timeMatch = label.match(/(\d{2}:\d{2})/);
        if (timeMatch) {
          return timeMatch[1];
        }
      }
      return label;
    });
  };

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [statsRes, tradesRes, priceTrendRes, transactionDistRes, transferDistRes, buySellCompRes, volumeByHourRes] =
        await Promise.all([
          apiService.getStats(),
          apiService.getTrades(filters, 50),
          apiService.charts.priceTrend(filters),
          apiService.charts.transactionDistribution(filters),
          apiService.charts.transferDistribution(filters),
          apiService.charts.buySellComparison(filters),
          apiService.charts.volumeByHour(filters),
        ]);

      setStats(statsRes.data);
      setTrades(tradesRes.data || []);

      setPriceTrend({
        ...priceTrendRes.data,
        labels: formatTimeLabels(priceTrendRes.data.labels),
      });
      setTransactionDist(transactionDistRes.data);
      setTransferDist(transferDistRes.data);
      setBuySellComp({
        ...buySellCompRes.data,
        labels: formatTimeLabels(buySellCompRes.data.labels),
      });
      setVolumeByHour(volumeByHourRes.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Trading Data Dashboard</h1>
        <p>Real-time trading analytics and insights</p>
      </header>

      <FilterPanel filters={filters} onFilterChange={setFilters} />

      {loading && <div className="loading">Loading data...</div>}
      {error && <div className="error">Error: {error}</div>}

      {stats && (
        <div className="stats-overview">
          <div className="stat-card">
            <h3>Total Trades</h3>
            <p className="stat-value">{stats.total_trades.toLocaleString()}</p>
            <p className="stat-subvalue">
              {(stats.total_weight_kg || 0).toLocaleString()} kg total
            </p>
          </div>

          <div className="stat-card">
            <h3>Weights</h3>
            <div className="stat-list">
              {(stats.weights || []).slice(0, 5).map((item) => (
                <div key={item.weight} className="stat-item">
                  <span>{item.weight}</span>
                  <strong>
                    {item.count} / {item.total_kg}kg
                  </strong>
                </div>
              ))}
              {(!stats.weights || stats.weights.length === 0) && (
                <div className="stat-item">
                  <span>No weights parsed yet</span>
                </div>
              )}
            </div>
          </div>

          <div className="stat-card">
            <h3>Transaction Types</h3>
            <div className="stat-list">
              {stats.transaction_types.map((item) => (
                <div key={item.type} className="stat-item">
                  <span>{item.type || "Unknown"}</span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="stat-card">
            <h3>Transfer Methods</h3>
            <div className="stat-list">
              {stats.transfer_methods.map((item) => (
                <div key={item.method} className="stat-item">
                  <span>{item.method || "Unknown"}</span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="charts-grid">
        {priceTrend && (
          <div
            className="chart-card full-width"
            style={{ paddingBottom: "80px" }}
          >
            <h2>Price Trend</h2>
            <p className="chart-subtitle">
              Average, min, and max prices over time
            </p>
            <Line
              data={priceTrend as ChartJSChartData<"line", number[], string>}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "top" as const,
                  },
                  title: {
                    display: false,
                  },
                },
                scales: {
                  y: {
                    beginAtZero: false,
                  },
                },
              }}
            />
          </div>
        )}

        {buySellComp && (
          <div className="chart-card large" style={{ paddingBottom: "80px" }}>
            <h2>Buy vs Sell Comparison</h2>
            <p className="chart-subtitle">Compare buy and sell prices</p>
            <Line
              data={buySellComp as ChartJSChartData<"line", number[], string>}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "top" as const,
                  },
                },
                scales: {
                  y: {
                    beginAtZero: false,
                  },
                },
              }}
            />
          </div>
        )}

        {transactionDist && (
          <div className="chart-card" style={{ paddingBottom: "80px" }}>
            <h2>Transaction Types</h2>
            <p className="chart-subtitle">Distribution of buy/sell/trade</p>
            <Pie
              data={
                transactionDist as ChartJSChartData<"pie", number[], string>
              }
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "bottom" as const,
                  },
                },
              }}
            />
          </div>
        )}

        {volumeByHour && (
          <div className="chart-card large" style={{ paddingBottom: "80px" }}>
            <h2>Volume by Hour</h2>
            <p className="chart-subtitle">
              Weight (kg) traded throughout the day
            </p>
            <Bar
              data={volumeByHour as ChartJSChartData<"bar", number[], string>}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "top" as const,
                  },
                },
                scales: {
                  y: {
                    type: "linear" as const,
                    display: true,
                    position: "left" as const,
                    title: {
                      display: true,
                      text: "Weight (kg)",
                    },
                  },
                  y1: {
                    type: "linear" as const,
                    display: true,
                    position: "right" as const,
                    title: {
                      display: true,
                      text: "Avg Price",
                    },
                    grid: {
                      drawOnChartArea: false,
                    },
                  },
                },
              }}
            />
          </div>
        )}

        {transferDist && (
          <div className="chart-card" style={{ paddingBottom: "80px" }}>
            <h2>Transfer Methods</h2>
            <p className="chart-subtitle">With vs without transfer</p>
            <Pie
              data={transferDist as ChartJSChartData<"pie", number[], string>}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "bottom" as const,
                  },
                },
              }}
            />
          </div>
        )}
      </div>

      <div className="trades-table-card">
        <h2>Recent Trades</h2>
        <p className="chart-subtitle">Including parsed weight from messages</p>
        <div className="trades-table-wrap">
          <table className="trades-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Price</th>
                <th>Type</th>
                <th>Transfer</th>
                <th>Weight</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id}>
                  <td>{trade.date}</td>
                  <td>{Number(trade.price).toLocaleString()}</td>
                  <td>{trade.transaction_type}</td>
                  <td>{trade.transfer_method}</td>
                  <td>{trade.weight || "—"}</td>
                </tr>
              ))}
              {trades.length === 0 && (
                <tr>
                  <td colSpan={5}>No trades for the selected filters</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
