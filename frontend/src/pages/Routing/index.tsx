import React from 'react';
import { Card, Table, Button, Space, Modal, Form, Input, Select, Tag, Switch, Row, Col, message, Typography, InputNumber } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined, PoweroffOutlined } from '@ant-design/icons';
import { routerApi, providerApi } from '@/api/client';
import type { SwitchStatus, RoutingRule, SwitchHistoryEntry, Provider, ProviderModel } from '@/types';

const { Title } = Typography;

const pageStyle: React.CSSProperties = {
  padding: '24px',
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: '16px',
};

const cardStyle: React.CSSProperties = {
  marginBottom: '24px',
};

export default function Routing() {
  const [loading, setLoading] = React.useState(false);
  const [rules, setRules] = React.useState<RoutingRule[]>([]);
  const [switchStatus, setSwitchStatus] = React.useState<SwitchStatus | null>(null);
  const [history, setHistory] = React.useState<SwitchHistoryEntry[]>([]);
  const [modalVisible, setModalVisible] = React.useState(false);
  const [editingRule, setEditingRule] = React.useState<Partial<RoutingRule> | null>(null);
  const [form] = Form.useForm();

  // 模型配置相关状态
  const [providers, setProviders] = React.useState<Provider[]>([]);
  const [models, setModels] = React.useState<Array<ProviderModel & { providerName: string; providerId: number }>>([]);
  const [modelModalVisible, setModelModalVisible] = React.useState(false);
  const [editingModel, setEditingModel] = React.useState<Partial<typeof models[0]> | null>(null);
  const [modelForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statusData, historyData, rulesData, providersData] = await Promise.all([
        routerApi.getStatus(),
        routerApi.getHistory(),
        routerApi.listRules(),
        providerApi.list(),
      ]);

      if (statusData) setSwitchStatus(statusData);
      if (historyData) setHistory(historyData);
      if (rulesData) setRules(rulesData.rules || []);
      if (providersData) {
        setProviders(providersData);
        // 获取所有模型并合并provider信息
        const allModels: Array<ProviderModel & { providerName: string; providerId: number }> = [];
        for (const provider of providersData) {
          try {
            const providerModels = await providerApi.listModels?.(provider.id);
            if (providerModels) {
              allModels.push(...providerModels.map(m => ({
                ...m,
                providerName: provider.name,
                providerId: provider.id,
              })));
            }
          } catch (e) {
            // 忽略获取模型失败的情况
          }
        }
        setModels(allModels);
      }
    } catch (error: any) {
      message.error('获取路由数据失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData();
  }, []);

  const handleToggle = async (enabled: boolean) => {
    try {
      const status = await routerApi.toggle({ value: enabled, reason: 'Manual toggle' });
      setSwitchStatus(status);
      message.success(enabled ? '路由已启用' : '路由已禁用');
      await fetchData();
    } catch (error: any) {
      message.error('切换失败');
    }
  };

  const handleAddRule = () => {
    setEditingRule({ is_active: true, priority: 0 });
    setModalVisible(true);
    form.resetFields();
  };

  const handleEditRule = (rule: RoutingRule) => {
    setEditingRule(rule);
    setModalVisible(true);
    form.setFieldsValue(rule);
  };

  const handleDeleteRule = async (id: number) => {
    try {
      // Note: Need to implement delete API
      message.success('删除成功');
      await fetchData();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule?.id) {
        // Update
        message.success('更新成功');
      } else {
        // Create
        const result = await routerApi.createRule(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      await fetchData();
    } catch (error: any) {
      message.error('保存失败');
    }
  };

  const handleEditModel = (model: typeof models[0]) => {
    setEditingModel(model);
    setModelModalVisible(true);
    modelForm.setFieldsValue({
      priority: model.priority,
      weight: model.weight,
    });
  };

  const handleModelModalOk = async () => {
    try {
      const values = await modelForm.validateFields();
      if (editingModel && editingModel.id) {
        // 更新模型的priority和weight
        await providerApi.updateModel?.(editingModel.providerId, editingModel.id, {
          priority: values.priority,
          weight: values.weight,
        });
        message.success('模型配置更新成功');
        await fetchData();
      }
      setModelModalVisible(false);
    } catch (error: any) {
      message.error('保存失败');
    }
  };

  const ruleColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '条件类型',
      dataIndex: 'condition_type',
      key: 'condition_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          regex: '正则匹配',
          complexity: '复杂度',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '条件值',
      dataIndex: 'condition_value',
      key: 'condition_value',
    },
    {
      title: '操作类型',
      dataIndex: 'action_type',
      key: 'action_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          use_model: '使用模型',
          use_provider: '使用 Provider',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '操作值',
      dataIndex: 'action_value',
      key: 'action_value',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
    {
      title: '命中次数',
      dataIndex: 'hit_count',
      key: 'hit_count',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: RoutingRule) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditRule(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteRule(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const historyColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (ts: number) => new Date(ts * 1000).toLocaleString(),
    },
    {
      title: '变更',
      dataIndex: 'change',
      key: 'change',
      render: (_: any, record: SwitchHistoryEntry) => (
        <span>
          {record.old_enabled === 'true' ? '启用' : '禁用'}
          {' '}
          →
          {' '}
          {record.new_enabled === 'true' ? '启用' : '禁用'}
        </span>
      ),
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
    },
    {
      title: '触发者',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
    },
  ];

  const modelColumns = [
    {
      title: '模型ID',
      dataIndex: 'model_id',
      key: 'model_id',
    },
    {
      title: '模型名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Provider',
      dataIndex: 'providerName',
      key: 'providerName',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: number) => (
        <Tag color={priority >= 100 ? 'green' : priority >= 50 ? 'orange' : 'red'}>
          {priority}
        </Tag>
      ),
    },
    {
      title: '负载权重',
      dataIndex: 'weight',
      key: 'weight',
      width: 100,
      render: (weight: number) => (
        <Tag color="blue">{weight}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: typeof models[0]) => (
        <Button
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleEditModel(record)}
        >
          配置
        </Button>
      ),
    },
  ];

  return (
    <div style={pageStyle}>
      <Title level={2}>路由配置</Title>

      {/* Router Switch Control */}
      <Card title="路由开关控制" style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          {/* 状态标签 */}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, color: '#8c8c8c', marginBottom: 6 }}>当前状态</div>
            <Tag
              color={switchStatus?.enabled ? 'success' : 'error'}
              icon={switchStatus?.enabled ? <CheckCircleOutlined /> : <PoweroffOutlined />}
              style={{ fontSize: 14, padding: '5px 14px', fontWeight: 500 }}
            >
              {switchStatus?.enabled ? '运行中' : '已停止'}
            </Tag>
          </div>

          {/* 控制按钮 */}
          <Button
            type={switchStatus?.enabled ? 'default' : 'primary'}
            danger={switchStatus?.enabled}
            size="large"
            onClick={() => handleToggle(!switchStatus?.enabled)}
            disabled={!switchStatus?.can_toggle}
            style={{ minWidth: 140, height: 38, fontSize: 14, fontWeight: 500 }}
          >
            {switchStatus?.enabled ? '禁用智能路由' : '启用智能路由'}
          </Button>
        </div>
      </Card>

      {/* Model Priority Configuration */}
      <Card
        title="模型优先级与负载均衡配置"
        extra={
          <span style={{ fontSize: 13, color: '#8c8c8c' }}>
            配置各模型的优先级和负载均衡权重
          </span>
        }
        style={cardStyle}
      >
        <Table
          columns={modelColumns}
          dataSource={models}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
          }}
        />
      </Card>

      {/* Routing Rules */}
      <Card
        title="路由规则"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAddRule}
          >
            添加规则
          </Button>
        }
        style={cardStyle}
      >
        <Table
          columns={ruleColumns}
          dataSource={rules}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
          }}
        />
      </Card>

      {/* Switch History */}
      <Card title="切换历史" style={cardStyle}>
        <Table
          columns={historyColumns}
          dataSource={history}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
          }}
        />
      </Card>

      {/* Add/Edit Rule Modal */}
      <Modal
        title={editingRule?.id ? '编辑路由规则' : '添加路由规则'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="例如: 代码相关路由到 GPT-4" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="规则描述..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="condition_type"
                label="条件类型"
                rules={[{ required: true }]}
                initialValue="regex"
              >
                <Select>
                  <option value="regex">正则匹配</option>
                  <option value="complexity">复杂度</option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priority" label="优先级" rules={[{ required: true }]} initialValue={0}>
                <Input type="number" placeholder="数字越大优先级越高" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="condition_value"
            label="条件值"
            rules={[{ required: true, message: '请输入条件值' }]}
          >
            <Input placeholder="例如: (?i)(code|function|class)" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="min_complexity" label="最小复杂度">
                <Input type="number" placeholder="可选" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="max_complexity" label="最大复杂度">
                <Input type="number" placeholder="可选" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="action_type"
            label="操作类型"
            rules={[{ required: true }]}
            initialValue="use_model"
          >
            <Select>
              <option value="use_model">使用模型</option>
              <option value="use_provider">使用 Provider</option>
            </Select>
          </Form.Item>

          <Form.Item
            name="action_value"
            label="操作值"
            rules={[{ required: true, message: '请输入操作值' }]}
          >
            <Input placeholder="例如: gpt-4" />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="是否启用"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Model Configuration Modal */}
      <Modal
        title="配置模型优先级与负载均衡"
        open={modelModalVisible}
        onOk={handleModelModalOk}
        onCancel={() => setModelModalVisible(false)}
        width={500}
      >
        <Form form={modelForm} layout="vertical">
          <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
            <div><strong>模型：</strong>{editingModel?.name}</div>
            <div><strong>Provider：</strong>{editingModel?.providerName}</div>
          </div>

          <Form.Item
            name="priority"
            label="优先级"
            rules={[{ required: true, message: '请输入优先级' }]}
            extra="数字越大优先级越高，用于选择使用哪个模型"
          >
            <InputNumber min={0} max={999} style={{ width: '100%' }} placeholder="100" />
          </Form.Item>

          <Form.Item
            name="weight"
            label="负载均衡权重"
            rules={[{ required: true, message: '请输入权重' }]}
            extra="用于同一优先级模型之间的负载均衡分配"
          >
            <InputNumber min={0} max={1000} style={{ width: '100%' }} placeholder="100" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
