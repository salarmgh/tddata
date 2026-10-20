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
    days: 0, // 0 = all time (data may be older than 1 day)
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
  const [weightByType, setWeightByType] = useState<ChartData | null>(null);
  const [weightNetTs, setWeightNetTs] = useState<ChartData | null>(null);
  const [weightNetCumulative, setWeightNetCumulative] =
    useState<ChartData | null>(null);
  const [sourceDatetime, setSourceDatetime] = useState("");
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

  /** Insert y=0 points wherever the series crosses zero so each segment is one sign. */
  const splitNetAtZero = (labels: string[], values: number[]) => {
    const outLabels: string[] = [];
    const outValues: number[] = [];
    const isCrossing: boolean[] = [];

    values.forEach((y1, i) => {
      if (i > 0) {
        const y0 = values[i - 1];
        if ((y0 > 0 && y1 < 0) || (y0 < 0 && y1 > 0)) {
          outLabels.push("");
          outValues.push(0);
          isCrossing.push(true);
        }
      }
      outLabels.push(labels[i]);
      outValues.push(y1);
      isCrossing.push(false);
    });

    return { labels: outLabels, values: outValues, isCrossing };
  };

  const buildSignedNetChart = (
    labels: string[],
    values: number[],
    seriesLabel: string
  ): ChartData => {
    const split = splitNetAtZero(labels, values);
    const blue = "rgb(54, 162, 235)";
    const red = "rgb(255, 99, 132)";
    const blueFill = "rgba(54, 162, 235, 0.15)";
    const redFill = "rgba(255, 99, 132, 0.15)";
    const segmentPositive = (y0: number, y1: number) =>
      y0 > 0 || y1 > 0 || (y0 === 0 && y1 === 0);

    return {
      labels: split.labels,
      datasets: [
        {
          label: seriesLabel,
          data: split.values,
          borderColor: blue,
          backgroundColor: blueFill,
          fill: true,
          tension: 0,
          pointRadius: split.isCrossing.map((c) => (c ? 0 : 3)),
          pointHoverRadius: split.isCrossing.map((c) => (c ? 0 : 4)),
          pointBackgroundColor: split.values.map((v) => (v >= 0 ? blue : red)),
          pointBorderColor: split.values.map((v) => (v >= 0 ? blue : red)),
          segment: {
            borderColor: (ctx: {
              p0: { parsed: { y: number | null } };
              p1: { parsed: { y: number | null } };
            }) => {
              const y0 = ctx.p0.parsed.y ?? 0;
              const y1 = ctx.p1.parsed.y ?? 0;
              return segmentPositive(y0, y1) ? blue : red;
            },
            backgroundColor: (ctx: {
              p0: { parsed: { y: number | null } };
              p1: { parsed: { y: number | null } };
            }) => {
              const y0 = ctx.p0.parsed.y ?? 0;
              const y1 = ctx.p1.parsed.y ?? 0;
              return segmentPositive(y0, y1) ? blueFill : redFill;
            },
          },
        },
      ],
    };
  };

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [statsRes, tradesRes, priceTrendRes, transactionDistRes, weightByTypeRes, weightNetTsRes, transferDistRes, buySellCompRes, volumeByHourRes] =
        await Promise.all([
          apiService.getStats(filters),
          apiService.getTrades(filters, 50),
          apiService.charts.priceTrend(filters),
          apiService.charts.transactionDistribution(filters),
          apiService.charts.weightByTransactionType(filters),
          apiService.charts.weightNetTimeseries(filters),
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
      setWeightByType(weightByTypeRes.data);
      {
        const netData = weightNetTsRes.data;
        const rawValues = (netData.datasets?.[0]?.data || []) as number[];
        setWeightNetTs(
          buildSignedNetChart(
            formatTimeLabels(netData.labels),
            rawValues,
            "Buy − Sell (kg)"
          )
        );
      }
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

  const fetchCumulativeNet = useCallback(async () => {
    try {
      const cumRes = await apiService.charts.weightNetCumulative(
        filters,
        sourceDatetime || filters.startDatetime || undefined
      );
      const cumData = cumRes.data;
      const rawValues = (cumData.datasets?.[0]?.data || []) as number[];
      setWeightNetCumulative(
        buildSignedNetChart(
          formatTimeLabels(cumData.labels),
          rawValues,
          "Cumulative Buy − Sell (kg)"
        )
      );
      if (!sourceDatetime && cumData.source_datetime) {
        const apiSource = cumData.source_datetime;
        const local = apiSource.includes("T")
          ? apiSource.slice(0, 16)
          : apiSource.replace(" ", "T").slice(0, 16);
        setSourceDatetime(local);
      }
    } catch (err) {
      console.error("Error fetching cumulative net:", err);
    }
  }, [filters, sourceDatetime]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  useEffect(() => {
    fetchCumulativeNet();
  }, [fetchCumulativeNet]);

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
          </div>

          <div className="stat-card">
            <h3>Total Weight</h3>
            <p className="stat-value">
              {(stats.total_weight_kg || 0).toLocaleString(undefined, {
                maximumFractionDigits: 2,
              })}
            </p>
            <p className="stat-subvalue">kg (filtered)</p>
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

        {weightByType && (
          <div className="chart-card" style={{ paddingBottom: "80px" }}>
            <h2>Weight by Type</h2>
            <p className="chart-subtitle">Total kg by buy / sell / trade</p>
            <Bar
              data={weightByType as ChartJSChartData<"bar", number[], string>}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    display: false,
                  },
                  tooltip: {
                    callbacks: {
                      label: (ctx) => {
                        const value = ctx.parsed.y ?? 0;
                        return `${value.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                        })} kg`;
                      },
                    },
                  },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    title: {
                      display: true,
                      text: "Weight (kg)",
                    },
                  },
                },
              }}
            />
          </div>
        )}

        {weightNetTs && (
          <div className="chart-card large" style={{ paddingBottom: "80px" }}>
            <h2>Net Weight (Buy − Sell)</h2>
            <p className="chart-subtitle">
              Blue = more buy · Red = more sell
            </p>
            <Line
              data={weightNetTs as ChartJSChartData<"line", number[], string>}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "top" as const,
                  },
                  tooltip: {
                    callbacks: {
                      label: (ctx) => {
                        const value = ctx.parsed.y ?? 0;
                        const sign = value > 0 ? "+" : "";
                        return `${sign}${value.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                        })} kg`;
                      },
                    },
                  },
                },
                scales: {
                  y: {
                    title: {
                      display: true,
                      text: "Buy − Sell (kg)",
                    },
                  },
                },
              }}
            />
          </div>
        )}

        {weightNetCumulative && (
          <div className="chart-card large" style={{ paddingBottom: "80px" }}>
            <div className="chart-header-row">
              <div>
                <h2>Cumulative Net from Source</h2>
                <p className="chart-subtitle">
                  Running buy − sell (kg) since the selected time · Blue = buy
                  surplus · Red = sell surplus
                </p>
              </div>
              <div className="chart-source-control">
                <label htmlFor="source-datetime">Source time</label>
                <input
                  id="source-datetime"
                  type="datetime-local"
                  value={sourceDatetime}
                  onChange={(e) => setSourceDatetime(e.target.value)}
                />
              </div>
            </div>
            <Line
              data={
                weightNetCumulative as ChartJSChartData<
                  "line",
                  number[],
                  string
                >
              }
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: "top" as const,
                  },
                  tooltip: {
                    callbacks: {
                      label: (ctx) => {
                        const value = ctx.parsed.y ?? 0;
                        const sign = value > 0 ? "+" : "";
                        return `${sign}${value.toLocaleString(undefined, {
                          maximumFractionDigits: 2,
                        })} kg from source`;
                      },
                    },
                  },
                },
                scales: {
                  y: {
                    title: {
                      display: true,
                      text: "Cumulative Buy − Sell (kg)",
                    },
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
        <p className="chart-subtitle">
          Including parsed weight from messages
          {stats && (
            <>
              {" "}
              · Total weight:{" "}
              <strong>
                {(stats.total_weight_kg || 0).toLocaleString(undefined, {
                  maximumFractionDigits: 2,
                })}{" "}
                kg
              </strong>
            </>
          )}
        </p>
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
