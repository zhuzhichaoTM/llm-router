import React from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, message, Popconfirm, Statistic, Row, Col, Progress } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { providerApi } from '@/api/client';
import type { Provider, ProviderModel, ProviderHealth } from '@/types';

export default function Providers() {
  const [loading, setLoading] = React.useState(false);
  const [providers, setProviders] = React.useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = React.useState<Provider | null>(null);
  const [healthStatus, setHealthStatus] = React.useState<Record<number, ProviderHealth>>({});
  const [modalVisible, setModalVisible] = React.useState(false);
  const [editingProvider, setEditingProvider] = React.useState<Partial<Provider> | null>(null);
  const [form] = Form.useForm();

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const data = await providerApi.list();
      if (data) {
        setProviders(data);
        // Fetch health status for each provider
        for (const provider of data) {
          try {
            const healthData = await providerApi.healthCheck(provider.id);
            if (healthData?.providers) {
              setHealthStatus(prev => ({ ...prev, [provider.id]: healthData.providers[0] }));
            }
          } catch {
            // Skip health check if it fails
          }
        }
      }
    } catch (error: any) {
      message.error('获取 Provider 列表失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchProviders();
  }, []);

  const handleAdd = () => {
    setEditingProvider({ status: 'active', priority: 100, weight: 100 });
    setModalVisible(true);
    form.resetFields();
  };

  const handleEdit = (provider: Provider) => {
    setEditingProvider(provider);
    setModalVisible(true);
    form.setFieldsValue({
      name: provider.name,
      provider_type: provider.provider_type,
      base_url: provider.base_url,
      region: provider.region,
      organization: provider.organization,
      timeout: provider.timeout,
      max_retries: provider.max_retries,
      priority: provider.priority,
      weight: provider.weight,
      status: provider.status,
    });
  };

  const handleDelete = async (id: number) => {
    try {
      message.loading('删除中...', 0);
      await providerApi.delete?.(id);
      message.success('删除成功');
      await fetchProviders();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleHealthCheck = async (id: number) => {
    try {
      const data = await providerApi.healthCheck(id);
      if (data?.providers?.[0]) {
        setHealthStatus(prev => ({ ...prev, [id]: data.providers[0] }));
      }
    } catch (error) {
      message.error('健康检查失败');
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (editingProvider?.id) {
        // Update
        await providerApi.update?.(editingProvider.id, values);
        message.success('更新成功');
      } else {
        // Create
        await providerApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      await fetchProviders();
    } catch (error) {
      message.error('保存失败');
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      active: { color: 'green', text: '正常' },
      inactive: { color: 'default', text: '未激活' },
      unhealthy: { color: 'red', text: '异常' },
    };
    return statusMap[status] || { color: 'default', text: status };
  };

  const columns = [
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
      title: '类型',
      dataIndex: 'provider_type',
      key: 'provider_type',
      render: (type: string) => (
        <Tag color={type === 'openai' ? 'blue' : type === 'anthropic' ? 'orange' : 'default'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const { color, text } = getStatusTag(status);
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      width: 80,
    },
    {
      title: '健康状态',
      key: 'health',
      width: 120,
      render: (_: any, record: Provider) => {
        const health = healthStatus[record.id];
        if (!health) {
          return <Button size="small" icon={<ReloadOutlined />} onClick={() => handleHealthCheck(record.id)} />;
        }
        if (health.is_healthy) {
          return <Tag icon={<CheckCircleOutlined />} color="success">正常</Tag>;
        }
        return (
          <Tag icon={<CloseCircleOutlined />} color="error">
            {health.latency_ms ? `${health.latency_ms}ms` : '异常'}
          </Tag>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: Provider) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个 Provider 吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const expandedRowRender = (record: Provider) => {
    const health = healthStatus[record.id];
    return (
      <div className="p-4">
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic
              title="延迟"
              value={health?.latency_ms || '-'}
              suffix="ms"
              valueStyle={{ color: health?.is_healthy ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={12}>
            <div className="text-gray-500">
              <p>Base URL: {record.base_url}</p>
              {record.region && <p>区域: {record.region}</p>}
              <p>超时: {record.timeout}s</p>
            </div>
          </Col>
        </Row>
      </div>
    );
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Provider 配置</h1>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleAdd}
        >
          添加 Provider
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={providers}
          rowKey="id"
          loading={loading}
          expandable={{
            expandedRowRender,
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingProvider?.id ? '编辑 Provider' : '添加 Provider'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入 Provider 名称' }]}
          >
            <Input placeholder="例如: openai" />
          </Form.Item>

          <Form.Item
            name="provider_type"
            label="类型"
            rules={[{ required: true, message: '请选择 Provider 类型' }]}
          >
            <select className="w-full p-2 border rounded">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="custom">Custom</option>
            </select>
          </Form.Item>

          <Form.Item
            name="base_url"
            label="Base URL"
            rules={[{ required: true, message: '请输入 Base URL' }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item name="region" label="区域">
            <Input placeholder="例如: us-west-1" />
          </Form.Item>

          <Form.Item name="organization" label="组织 ID">
            <Input placeholder="可选的组织 ID" />
          </Form.Item>

          <Form.Item
            name="timeout"
            label="超时时间（秒）"
            rules={[{ required: true, message: '请输入超时时间' }]}
            initialValue={60}
          >
            <Input type="number" />
          </Form.Item>

          <Form.Item
            name="max_retries"
            label="最大重试次数"
            rules={[{ required: true, message: '请输入最大重试次数' }]}
            initialValue={3}
          >
            <Input type="number" />
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            rules={[{ required: true, message: '请输入优先级' }]}
            initialValue={100}
          >
            <Input type="number" />
          </Form.Item>

          <Form.Item
            name="weight"
            label="负载均衡权重"
            rules={[{ required: true, message: '请输入权重' }]}
            initialValue={100}
          >
            <Input type="number" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
