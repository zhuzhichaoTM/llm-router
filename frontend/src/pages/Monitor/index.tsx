import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Progress } from 'antd';
import { ReloadOutlined, ArrowUpOutlined, ArrowDownOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { chatApi, routerApi } from '@/api/client';
import type { DailyCost, RouterMetrics } from '@/types';

export default function Monitor() {
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<RouterMetrics | null>(null);
  const [dailyCost, setDailyCost] = useState<DailyCost[]>([]);
  const [recentRequests, setRecentRequests] = useState<any[]>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [metricsData, costData] = await Promise.all([
        routerApi.getMetrics(),
        costApi.getDaily(7),
      ]);

      if (metricsData) setMetrics(metricsData);
      if (costData) setDailyCost(costData);
    } catch (error) {
      console.error('Failed to fetch monitor data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">监控面板</h1>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="路由开关"
              value={metrics?.current_status ? '已启用' : '已禁用'}
              valueStyle={{
                color: metrics?.current_status ? '#52c41a' : '#ff4d4f',
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日请求"
              value={loading ? '---' : recentRequests.length}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="成功请求"
              value={loading ? '---' : (recentRequests.filter((r: any) => !r.error).length)}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="失败请求"
              value={loading ? '---' : (recentRequests.filter((r: any) => r.error).length)}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card
            title="请求统计"
            extra={<Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>}
          >
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">成功率</span>
                  <span className="font-medium text-green-600">
                    {recentRequests.length > 0
                      ? `${((recentRequests.filter((r: any) => !r.error).length / recentRequests.length) * 100).toFixed(1)}%`
                      : '---'}
                  </span>
                </div>
                <Progress
                  percent={recentRequests.length > 0
                    ? Math.round((recentRequests.filter((r: any) => !r.error).length / recentRequests.length) * 100)
                    : 0}
                  strokeColor="#52c41a"
                />
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">平均延迟</span>
                  <span className="font-medium">
                    {metrics?.recent_history?.[0]?.latency_ms ? `${metrics.recent_history[0].latency_ms}ms` : '---'}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Token 使用量（近7天）">
            <div className="h-48">
              <div className="flex items-center justify-center h-full text-gray-400">
                图表组件待实现
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="最近请求记录" className="mb-6">
        <Table
          columns={[
            {
              title: '时间',
              dataIndex: 'timestamp',
              key: 'timestamp',
              render: (ts: number) => new Date(ts).toLocaleString(),
            },
            {
              title: '模型',
              dataIndex: 'model',
              key: 'model',
            },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (status: string) => {
                if (status === 'success') {
                  return <Tag icon={<CheckCircleOutlined />} color="success">成功</Tag>;
                }
                return <Tag icon={<CloseCircleOutlined />} color="error">失败</Tag>;
              },
            },
            {
              title: '延迟',
              dataIndex: 'latency',
              key: 'latency',
              render: (latency: number) => `${latency}ms`,
            },
            {
              title: 'Tokens',
              dataIndex: 'tokens',
              key: 'tokens',
            },
          ]}
          dataSource={recentRequests}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  );
}
