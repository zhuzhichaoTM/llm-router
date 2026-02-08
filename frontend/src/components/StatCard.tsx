import React from 'react';
import { Card, Statistic, Row, Col } from 'antd';
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
  trend?: 'up' | 'down' | 'flat';
  loading?: boolean;
}

const cardStyle: React.CSSProperties = {
  transition: 'box-shadow 0.3s',
};

const cardHoverStyle: React.CSSProperties = {
  ...cardStyle,
  boxShadow: '0 1px 2px 0 rgba(0,0,0,0.03), 0 1px 6px -1px rgba(0,0,0,0.02), 0 2px 4px 0 rgba(0,0,0,0.02)',
};

const trendStyle: React.CSSProperties = {
  marginTop: '8px',
};

const trendUpStyle: React.CSSProperties = {
  color: '#52c41a',
};

const trendDownStyle: React.CSSProperties = {
  color: '#ff4d4f',
};

const trendFlatStyle: React.CSSProperties = {
  color: '#999',
};

const labelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  marginLeft: '4px',
};

export default function StatCard({
  title,
  value,
  prefix,
  suffix,
  color = '#1890ff',
  trend,
  loading,
}: StatCardProps) {
  const [hovered, setHovered] = React.useState(false);

  return (
    <Card
      loading={loading}
      style={{ ...cardStyle, boxShadow: hovered ? cardHoverStyle.boxShadow : cardStyle.boxShadow || 'none' }}
      bodyStyle={{ padding: '24px' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Statistic
        title={<span style={{ fontSize: 14, color: '#8c8c8c' }}>{title}</span>}
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ color }}
      />
      {trend && (
        <div style={trendStyle}>
          {trend === 'up' && <span style={trendUpStyle}>↑</span>}
          {trend === 'down' && <span style={trendDownStyle}>↓</span>}
          {trend === 'flat' && <span style={trendFlatStyle}>-</span>}
          <span style={labelStyle}>较昨日</span>
        </div>
      )}
    </Card>
  );
}

export interface StatsSectionProps {
  loading?: boolean;
}

const sectionStyle: React.CSSProperties = {
  marginBottom: '24px',
};

export function StatsSection({ loading }: StatsSectionProps) {
  return (
    <Row gutter={[16, 16]} style={sectionStyle}>
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
