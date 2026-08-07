import React from "react";
import { Filters } from "../types";

interface FilterPanelProps {
  filters: Filters;
  onFilterChange: (filters: Filters) => void;
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFilterChange,
}) => {
  const handleChange = (key: keyof Filters, value: string | number) => {
    onFilterChange({ ...filters, [key]: value });
  };

  return (
    <div className="filter-panel">
      <h3>Filters</h3>

      <div className="filter-row">
        <div className="filter-group">
          <label>Time Period (Days)</label>
          <input
            type="number"
            value={filters.days}
            onChange={(e) =>
              handleChange("days", parseInt(e.target.value) || 1)
            }
            min="1"
            max="365"
          />
        </div>

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
      </div>
    </div>
  );
};

export default FilterPanel;
