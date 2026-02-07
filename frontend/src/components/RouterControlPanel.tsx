import React from 'react';
import { Card, Button, Switch, Space, Tag, Tooltip } from 'antd';
import { PoweroffOutlined, ThunderboltOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { SwitchStatus, RouterMetrics } from '@/types';

export interface RouterControlPanelProps {
  status: SwitchStatus | null;
  metrics: RouterMetrics | null;
  loading?: boolean;
  onToggle?: (enabled: boolean, reason: string) => Promise<void>;
}

export default function RouterControlPanel({
  status,
  metrics,
  loading,
  onToggle,
}: RouterControlPanelProps) {
  const [toggling, setToggling] = React.useState(false);

  const handleToggle = async () => {
    if (!status?.can_toggle || !onToggle) return;

    setToggling(true);
    try {
      await onToggle(!status.enabled, toggling ? 'Manual toggle' : 'Control panel toggle');
    } finally {
      setToggling(false);
    }
  };

  const getCooldownText = () => {
    if (status?.cooldown_until) {
      const remaining = Math.max(0, status.cooldown_until - Date.now() / 1000);
      if (remaining > 60) {
        return `${Math.floor(remaining / 60)} 分钟`;
      }
      return `${remaining} 秒`;
    }
    return '';
  };

  return (
    <Card
      title="路由开关控制"
      className="mb-6"
      loading={loading}
      extra={
        <Tag color={status?.enabled ? 'green' : 'red'}>
          {status?.enabled ? '已启用' : '已禁用'}
        </Tag>
      }
    >
      <Space direction="vertical" size="large" className="w-full">
        <div className="flex items-center justify-between">
          <Space>
            <span className="text-gray-600">当前状态：</span>
            <Tag
              color={status?.enabled ? 'success' : 'error'}
              icon={status?.enabled ? <CheckCircleOutlined /> : <PoweroffOutlined />}
            >
              {status?.enabled ? '智能路由启用' : '智能路由禁用'}
            </Tag>
          </Space>
          <Tooltip title={!status?.can_toggle ? getCooldownText() : ''}>
            <Button
              type={status?.enabled ? 'primary' : 'default'}
              danger={!status?.enabled}
              icon={status?.enabled ? <PoweroffOutlined /> : <ThunderboltOutlined />}
              onClick={handleToggle}
              loading={toggling}
              disabled={!status?.can_toggle}
            >
              {status?.enabled ? '禁用' : '启用'}
            </Button>
          </Tooltip>
        </div>

        {!status?.can_toggle && (
          <div className="text-center">
            <ClockCircleOutlined className="text-orange-500" />
            <span className="ml-2 text-orange-500">
              冷却中：{getCooldownText()}
            </span>
          </div>
        )}

        {metrics && (
          <div className="bg-gray-50 p-4 rounded">
            <Space direction="vertical" className="w-full">
              <div className="flex justify-between">
                <span className="text-gray-600">总切换次数：</span>
                <span className="font-medium">{metrics.total_switches}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">启用次数：</span>
                <span className="font-medium text-green-600">{metrics.enabled_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">禁用次数：</span>
                <span className="font-medium text-red-600">{metrics.disabled_count}</span>
              </div>
            </Space>
          </div>
        )}
      </Space>
    </Card>
  );
}
