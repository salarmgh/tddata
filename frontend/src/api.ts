import axios from "axios";
import { TradesResponse, ChartResponse, StatsResponse, Filters } from "./types";

const API_BASE = "http://localhost:5000/api";

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

const appendFilterParams = (
  params: URLSearchParams,
  filters: Partial<Filters>
) => {
  if (filters.startDatetime) {
    params.append("start_datetime", filters.startDatetime);
  }
  if (filters.endDatetime) {
    params.append("end_datetime", filters.endDatetime);
  }
  // Only use days lookback when no explicit time range is set
  if (!filters.startDatetime && !filters.endDatetime && filters.days) {
    params.append("days", filters.days.toString());
  }
  if (filters.transactionType) {
    params.append("transaction_type", filters.transactionType);
  }
  if (filters.transferMethod) {
    params.append("transfer_method", filters.transferMethod);
  }
  if (filters.deliveryTime) {
    params.append("delivery_time", filters.deliveryTime);
  }
  if (filters.weight) {
    params.append("weight", filters.weight);
  }
  if (filters.minPrice) {
    params.append("min_price", filters.minPrice);
  }
  if (filters.maxPrice) {
    params.append("max_price", filters.maxPrice);
  }
};

export const apiService = {
  health: async () => {
    const response = await api.get("/health");
    return response.data;
  },

  getTrades: async (
    filters: Partial<Filters>,
    limit = 100,
    offset = 0
  ): Promise<TradesResponse> => {
    const params = new URLSearchParams();
    appendFilterParams(params, filters);
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());

    const response = await api.get<TradesResponse>(`/trades?${params}`);
    return response.data;
  },

  getStats: async (): Promise<StatsResponse> => {
    const response = await api.get<StatsResponse>("/stats");
    return response.data;
  },

  getWeights: async (): Promise<{
    success: boolean;
    data: Array<{ weight: string; count: number }>;
  }> => {
    const response = await api.get("/filters/weights");
    return response.data;
  },

  charts: {
    priceTrend: async (filters: Partial<Filters>): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      appendFilterParams(params, filters);
      const response = await api.get<ChartResponse>(
        `/chart/price-trend?${params}`
      );
      return response.data;
    },

    transactionDistribution: async (
      filters: Partial<Filters>
    ): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      appendFilterParams(params, filters);
      const response = await api.get<ChartResponse>(
        `/chart/transaction-distribution?${params}`
      );
      return response.data;
    },

    transferDistribution: async (
      filters: Partial<Filters>
    ): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      appendFilterParams(params, filters);
      const response = await api.get<ChartResponse>(
        `/chart/transfer-distribution?${params}`
      );
      return response.data;
    },

    volumeByHour: async (filters: Partial<Filters>): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      appendFilterParams(params, filters);
      const response = await api.get<ChartResponse>(
        `/chart/volume-by-hour?${params}`
      );
      return response.data;
    },

    priceRange: async (
      filters: Partial<Filters>,
      bins = 10
    ): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      appendFilterParams(params, filters);
      params.append("bins", bins.toString());
      const response = await api.get<ChartResponse>(
        `/chart/price-range?${params}`
      );
      return response.data;
    },

    buySellComparison: async (
      filters: Partial<Filters>
    ): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      appendFilterParams(params, filters);
      const response = await api.get<ChartResponse>(
        `/chart/buy-sell-comparison?${params}`
      );
      return response.data;
    },
  },
};
