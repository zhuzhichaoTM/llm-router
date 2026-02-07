import React from 'react';
import { Card, Row, Col, DatePicker, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { costApi } from '@/api/client';
import type { DailyCost, ModelCost, CostSummary } from '@/types';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';

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
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">成本分析</h1>
        <Button
          icon={<ReloadOutlined />}
          onClick={fetchData}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {/* Date Range Selector */}
      <Card className="mb-6">
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
        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} sm={12} lg={6}>
            <Card
              title="总成本"
              className="text-center"
            >
              <div className="text-3xl font-bold text-blue-600">
                ${summary.total_cost.toFixed(4)}
              </div>
              <div className="text-sm text-gray-500 mt-2">
                {summary.period}
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card
              title="输入成本"
              className="text-center"
            >
              <div className="text-3xl font-bold text-green-600">
                ${summary.input_cost.toFixed(4)}
              </div>
              <div className="text-sm text-gray-500 mt-2">
                占比 {((summary.input_cost / summary.total_cost) * 100).toFixed(1)}%
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card
              title="输出成本"
              className="text-center"
            >
              <div className="text-3xl font-bold text-orange-600">
                ${summary.output_cost.toFixed(4)}
              </div>
              <div className="text-sm text-gray-500 mt-2">
                占比 {((summary.output_cost / summary.total_cost) * 100).toFixed(1)}%
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card
              title="Token 使用量"
              className="text-center"
            >
              <div className="text-3xl font-bold text-purple-600">
                {summary.total_tokens.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500 mt-2">
                总计
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {/* Daily Cost Chart */}
      <Card title="每日成本趋势" className="mb-6" loading={loading}>
        <div className="h-64">
          {/* Chart component would go here */}
          <div className="flex items-center justify-center h-full text-gray-400">
            图表组件待实现
          </div>
        </div>
      </Card>

      {/* Model Cost Breakdown */}
      <Card title="按模型成本分析" className="mb-6" loading={loading}>
        <div className="h-64">
          {/* Chart component would go here */}
          <div className="flex items-center justify-center h-full text-gray-400">
            图表组件待实现
          </div>
        </div>
      </Card>
    </div>
  );
}
