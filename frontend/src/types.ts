// Type definitions for Trading Data API

export interface Trade {
  id: number;
  message_id: string;
  channel_id: number;
  channel_name: string;
  price: number;
  transaction_type: string;
  transfer_method: string;
  delivery_time: string;
  original_text: string;
  timestamp: number;
  date: string;
  crawled_at: string;
}

export interface TradesResponse {
  success: boolean;
  total: number;
  limit: number;
  offset: number;
  data: Trade[];
}

// Chart data compatible with Chart.js
// Using a flexible type that works with all chart types
export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string | string[];
    fill?: boolean;
    type?: 'line' | 'bar' | 'pie';
    yAxisID?: string;
    [key: string]: any; // Allow additional properties
  }>;
}

export interface ChartResponse {
  success: boolean;
  data: ChartData;
  volume?: number[];
}

export interface Stats {
  total_trades: number;
  transaction_types: Array<{ type: string; count: number }>;
  transfer_methods: Array<{ method: string; count: number }>;
  delivery_times: Array<{ time: string; count: number }>;
}

export interface StatsResponse {
  success: boolean;
  data: Stats;
}

export interface Filters {
  days: number;
  transactionType: string;
  transferMethod: string;
  deliveryTime: string;
  minPrice: string;
  maxPrice: string;
}

