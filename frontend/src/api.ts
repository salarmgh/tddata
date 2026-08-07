import axios from 'axios';
import { TradesResponse, ChartResponse, StatsResponse, Filters } from './types';

const API_BASE = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Health check
  health: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get trades with filters
  getTrades: async (filters: Partial<Filters>, limit = 100, offset = 0): Promise<TradesResponse> => {
    const params = new URLSearchParams();

    if (filters.transactionType) params.append('transaction_type', filters.transactionType);
    if (filters.transferMethod) params.append('transfer_method', filters.transferMethod);
    if (filters.deliveryTime) params.append('delivery_time', filters.deliveryTime);
    if (filters.minPrice) params.append('min_price', filters.minPrice);
    if (filters.maxPrice) params.append('max_price', filters.maxPrice);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const response = await api.get<TradesResponse>(`/trades?${params}`);
    return response.data;
  },

  // Get statistics
  getStats: async (): Promise<StatsResponse> => {
    const response = await api.get<StatsResponse>('/stats');
    return response.data;
  },

  // Chart endpoints
  charts: {
    priceTrend: async (filters: Partial<Filters>): Promise<ChartResponse> => {
      const params = new URLSearchParams();
      if (filters.days) params.append('days', filters.days.toString());
      if (filters.transactionType) params.append('transaction_type', filters.transactionType);
      if (filters.transferMethod) params.append('transfer_method', filters.transferMethod);

      const response = await api.get<ChartResponse>(`/chart/price-trend?${params}`);
      return response.data;
    },

    transactionDistribution: async (days?: number): Promise<ChartResponse> => {
      const params = days ? `?days=${days}` : '';
      const response = await api.get<ChartResponse>(`/chart/transaction-distribution${params}`);
      return response.data;
    },

    transferDistribution: async (days?: number): Promise<ChartResponse> => {
      const params = days ? `?days=${days}` : '';
      const response = await api.get<ChartResponse>(`/chart/transfer-distribution${params}`);
      return response.data;
    },

    volumeByHour: async (days = 7): Promise<ChartResponse> => {
      const response = await api.get<ChartResponse>(`/chart/volume-by-hour?days=${days}`);
      return response.data;
    },

    priceRange: async (days = 7, bins = 10): Promise<ChartResponse> => {
      const response = await api.get<ChartResponse>(`/chart/price-range?days=${days}&bins=${bins}`);
      return response.data;
    },

    buySellComparison: async (days = 7): Promise<ChartResponse> => {
      const response = await api.get<ChartResponse>(`/chart/buy-sell-comparison?days=${days}`);
      return response.data;
    },
  },
};

