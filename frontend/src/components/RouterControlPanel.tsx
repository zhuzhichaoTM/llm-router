import React from 'react';
import { Card, Tag, Space } from 'antd';
import { CheckCircleOutlined, PoweroffOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { SwitchStatus, RouterMetrics } from '@/types';

const cardContainerStyle: React.CSSProperties = {
  marginBottom: '24px',
};

const fullWidthStyle: React.CSSProperties = {
  width: '100%',
};

const flexBetweenStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};

const labelStyle: React.CSSProperties = {
  color: '#8c8c8c',
};

const metricsContainerStyle: React.CSSProperties = {
  background: '#fafafa',
  padding: '16px',
  borderRadius: '4px',
};

const metricsItemStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
};

const valueStyle: React.CSSProperties = {
  fontWeight: 500,
};

const greenValueStyle: React.CSSProperties = {
  ...valueStyle,
  color: '#52c41a',
};

const redValueStyle: React.CSSProperties = {
  ...valueStyle,
  color: '#ff4d4f',
};

export interface RouterControlPanelProps {
  status: SwitchStatus | null;
  metrics: RouterMetrics | null;
  loading?: boolean;
}

export default function RouterControlPanel({
  status,
  metrics,
  loading,
}: RouterControlPanelProps) {
  return (
    <Card
      title="路由开关状态"
      style={cardContainerStyle}
      loading={loading}
      extra={
        <Tag color={status?.enabled ? 'green' : 'red'}>
          {status?.enabled ? '运行中' : '已停止'}
        </Tag>
      }
    >
      <Space direction="vertical" size="large" style={fullWidthStyle}>
        <div>
          <Space>
            <span style={labelStyle}>当前状态：</span>
            <Tag
              color={status?.enabled ? 'success' : 'error'}
              icon={status?.enabled ? <CheckCircleOutlined /> : <PoweroffOutlined />}
            >
              {status?.enabled ? '智能路由启用' : '智能路由禁用'}
            </Tag>
          </Space>
        </div>

        {metrics && (
          <div style={metricsContainerStyle}>
            <Space direction="vertical" style={fullWidthStyle}>
              <div style={metricsItemStyle}>
                <span style={labelStyle}>总切换次数：</span>
                <span style={valueStyle}>{metrics.total_switches}</span>
              </div>
              <div style={metricsItemStyle}>
                <span style={labelStyle}>启用次数：</span>
                <span style={greenValueStyle}>{metrics.enabled_count}</span>
              </div>
              <div style={metricsItemStyle}>
                <span style={labelStyle}>禁用次数：</span>
                <span style={redValueStyle}>{metrics.disabled_count}</span>
              </div>
            </Space>
          </div>
        )}
      </Space>
    </Card>
  );
}
