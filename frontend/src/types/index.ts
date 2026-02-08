/**
 * Type definitions for LLM Router
 */

// API Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

// Chat
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: Message[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  stop?: string[];
}

export interface Usage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface Choice {
  index: number;
  message: Message;
  finish_reason: string;
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Choice[];
  usage: Usage;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_window: number;
  input_price_per_1k: number;
  output_price_per_1k: number;
}

// Router
export interface SwitchStatus {
  enabled: boolean;
  pending: boolean;
  pending_value: boolean | null;
  scheduled_at: number | null;
  cooldown_until: number | null;
  can_toggle: boolean;
}

export interface ToggleRequest {
  value: boolean;
  reason?: string;
  force?: boolean;
  delay?: number;
}

export interface RouterMetrics {
  current_status: boolean;
  pending_switch: boolean;
  cooldown_remaining: number;
  total_switches: number;
  enabled_count: number;
  disabled_count: number;
  recent_history: SwitchHistoryEntry[];
}

export interface SwitchHistoryEntry {
  old_enabled: string;
  new_enabled: string;
  reason: string;
  triggered_by: string;
  timestamp: number;
}

export interface RoutingRule {
  id: number;
  name: string;
  description?: string;
  condition_type: string;
  condition_value: string;
  min_complexity?: number;
  max_complexity?: number;
  action_type: string;
  action_value: string;
  priority: number;
  is_active: boolean;
  hit_count: number;
  created_at: string;
  updated_at: string;
}

// Cost
export interface DailyCost {
  date: string;
  cost: number;
  tokens: number;
}

export interface ModelCost {
  model_id: string;
  total_cost: number;
  request_count: number;
  total_tokens: number;
}

export interface UserCost {
  user_id: number;
  username: string | null;
  total_cost: number;
  request_count: number;
}

export interface CostSummary {
  period: string;
  total_cost: number;
  input_cost: number;
  output_cost: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  total_requests: number;
}

// Provider
export interface Provider {
  id: number;
  name: string;
  provider_type: 'openai' | 'anthropic' | 'custom';
  api_key: string;
  base_url: string;
  region?: string;
  organization?: string;
  timeout: number;
  max_retries: number;
  status: 'active' | 'inactive' | 'unhealthy';
  priority: number;
  weight: number;
  created_at: string;
  updated_at: string;
}

export interface ProviderModel {
  id: number;
  provider_id: number;
  model_id: string;
  name: string;
  context_window: number;
  input_price_per_1k: number;
  output_price_per_1k: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderHealth {
  provider_id: number;
  provider_name: string;
  is_healthy: boolean;
  latency_ms: number | null;
  error_message: string | null;
}

// Common
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// Analytics
export interface AnalyticsMetric {
  metric_name: string;
  metric_value: number;
  timestamp: string;
  tags?: Record<string, any>;
}

export interface PerformanceMetrics {
  avgResponseTime: number;
  p95ResponseTime: number;
  p99ResponseTime: number;
  errorRate: number;
  qps: number;
  totalRequests: number;
}

export interface ErrorLog {
  id: string;
  request_id: string;
  error_code: string;
  error_message: string;
  error_type: string;
  provider_id?: string;
  model?: string;
  user_id?: string;
  timestamp: string;
}

export interface ErrorSummary {
  total: number;
  byType: Record<string, number>;
}

export interface UserBehavior {
  id: string;
  user_id: string;
  event_type: string;
  event_data: Record<string, any>;
  session_id?: string;
  client_info?: Record<string, any>;
  timestamp: string;
}

export interface AlertRule {
  id: string;
  rule_name: string;
  severity: 'critical' | 'warning' | 'info';
  description: string;
  is_active: boolean;
  triggered_at?: string;
}
