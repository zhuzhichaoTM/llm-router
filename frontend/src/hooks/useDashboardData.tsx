import { useState, useEffect } from 'react';
import { routerApi, costApi, providerApi } from '@/api/client';
import type {
  SwitchStatus,
  RouterMetrics,
  RoutingRule,
  DailyCost,
  ModelCost,
  UserCost,
  Provider,
  ModelInfo,
} from '@/types';

export function useDashboardData() {
  const [loading, setLoading] = useState(false);
  const [switchStatus, setSwitchStatus] = useState<SwitchStatus | null>(null);
  const [metrics, setMetrics] = useState<RouterMetrics | null>(null);
  const [todayCost, setTodayCost] = useState(0);
  const [totalCost, setTotalCost] = useState(0);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [status, metricsData, dailyData, providerList, modelList] = await Promise.all([
        routerApi.getStatus(),
        routerApi.getMetrics(),
        costApi.getCurrent(),
        providerApi.list(),
        chatApi.listModels(),
      ]);

      if (status) setSwitchStatus(status);
      if (metricsData) setMetrics(metricsData);
      if (dailyData) {
        setTodayCost(dailyData.daily?.cost || 0);
        setTotalCost(dailyData.total || 0);
      }
      if (providerList) setProviders(providerList);
      if (modelList) setModels(modelList);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return {
    loading,
    switchStatus,
    metrics,
    todayCost,
    totalCost,
    providers,
    models,
    refresh: fetchData,
  };
}
