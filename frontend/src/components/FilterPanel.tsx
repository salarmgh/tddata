import React, { useEffect, useState } from "react";
import { Filters } from "../types";
import { apiService } from "../api";

interface FilterPanelProps {
  filters: Filters;
  onFilterChange: (filters: Filters) => void;
}

const toDatetimeLocal = (date: Date): string => {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFilterChange,
}) => {
  const [weights, setWeights] = useState<Array<{ weight: string; count: number }>>(
    []
  );

  useEffect(() => {
    apiService
      .getWeights()
      .then((res) => setWeights(res.data || []))
      .catch(() => setWeights([]));
  }, []);

  const handleChange = (key: keyof Filters, value: string | number) => {
    onFilterChange({ ...filters, [key]: value });
  };

  const applyQuickRange = (days: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    onFilterChange({
      ...filters,
      days,
      startDatetime: toDatetimeLocal(start),
      endDatetime: toDatetimeLocal(end),
    });
  };

  const clearTimeRange = () => {
    onFilterChange({
      ...filters,
      startDatetime: "",
      endDatetime: "",
      days: 0,
    });
  };

  return (
    <div className="filter-panel">
      <h3>Filters</h3>

      <div className="filter-row">
        <div className="filter-group">
          <label>Start (date & time)</label>
          <input
            type="datetime-local"
            value={filters.startDatetime}
            onChange={(e) => handleChange("startDatetime", e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>End (date & time)</label>
          <input
            type="datetime-local"
            value={filters.endDatetime}
            onChange={(e) => handleChange("endDatetime", e.target.value)}
          />
        </div>

          <div className="filter-group">
          <label>Quick range</label>
          <div className="quick-range-buttons">
            <button type="button" onClick={() => applyQuickRange(1)}>
              1d
            </button>
            <button type="button" onClick={() => applyQuickRange(7)}>
              7d
            </button>
            <button type="button" onClick={() => applyQuickRange(30)}>
              30d
            </button>
            <button type="button" onClick={clearTimeRange}>
              All
            </button>
          </div>
        </div>
      </div>

      <div className="filter-row">
        <div className="filter-group">
          <label>Transaction Type</label>
          <select
            value={filters.transactionType}
            onChange={(e) => handleChange("transactionType", e.target.value)}
          >
            <option value="">All Types</option>
            <option value="خرید">Buy (خرید)</option>
            <option value="فروش">Sell (فروش)</option>
            <option value="معامله">Trade (معامله)</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Transfer Method</label>
          <select
            value={filters.transferMethod}
            onChange={(e) => handleChange("transferMethod", e.target.value)}
          >
            <option value="">All Methods</option>
            <option value="باحواله">With Transfer (باحواله)</option>
            <option value="بدون حواله">Without Transfer (بدون حواله)</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Delivery Time</label>
          <select
            value={filters.deliveryTime}
            onChange={(e) => handleChange("deliveryTime", e.target.value)}
          >
            <option value="">All Times</option>
            <option value="امروزی">Today (امروزی)</option>
            <option value="فردا">Tomorrow (فردا)</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Weight</label>
          <select
            value={filters.weight}
            onChange={(e) => handleChange("weight", e.target.value)}
          >
            <option value="">All Weights</option>
            {weights.map((item) => (
              <option key={item.weight} value={item.weight}>
                {item.weight} ({item.count})
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

export default FilterPanel;
