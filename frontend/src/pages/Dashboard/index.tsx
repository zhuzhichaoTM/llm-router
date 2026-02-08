import React from 'react';
import { Card, Row, Col, Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { useDashboardData } from '@/hooks/useDashboardData';
import { StatsSection } from '@/components/StatCard';
import RouterControlPanel from '@/components/RouterControlPanel';
import CostChart from '@/components/CostChart';

const { Title } = Typography;

export default function Dashboard() {
  const {
    loading,
    switchStatus,
    metrics,
    todayCost,
    totalCost,
  } = useDashboardData();

  const cardStyle: React.CSSProperties = {
    marginBottom: 16,
  };

  const quickActionStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    marginBottom: '8px',
    borderRadius: '4px',
    cursor: 'pointer',
  };

  return (
    <div>
      <Title level={2}>仪表盘</Title>

      <Spin spinning={loading} indicator={<LoadingOutlined />}>
        <div>
          {/* Stats Section */}
          <div style={cardStyle}>
            <StatsSection loading={loading} />
          </div>

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
              <Card title="快速操作" style={cardStyle}>
                <a href="/cost" style={{ textDecoration: 'none' }}>
                  <div style={{ background: '#e6f7ff', ...quickActionStyle }}>
                    <span>查看成本详情</span>
                    <span style={{ color: '#1890ff' }}>→</span>
                  </div>
                </a>
                <a href="/providers" style={{ textDecoration: 'none' }}>
                  <div style={{ background: '#f6ffed', ...quickActionStyle }}>
                    <span>配置 Provider</span>
                    <span style={{ color: '#52c41a' }}>→</span>
                  </div>
                </a>
                <a href="/routing" style={{ textDecoration: 'none' }}>
                  <div style={{ background: '#fff7e6', ...quickActionStyle }}>
                    <span>管理路由规则</span>
                    <span style={{ color: '#fa8c16' }}>→</span>
                  </div>
                </a>
                <a href="/monitor" style={{ textDecoration: 'none' }}>
                  <div style={{ background: '#f9f0ff', ...quickActionStyle, marginBottom: 0 }}>
                    <span>查看监控面板</span>
                    <span style={{ color: '#722ed1' }}>→</span>
                  </div>
                </a>
              </Card>
            </Col>
          </Row>

          {/* Cost Charts */}
          {!loading && (
            <div style={cardStyle}>
              <CostChart
                dailyData={[]}
                modelData={[]}
                todayCost={todayCost || 0}
                loading={false}
              />
            </div>
          )}
        </div>
      </Spin>
    </div>
  );
}
