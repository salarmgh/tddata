// Type definitions for Trading Data API

export interface Trade {
  id: number;
  message_id: string;
  channel_name: string;
  price: number;
  transaction_type: string;
  transfer_method: string;
  delivery_time: string | null;
  description: string | null;
  weight: string | null;
  weight_kg: number | null;
  timestamp: number;
  date: string;
}

export interface TradesResponse {
  success: boolean;
  total: number;
  limit: number;
  offset: number;
  data: Trade[];
}

export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string | string[];
    fill?: boolean;
    type?: "line" | "bar" | "pie";
    yAxisID?: string;
    [key: string]: any;
  }>;
  volume?: number[];
  weight_kg?: number[];
  trade_counts?: number[];
}

export interface ChartResponse {
  success: boolean;
  data: ChartData;
  volume?: number[];
}

export interface Stats {
  total_trades: number;
  total_weight_kg: number;
  transaction_types: Array<{ type: string; count: number }>;
  transfer_methods: Array<{ method: string; count: number }>;
  delivery_times: Array<{ time: string; count: number }>;
  weights: Array<{ weight: string; count: number; total_kg: number }>;
}

export interface StatsResponse {
  success: boolean;
  data: Stats;
}

export interface Filters {
  days: number;
  startDatetime: string;
  endDatetime: string;
  transactionType: string;
  transferMethod: string;
  deliveryTime: string;
  weight: string;
  minPrice: string;
  maxPrice: string;
}
