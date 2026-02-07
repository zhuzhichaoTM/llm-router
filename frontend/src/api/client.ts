/**
 * API client for LLM Router backend
 */
import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
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
    const response = await apiClient.post<ApiResponse<ChatCompletionResponse>>(
      '/api/v1/chat/completions',
      request
    );
    return response.data;
  },

  listModels: async () => {
    const response = await apiClient.get<ApiResponse<ModelInfo[]>>(
      '/api/v1/chat/models'
    );
    return response.data;
  },
};

// Router API
export const routerApi = {
  getStatus: async () => {
    const response = await apiClient.get<ApiResponse<SwitchStatus>>(
      '/api/v1/router/status'
    );
    return response.data;
  },

  toggle: async (request: ToggleRequest) => {
    const response = await apiClient.post<ApiResponse<SwitchStatus>>(
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
    const response = await apiClient.get<ApiResponse<SwitchHistoryEntry[]>>(
      `/api/v1/router/history?limit=${limit}`
    );
    return response.data;
  },

  getMetrics: async () => {
    const response = await apiClient.get<ApiResponse<RouterMetrics>>(
      '/api/v1/router/metrics'
    );
    return response.data;
  },

  listRules: async () => {
    const response = await apiClient.get<ApiResponse<{ rules: RoutingRule[]; total: number }>>(
      '/api/v1/router/rules'
    );
    return response.data;
  },

  createRule: async (rule: Partial<RoutingRule>) => {
    const response = await apiClient.post<ApiResponse<RoutingRule>>(
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
    const response = await apiClient.get<ApiResponse<{
      daily: { cost: number; tokens: number };
      total: number;
    }>>('/api/v1/cost/current');
    return response.data;
  },

  getDaily: async (days: number = 7) => {
    const response = await apiClient.get<ApiResponse<DailyCost[]>>(
      `/api/v1/cost/daily?days=${days}`
    );
    return response.data;
  },

  getSummary: async (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await apiClient.get<ApiResponse<CostSummary>>(
      `/api/v1/cost/summary?${params.toString()}`
    );
    return response.data;
  },

  getByModel: async (limit: number = 20) => {
    const response = await apiClient.get<ApiResponse<{ models: ModelCost[] }>>(
      `/api/v1/cost/by-model?limit=${limit}`
    );
    return response.data;
  },

  getByUser: async (limit: number = 20) => {
    const response = await apiClient.get<ApiResponse<{ users: UserCost[] }>>(
      `/api/v1/cost/by-user?limit=${limit}`
    );
    return response.data;
  },
};

// Provider API
export const providerApi = {
  list: async () => {
    const response = await apiClient.get<ApiResponse<Provider[]>>(
      '/api/v1/providers'
    );
    return response.data;
  },

  create: async (provider: Partial<Provider>) => {
    const response = await apiClient.post<ApiResponse<Provider>>(
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
    const response = await apiClient.get<ApiResponse<Provider>>(
      `/api/v1/providers/${id}`
    );
    return response.data;
  },

  healthCheck: async (id: number) => {
    const response = await apiClient.post<ApiResponse<{ healthy: boolean; providers: ProviderHealth[] }>>(
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
    const response = await apiClient.get<ApiResponse<ProviderModel[]>>(
      `/api/v1/providers/${id}/models`
    );
    return response.data;
  },

  createModel: async (id: number, model: Partial<ProviderModel>) => {
    const response = await apiClient.post<ApiResponse<ProviderModel>>(
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
};

export default apiClient;
