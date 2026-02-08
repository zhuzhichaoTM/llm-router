import React from 'react';
import type { DailyCost, ModelCost } from '@/types';
import { Col, Row, Progress } from 'antd';
import { Pie, Column, Line } from '@ant-design/charts';

const headingStyle: React.CSSProperties = {
  fontSize: '16px',
  fontWeight: 500,
  marginBottom: '16px',
};

const centerStyle: React.CSSProperties = {
  textAlign: 'center',
  padding: '32px 0',
};

const costValueStyle: React.CSSProperties = {
  fontSize: '36px',
  fontWeight: 'bold',
  color: '#1890ff',
};

const progressStyle: React.CSSProperties = {
  marginTop: '16px',
};

export interface CostChartProps {
  dailyData: DailyCost[];
  modelData: ModelCost[];
  todayCost: number;
  loading?: boolean;
}

export default function CostChart({ dailyData, modelData, todayCost, loading }: CostChartProps) {
  const dailyChartData = React.useMemo(() => {
    return (dailyData || []).map(item => ({
      date: item.date,
      value: item.cost,
      tokens: item.tokens,
    }));
  }, [dailyData]);

  const modelChartData = React.useMemo(() => {
    return (modelData || []).map(item => ({
      name: item.model_id,
      value: item.total_cost,
    }));
  }, [modelData]);

  const pieData = React.useMemo(() => {
    return (modelData || []).slice(0, 6).map(item => ({
      name: item.model_id,
      value: item.total_cost,
    }));
  }, [modelData]);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={12}>
        <h3 style={headingStyle}>成本趋势（近7天）</h3>
        <Line
          height={300}
          data={dailyChartData}
          xField="date"
          yField="value"
          loading={loading}
          color={['#1890ff']}
          smooth
        />
      </Col>

      <Col xs={24} lg={12}>
        <h3 style={headingStyle}>模型成本分布</h3>
        <Pie
          height={300}
          data={pieData}
          angleField="value"
          colorField="name"
          innerRadius={0.5}
          outerRadius={0.8}
          label={{
            type: 'outer',
            content: '{percentage}',
          }}
          style={{
            legend: {
              position: 'right',
            },
          }}
          loading={loading}
        />
      </Col>

      <Col xs={24}>
        <h3 style={headingStyle}>模型成本详情</h3>
        <Column
          xField="name"
          yField="value"
          data={modelChartData}
          height={300}
          loading={loading}
          color="#52c41a"
        />
      </Col>

      <Col xs={24} lg={12}>
        <h3 style={headingStyle}>今日成本</h3>
        <div style={centerStyle}>
          <div style={costValueStyle}>
            ${todayCost.toFixed(4)}
          </div>
          <Progress
            percent={Math.min(todayCost / 100 * 100, 100)}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            style={progressStyle}
          />
        </div>
      </Col>
    </Row>
  );
}
