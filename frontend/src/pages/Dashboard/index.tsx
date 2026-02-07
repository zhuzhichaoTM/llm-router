import React from 'react';
import { Card, Row, Col, Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { useDashboardData } from '@/hooks/useDashboardData';
import { StatsSection } from '@/components/StatCard';
import RouterControlPanel from '@/components/RouterControlPanel';
import CostChart from '@/components/CostChart';

export default function Dashboard() {
  const {
    loading,
    switchStatus,
    metrics,
    todayCost,
    totalCost,
  } = useDashboardData();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">仪表盘</h1>

      <Spin spinning={loading} indicator={<LoadingOutlined />}>
        <div className="space-y-6">
          {/* Stats Section */}
          <StatsSection loading={loading} />

          {/* Router Control */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <RouterControlPanel
                status={switchStatus}
                metrics={metrics}
                loading={loading}
              />
            </Col>
            <Col xs={24} lg={12}>
              <Card
                title="快速操作"
                className="hover:shadow-lg"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded">
                    <span className="font-medium">查看成本详情</span>
                    <span className="text-blue-600">→</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded">
                    <span className="font-medium">配置 Provider</span>
                    <span className="text-green-600">→</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-orange-50 rounded">
                    <span className="font-medium">管理路由规则</span>
                    <span className="text-orange-600">→</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-purple-50 rounded">
                    <span className="font-medium">查看监控面板</span>
                    <span className="text-purple-600">→</span>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>

          {/* Cost Charts */}
          {!loading && (
            <CostChart
              dailyData={[]}
              modelData={[]}
              todayCost={todayCost}
              loading={false}
            />
          )}
        </div>
      </Spin>
    </div>
  );
}
