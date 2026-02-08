import React, { useState, useEffect } from 'react';
import { Card, Tabs, Row, Col, Statistic, Table, Select, DatePicker, Button, Space, Tag, Progress, Typography, Alert } from 'antd';
import { ReloadOutlined, RiseOutlined, FallOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { analyticsApi } from '@/api/client';
import type { AnalyticsMetric, ErrorLog, UserBehavior, AlertRule } from '@/types';
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const pageStyle: React.CSSProperties = {
  padding: '24px',
};

const cardStyle: React.CSSProperties = {
  marginBottom: '24px',
};

export default function Analytics() {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('performance');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs(),
  ]);

  // Performance metrics
  const [performanceMetrics, setPerformanceMetrics] = useState({
    avgResponseTime: 0,
    p95ResponseTime: 0,
    p99ResponseTime: 0,
    errorRate: 0,
    qps: 0,
    totalRequests: 0,
  });

  // Error logs
  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([]);
  const [errorSummary, setErrorSummary] = useState({ total: 0, byType: {} as Record<string, number> });

  // Model analytics
  const [modelAnalytics, setModelAnalytics] = useState<any[]>([]);

  // User analytics
  const [userAnalytics, setUserAnalytics] = useState({
    totalUsers: 0,
    activeUsers: 0,
    newUsers: 0,
    topUsers: [] as any[],
  });

  // Cost analytics
  const [costAnalytics, setCostAnalytics] = useState({
    totalCost: 0,
    byModel: [] as any[],
    trend: [] as any[],
  });

  // Alerts
  const [alerts, setAlerts] = useState<AlertRule[]>([]);

  const fetchPerformanceData = async () => {
    setLoading(true);
    try {
      const response = await analyticsApi.getPerformanceMetrics({
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
      });
      setPerformanceMetrics(response);
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchErrorData = async () => {
    setLoading(true);
    try {
      const [logs, summary] = await Promise.all([
        analyticsApi.getErrorLogs({
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
          limit: 50,
        }),
        analyticsApi.getErrorSummary({
          start_date: dateRange[0].format('YYYY-MM-DD'),
          end_date: dateRange[1].format('YYYY-MM-DD'),
        }),
      ]);
      setErrorLogs(logs);
      setErrorSummary(summary);
    } catch (error) {
      console.error('Failed to fetch error data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchModelData = async () => {
    setLoading(true);
    try {
      const response = await analyticsApi.getModelAnalytics({
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
      });
      setModelAnalytics(response);
    } catch (error) {
      console.error('Failed to fetch model analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserData = async () => {
    setLoading(true);
    try {
      const response = await analyticsApi.getUserAnalytics({
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
      });
      setUserAnalytics(response);
    } catch (error) {
      console.error('Failed to fetch user analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCostData = async () => {
    setLoading(true);
    try {
      const response = await analyticsApi.getCostAnalytics({
        start_date: dateRange[0].format('YYYY-MM-DD'),
        end_date: dateRange[1].format('YYYY-MM-DD'),
      });
      setCostAnalytics(response);
    } catch (error) {
      console.error('Failed to fetch cost analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const response = await analyticsApi.getAlerts();
      setAlerts(response);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'performance') fetchPerformanceData();
    else if (activeTab === 'errors') fetchErrorData();
    else if (activeTab === 'models') fetchModelData();
    else if (activeTab === 'users') fetchUserData();
    else if (activeTab === 'cost') fetchCostData();
    else if (activeTab === 'alerts') fetchAlerts();
  }, [activeTab, dateRange]);

  const tabItems = [
    {
      key: 'performance',
      label: '性能监控',
      children: (
        <div>
          {/* Performance Overview */}
          <Row gutter={[16, 16]} style={cardStyle}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="平均响应时间"
                  value={performanceMetrics.avgResponseTime}
                  suffix="ms"
                  valueStyle={{ color: performanceMetrics.avgResponseTime < 1000 ? '#52c41a' : '#ff4d4f' }}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="P95 响应时间"
                  value={performanceMetrics.p95ResponseTime}
                  suffix="ms"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="P99 响应时间"
                  value={performanceMetrics.p99ResponseTime}
                  suffix="ms"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="QPS"
                  value={performanceMetrics.qps}
                  precision={2}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={cardStyle}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="总请求数"
                  value={performanceMetrics.totalRequests}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="错误率"
                  value={performanceMetrics.errorRate * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: performanceMetrics.errorRate < 0.05 ? '#52c41a' : '#ff4d4f' }}
                />
                <Progress
                  percent={Math.round(performanceMetrics.errorRate * 100)}
                  strokeColor={performanceMetrics.errorRate < 0.05 ? '#52c41a' : '#ff4d4f'}
                  showInfo={false}
                />
              </Card>
            </Col>
          </Row>

          {/* Response Time Distribution */}
          <Card title="响应时间分布" style={cardStyle}>
            <Alert
              message="响应时间分布图表"
              description="这里将显示响应时间的分布直方图，展示不同区间的请求占比"
              type="info"
              showIcon
            />
          </Card>

          {/* QPS Trend */}
          <Card title="QPS 趋势" style={cardStyle}>
            <Alert
              message="QPS 趋势图表"
              description="这里将显示 QPS 随时间变化的折线图"
              type="info"
              showIcon
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'errors',
      label: '错误分析',
      children: (
        <div>
          {/* Error Summary */}
          <Row gutter={[16, 16]} style={cardStyle}>
            <Col xs={24} sm={12} lg={8}>
              <Card>
                <Statistic
                  title="总错误数"
                  value={errorSummary.total}
                  valueStyle={{ color: errorSummary.total > 0 ? '#ff4d4f' : '#52c41a' }}
                  prefix={errorSummary.total > 0 ? <WarningOutlined /> : <CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8}>
              <Card title="错误类型分布">
                {Object.entries(errorSummary.byType || {}).map(([type, count]: [string, any]) => (
                  <div key={type} style={{ marginBottom: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <Tag color={type === '5xx' ? 'red' : type === '4xx' ? 'orange' : 'blue'}>{type}</Tag>
                      <span>{count}</span>
                    </div>
                    <Progress
                      percent={Math.round((count / errorSummary.total) * 100)}
                      size="small"
                      showInfo={false}
                    />
                  </div>
                ))}
              </Card>
            </Col>
          </Row>

          {/* Error Logs */}
          <Card title="错误日志" style={cardStyle}>
            <Table
              columns={[
                { title: '时间', dataIndex: 'timestamp', key: 'timestamp', render: (ts: string) => new Date(ts).toLocaleString() },
                { title: '错误类型', dataIndex: 'error_type', key: 'error_type', render: (type: string) => <Tag color="red">{type}</Tag> },
                { title: '错误码', dataIndex: 'error_code', key: 'error_code' },
                { title: '错误信息', dataIndex: 'error_message', key: 'error_message', ellipsis: true },
                { title: '模型', dataIndex: 'model', key: 'model' },
              ]}
              dataSource={errorLogs}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'models',
      label: '模型分析',
      children: (
        <div>
          {/* Model Overview */}
          <Card title="模型使用概览" style={cardStyle}>
            <Alert
              message="模型使用对比图表"
              description="这里将显示各模型的使用量、成本、性能对比图表"
              type="info"
              showIcon
            />
          </Card>

          {/* Model Details */}
          <Card title="模型详情" style={cardStyle}>
            <Table
              columns={[
                { title: '模型', dataIndex: 'model', key: 'model' },
                { title: '请求次数', dataIndex: 'request_count', key: 'request_count', render: (count: number) => count.toLocaleString() },
                { title: '成功次数', dataIndex: 'success_count', key: 'success_count', render: (count: number) => count.toLocaleString() },
                { title: '成功率', dataIndex: 'success_rate', key: 'success_rate', render: (rate: number) => `${(rate * 100).toFixed(2)}%` },
                { title: '平均响应时间', dataIndex: 'avg_latency', key: 'avg_latency', render: (ms: number) => `${ms.toFixed(0)}ms` },
                { title: '总成本', dataIndex: 'total_cost', key: 'total_cost', render: (cost: number) => `$${cost.toFixed(4)}` },
                { title: '总 Tokens', dataIndex: 'total_tokens', key: 'total_tokens', render: (tokens: number) => tokens.toLocaleString() },
              ]}
              dataSource={modelAnalytics}
              rowKey="model"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>

          {/* Model Trend */}
          <Card title="模型使用趋势" style={cardStyle}>
            <Alert
              message="模型使用趋势图表"
              description="这里将显示各模型使用量随时间变化的趋势图"
              type="info"
              showIcon
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'users',
      label: '用户分析',
      children: (
        <div>
          {/* User Overview */}
          <Row gutter={[16, 16]} style={cardStyle}>
            <Col xs={24} sm={12} lg={8}>
              <Card>
                <Statistic
                  title="总用户数"
                  value={userAnalytics.totalUsers}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8}>
              <Card>
                <Statistic
                  title="活跃用户"
                  value={userAnalytics.activeUsers}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8}>
              <Card>
                <Statistic
                  title="新增用户"
                  value={userAnalytics.newUsers}
                  prefix={<FallOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* Top Users */}
          <Card title="活跃用户排行" style={cardStyle}>
            <Table
              columns={[
                { title: '用户 ID', dataIndex: 'user_id', key: 'user_id' },
                { title: '请求次数', dataIndex: 'request_count', key: 'request_count' },
                { title: '总成本', dataIndex: 'total_cost', key: 'total_cost', render: (cost: number) => `$${cost.toFixed(4)}` },
                { title: '最后活跃', dataIndex: 'last_active', key: 'last_active', render: (ts: string) => new Date(ts).toLocaleString() },
              ]}
              dataSource={userAnalytics.topUsers}
              rowKey="user_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>

          {/* User Behavior */}
          <Card title="用户行为分析" style={cardStyle}>
            <Alert
              message="用户行为分析图表"
              description="这里将显示用户活跃时段、使用模式等分析图表"
              type="info"
              showIcon
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'cost',
      label: '成本分析',
      children: (
        <div>
          {/* Cost Overview */}
          <Row gutter={[16, 16]} style={cardStyle}>
            <Col xs={24} sm={12} lg={8}>
              <Card>
                <Statistic
                  title="总成本"
                  value={costAnalytics.totalCost}
                  prefix="$"
                  precision={4}
                  valueStyle={{ color: costAnalytics.totalCost > 100 ? '#fa8c16' : '#52c41a' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Cost by Model */}
          <Card title="各模型成本占比" style={cardStyle}>
            <Alert
              message="成本占比图表"
              description="这里将显示各模型成本占比的饼图"
              type="info"
              showIcon
            />
          </Card>

          {/* Cost Trend */}
          <Card title="成本趋势" style={cardStyle}>
            <Alert
              message="成本趋势图表"
              description="这里将显示成本随时间变化的趋势图"
              type="info"
              showIcon
            />
          </Card>

          {/* Cost Details */}
          <Card title="成本明细" style={cardStyle}>
            <Table
              columns={[
                { title: '模型', dataIndex: 'model', key: 'model' },
                { title: '请求数', dataIndex: 'request_count', key: 'request_count' },
                { title: '输入 Tokens', dataIndex: 'input_tokens', key: 'input_tokens' },
                { title: '输出 Tokens', dataIndex: 'output_tokens', key: 'output_tokens' },
                { title: '输入成本', dataIndex: 'input_cost', key: 'input_cost', render: (cost: number) => `$${cost.toFixed(6)}` },
                { title: '输出成本', dataIndex: 'output_cost', key: 'output_cost', render: (cost: number) => `$${cost.toFixed(6)}` },
                { title: '总成本', dataIndex: 'total_cost', key: 'total_cost', render: (cost: number) => `$${cost.toFixed(6)}` },
              ]}
              dataSource={costAnalytics.byModel}
              rowKey="model"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </div>
      ),
    },
    {
      key: 'alerts',
      label: '告警管理',
      children: (
        <div>
          {/* Active Alerts */}
          <Card title="活跃告警" style={cardStyle}>
            {alerts.filter((a) => a.is_active).length === 0 ? (
              <Alert
                message="无活跃告警"
                description="当前没有活跃的告警"
                type="success"
                showIcon
              />
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                {alerts.filter((a) => a.is_active).map((alert) => (
                  <Alert
                    key={alert.id}
                    message={alert.rule_name}
                    description={alert.description}
                    type={alert.severity === 'critical' ? 'error' : alert.severity === 'warning' ? 'warning' : 'info'}
                    showIcon
                    action={
                      <Button size="small" onClick={() => {/* Handle dismiss */}}>
                        忽略
                      </Button>
                    }
                  />
                ))}
              </Space>
            )}
          </Card>

          {/* Alert History */}
          <Card title="告警历史" style={cardStyle}>
            <Table
              columns={[
                { title: '告警名称', dataIndex: 'rule_name', key: 'rule_name' },
                { title: '严重级别', dataIndex: 'severity', key: 'severity', render: (severity: string) => {
                  const color = severity === 'critical' ? 'red' : severity === 'warning' ? 'orange' : 'blue';
                  return <Tag color={color}>{severity}</Tag>;
                }},
                { title: '状态', dataIndex: 'is_active', key: 'is_active', render: (active: boolean) => (
                  <Tag color={active ? 'red' : 'green'}>{active ? '活跃' : '已恢复'}</Tag>
                )},
                { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', render: (ts: string) => new Date(ts).toLocaleString() },
                { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
              ]}
              dataSource={alerts}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </div>
      ),
    },
  ];

  return (
    <div style={pageStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2}>数据分析</Title>
        <Space>
          <RangePicker
            value={dateRange}
            onChange={(dates: any) => setDateRange(dates)}
            allowClear={false}
          />
          <Button icon={<ReloadOutlined />} onClick={() => {
            if (activeTab === 'performance') fetchPerformanceData();
            else if (activeTab === 'errors') fetchErrorData();
            else if (activeTab === 'models') fetchModelData();
            else if (activeTab === 'users') fetchUserData();
            else if (activeTab === 'cost') fetchCostData();
            else if (activeTab === 'alerts') fetchAlerts();
          }} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />
    </div>
  );
}
