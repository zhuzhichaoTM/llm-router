import React from 'react';
import { Card, Statistic, Row, Col, Space } from 'antd';
import {
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';

export interface StatCardProps {
  title: string;
  value: string | number;
  prefix?: React.ReactNode;
  suffix?: string;
  color?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'flat';
  loading?: boolean;
}

export default function StatCard({
  title,
  value,
  prefix,
  suffix,
  color = '#1890ff',
  icon,
  trend,
  loading,
}: StatCardProps) {
  return (
    <Card
      loading={loading}
      className="hover:shadow-lg transition-shadow"
      bodyStyle={{ padding: '24px' }}
    >
      <Statistic
        title={title}
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ color }}
        titleStyle={{ fontSize: 14, color: '#8c8c8c' }}
      />
      {trend && (
        <div className="mt-2">
          {trend === 'up' && <span className="text-green-500">↑</span>}
          {trend === 'down' && <span className="text-red-500">↓</span>}
          {trend === 'flat' && <span className="text-gray-400">-</span>}
          <span className="text-xs text-gray-500 ml-1">较昨日</span>
        </div>
      )}
    </Card>
  );
}

export interface StatsSectionProps {
  loading?: boolean;
}

export function StatsSection({ loading }: StatsSectionProps) {
  return (
    <Row gutter={[16, 16]} className="mb-6">
      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="活跃会话"
          value={loading ? '---' : 128}
          icon={<ThunderboltOutlined />}
          color="#1890ff"
          loading={loading}
        />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="平均响应时间"
          value={loading ? '---' : 156}
          suffix="ms"
          icon={<ClockCircleOutlined />}
          color="#52c41a"
          loading={loading}
        />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="路由准确率"
          value={loading ? '---' : '98.5'}
          suffix="%"
          icon={<CheckCircleOutlined />}
          color="#722ed1"
          loading={loading}
        />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <StatCard
          title="系统健康度"
          value={loading ? '---' : 99.9}
          suffix="%"
          icon={<WarningOutlined />}
          color="#faad14"
          loading={loading}
        />
      </Col>
    </Row>
  );
}
