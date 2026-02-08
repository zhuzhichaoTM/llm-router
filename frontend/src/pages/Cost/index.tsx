import React from 'react';
import { Card, Row, Col, DatePicker, Button, Statistic, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { costApi } from '@/api/client';
import type { DailyCost, ModelCost, CostSummary } from '@/types';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import CostChart from '@/components/CostChart';

const { Title } = Typography;

const pageStyle: React.CSSProperties = {
  padding: '24px',
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '24px',
};

const cardStyle: React.CSSProperties = {
  marginBottom: '24px',
};

const chartStyle: React.CSSProperties = {
  height: '300px',
};

const emptyStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  color: '#999',
};

export default function Cost() {
  const [loading, setLoading] = React.useState(false);
  const [startDate, setStartDate] = React.useState<Dayjs>(dayjs().subtract(30, 'day'));
  const [endDate, setEndDate] = React.useState<Dayjs>(dayjs());
  const [dailyData, setDailyData] = React.useState<DailyCost[]>([]);
  const [modelData, setModelData] = React.useState<ModelCost[]>([]);
  const [summary, setSummary] = React.useState<CostSummary | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [daily, modelData, summaryData] = await Promise.all([
        costApi.getDaily(30),
        costApi.getByModel(10),
        costApi.getSummary(
          startDate.format('YYYY-MM-DD'),
          endDate.format('YYYY-MM-DD'),
        ),
      ]);

      if (daily) setDailyData(daily);
      if (modelData) setModelData(modelData.models || []);
      if (summaryData) setSummary(summaryData);
    } catch (error) {
      console.error('Failed to fetch cost data:', error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData();
  }, [startDate, endDate]);

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <Title level={2}>成本分析</Title>
        <Button
          icon={<ReloadOutlined />}
          onClick={fetchData}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {/* Date Range Selector */}
      <Card style={cardStyle}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <DatePicker.RangePicker
              value={[startDate, endDate]}
              onChange={(dates: any) => {
                if (dates && dates[0] && dates[1]) {
                  setStartDate(dates[0]);
                  setEndDate(dates[1]);
                }
              }}
              format="YYYY-MM-DD"
            />
          </Col>
        </Row>
      </Card>

      {/* Cost Summary */}
      {summary && (
        <Row gutter={[16, 16]} style={cardStyle}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="总成本"
                value={summary.total_cost}
                precision={4}
                prefix="$"
                valueStyle={{ color: '#3b82f6' }}
              />
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
                {summary.period}
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="输入成本"
                value={summary.input_cost}
                precision={4}
                prefix="$"
                valueStyle={{ color: '#10b981' }}
              />
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
                占比 {((summary.input_cost / summary.total_cost) * 100).toFixed(1)}%
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="输出成本"
                value={summary.output_cost}
                precision={4}
                prefix="$"
                valueStyle={{ color: '#f97316' }}
              />
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
                占比 {((summary.output_cost / summary.total_cost) * 100).toFixed(1)}%
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Token 使用量"
                value={summary.total_tokens}
                valueStyle={{ color: '#8b5cf6' }}
              />
              <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
                总计
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {/* Daily Cost Chart */}
      <Card title="每日成本趋势" style={cardStyle} loading={loading}>
        <div style={chartStyle}>
          {dailyData.length > 0 ? (
            <CostChart
              data={dailyData.map((d) => ({
                date: new Date(d.date).toLocaleDateString('zh-CN'),
                总成本: d.total_cost,
                输入成本: d.input_cost,
                输出成本: d.output_cost,
              }))}
              xAxisKey="date"
              lines={[
                { dataKey: '总成本', stroke: '#3b82f6', name: '总成本' },
                { dataKey: '输入成本', stroke: '#10b981', name: '输入成本' },
                { dataKey: '输出成本', stroke: '#f97316', name: '输出成本' },
              ]}
            />
          ) : (
            <div style={emptyStyle}>暂无数据</div>
          )}
        </div>
      </Card>

      {/* Model Cost Breakdown */}
      <Card title="按模型成本分析" style={cardStyle} loading={loading}>
        <div style={chartStyle}>
          {modelData.length > 0 ? (
            <CostChart
              data={modelData.map((m) => ({
                模型: m.model_name,
                成本: m.total_cost,
              }))}
              xAxisKey="模型"
              bars={[
                { dataKey: '成本', fill: '#8b5cf6', name: '成本' },
              ]}
            />
          ) : (
            <div style={emptyStyle}>暂无数据</div>
          )}
        </div>
      </Card>
    </div>
  );
}
