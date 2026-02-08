/**
 * API client for LLM Router backend
 */
import axios, { AxiosError, AxiosResponse } from 'axios';
import type {
  ApiResponse,
  ChatCompletionRequest,
  ChatCompletionResponse,
  ModelInfo,
  SwitchStatus,
  ToggleRequest,
  RouterMetrics,
  SwitchHistoryEntry,
  RoutingRule,
  DailyCost,
  ModelCost,
  UserCost,
  CostSummary,
  Provider,
  ProviderModel,
  ProviderHealth,
  PerformanceMetrics,
  ErrorLog,
  ErrorSummary,
  AlertRule,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add API key if available
    const apiKey = localStorage.getItem('llm_router_api_key');
    if (apiKey && config.headers) {
      config.headers['Authorization'] = `Bearer ${apiKey}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

/**
 * Set API key for subsequent requests
 */
export const setApiKey = (apiKey: string) => {
  localStorage.setItem('llm_router_api_key', apiKey);
};

export const getApiKey = () => {
  return localStorage.getItem('llm_router_api_key');
};

export const clearApiKey = () => {
  localStorage.removeItem('llm_router_api_key');
};

/**
 * Set admin API key
 */
export const setAdminApiKey = (apiKey: string) => {
  localStorage.setItem('llm_router_admin_api_key', apiKey);
};

export const getAdminApiKey = () => {
  return localStorage.getItem('llm_router_admin_api_key');
};

// Chat API
export const chatApi = {
  completions: async (request: ChatCompletionRequest) => {
    const response = await apiClient.post<ChatCompletionResponse>(
      '/api/v1/chat/completions',
      request
    );
    return response.data;
  },

  listModels: async () => {
    const response = await apiClient.get<ModelInfo[]>(
      '/api/v1/chat/models'
    );
    return response.data;
  },
};

// Router API
export const routerApi = {
  getStatus: async () => {
    const response = await apiClient.get<SwitchStatus>(
      '/api/v1/router/status'
    );
    return response.data;
  },

  toggle: async (request: ToggleRequest) => {
    const response = await apiClient.post<SwitchStatus>(
      '/api/v1/router/toggle',
      request,
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },

  getHistory: async (limit: number = 100) => {
    const response = await apiClient.get<SwitchHistoryEntry[]>(
      `/api/v1/router/history?limit=${limit}`
    );
    return response.data;
  },

  getMetrics: async () => {
    const response = await apiClient.get<RouterMetrics>(
      '/api/v1/router/metrics'
    );
    return response.data;
  },

  listRules: async () => {
    const response = await apiClient.get<{ rules: RoutingRule[]; total: number }>(
      '/api/v1/router/rules'
    );
    return response.data;
  },

  createRule: async (rule: Partial<RoutingRule>) => {
    const response = await apiClient.post<RoutingRule>(
      '/api/v1/router/rules',
      rule,
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },
};

// Cost API
export const costApi = {
  getCurrent: async () => {
    const response = await apiClient.get<{
      daily: { cost: number; tokens: number };
      total: number;
    }>('/api/v1/cost/current');
    return response.data;
  },

  getDaily: async (days: number = 7) => {
    const response = await apiClient.get<DailyCost[]>(
      `/api/v1/cost/daily?days=${days}`
    );
    return response.data;
  },

  getSummary: async (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await apiClient.get<CostSummary>(
      `/api/v1/cost/summary?${params.toString()}`
    );
    return response.data;
  },

  getByModel: async (limit: number = 20) => {
    const response = await apiClient.get<{ models: ModelCost[] }>(
      `/api/v1/cost/by-model?limit=${limit}`
    );
    return response.data;
  },

  getByUser: async (limit: number = 20) => {
    const response = await apiClient.get<{ users: UserCost[] }>(
      `/api/v1/cost/by-user?limit=${limit}`
    );
    return response.data;
  },
};

// Provider API
export const providerApi = {
  list: async () => {
    const response = await apiClient.get<Provider[]>(
      '/api/v1/providers'
    );
    return response.data;
  },

  create: async (provider: Partial<Provider>) => {
    const response = await apiClient.post<Provider>(
      '/api/v1/providers',
      provider,
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },

  get: async (id: number) => {
    const response = await apiClient.get<Provider>(
      `/api/v1/providers/${id}`
    );
    return response.data;
  },

  healthCheck: async (id: number) => {
    const response = await apiClient.post<{ healthy: boolean; providers: ProviderHealth[] }>(
      `/api/v1/providers/${id}/health`,
      {},
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },

  listModels: async (id: number) => {
    const response = await apiClient.get<ProviderModel[]>(
      `/api/v1/providers/${id}/models`
    );
    return response.data;
  },

  createModel: async (id: number, model: Partial<ProviderModel>) => {
    const response = await apiClient.post<ProviderModel>(
      `/api/v1/providers/${id}/models`,
      model,
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },

  update: async (id: number, provider: Partial<Provider>) => {
    const response = await apiClient.put<Provider>(
      `/api/v1/providers/${id}`,
      provider,
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },

  delete: async (id: number) => {
    const response = await apiClient.delete<void>(
      `/api/v1/providers/${id}`,
      {
        headers: {
          'Authorization': `Bearer ${getAdminApiKey()}`,
        },
      }
    );
    return response.data;
  },
};

// Analytics API
export const analyticsApi = {
  getPerformanceMetrics: async (params: { start_date: string; end_date: string }) => {
    const response = await apiClient.get<PerformanceMetrics>(
      `/api/v1/analytics/performance?start_date=${params.start_date}&end_date=${params.end_date}`
    );
    return response.data;
  },

  getErrorLogs: async (params: { start_date: string; end_date: string; limit?: number }) => {
    const queryParams = new URLSearchParams({
      start_date: params.start_date,
      end_date: params.end_date,
    });
    if (params.limit) queryParams.append('limit', params.limit.toString());
    const response = await apiClient.get<ErrorLog[]>(
      `/api/v1/analytics/errors?${queryParams.toString()}`
    );
    return response.data;
  },

  getErrorSummary: async (params: { start_date: string; end_date: string }) => {
    const response = await apiClient.get<ErrorSummary>(
      `/api/v1/analytics/errors/summary?start_date=${params.start_date}&end_date=${params.end_date}`
    );
    return response.data;
  },

  getModelAnalytics: async (params: { start_date: string; end_date: string }) => {
    const response = await apiClient.get<any[]>(
      `/api/v1/analytics/models?start_date=${params.start_date}&end_date=${params.end_date}`
    );
    return response.data;
  },

  getUserAnalytics: async (params: { start_date: string; end_date: string }) => {
    const response = await apiClient.get<any>(
      `/api/v1/analytics/users?start_date=${params.start_date}&end_date=${params.end_date}`
    );
    return response.data;
  },

  getCostAnalytics: async (params: { start_date: string; end_date: string }) => {
    const response = await apiClient.get<any>(
      `/api/v1/analytics/cost?start_date=${params.start_date}&end_date=${params.end_date}`
    );
    return response.data;
  },

  getAlerts: async () => {
    const response = await apiClient.get<AlertRule[]>(
      '/api/v1/analytics/alerts'
    );
    return response.data;
  },
};

export default apiClient;
