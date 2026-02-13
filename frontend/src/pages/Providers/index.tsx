import React from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, message, Popconfirm, Statistic, Row, Col, Select, Typography } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { providerApi } from '@/api/client';
import type { Provider, ProviderModel, ProviderHealth } from '@/types';

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

const detailStyle: React.CSSProperties = {
  color: '#999',
};

export default function Providers() {
  const [loading, setLoading] = React.useState(false);
  const [providers, setProviders] = React.useState<Provider[]>([]);
  const [providerModels, setProviderModels] = React.useState<Record<number, ProviderModel[]>>({});
  const [healthStatus, setHealthStatus] = React.useState<Record<number, ProviderHealth>>({});
  const [modalVisible, setModalVisible] = React.useState(false);
  const [editingProvider, setEditingProvider] = React.useState<Partial<Provider> | null>(null);
  const [form] = Form.useForm();
  const [verifyingIds, setVerifyingIds] = React.useState<Record<number, boolean>>({});

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const data = await providerApi.list();
      if (data) {
        setProviders(data);
        // Fetch models for each provider
        const modelsData: Record<number, ProviderModel[]> = {};
        for (const provider of data) {
          try {
            const models = await providerApi.listModels?.(provider.id);
            if (models) {
              modelsData[provider.id] = models;
            }
          } catch (error) {
            console.error(`Failed to fetch models for provider ${provider.id}:`, error);
            modelsData[provider.id] = [];
          }
        }
        setProviderModels(modelsData);
      }
    } catch (error: any) {
      let errorMsg = '获取模型供应商列表失败';
      let suggestion = '请刷新页面重试';

      if (error?.response?.status === 401) {
        errorMsg = '权限验证失败';
        suggestion = '请检查 API Key 是否正确配置';
      } else if (error?.response?.status === 403) {
        errorMsg = '权限不足';
        suggestion = '需要管理员权限才能访问';
      } else if (error?.message?.includes('Network Error')) {
        errorMsg = '网络连接失败';
        suggestion = '请检查网络连接或后端服务是否运行';
      } else if (error?.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      }

      message.error({
        content: (
          <div>
            <div>{errorMsg}</div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
              {suggestion}
            </div>
          </div>
        ),
        duration: 5,
      });
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchProviders();
  }, []);

  const handleAdd = () => {
    setEditingProvider({ status: 'active' });
    setModalVisible(true);
    form.resetFields();
  };

  const handleEdit = async (provider: Provider) => {
    setEditingProvider(provider);
    setModalVisible(true);
    form.setFieldsValue({
      name: provider.name,
      provider_type: provider.provider_type,
      api_key: undefined, // Don't preload API key for security
      base_url: provider.base_url,
      region: provider.region,
      organization: provider.organization,
      timeout: provider.timeout,
      max_retries: provider.max_retries,
      status: provider.status,
      // Preload model_ids as slash-separated string
      model_ids: providerModels[provider.id]?.map(m => m.model_id).join(' / ') || '',
    });
  };

  const handleDelete = async (id: number) => {
    try {
      const hideLoading = message.loading('删除中...', 0);
      await providerApi.delete?.(id);
      hideLoading();
      message.success('删除成功');
      await fetchProviders();
    } catch (error: any) {
      let errorMsg = '删除失败';
      let suggestion = '请稍后重试';

      if (error?.response?.status === 404) {
        errorMsg = '供应商不存在';
        suggestion = '该供应商可能已被删除，请刷新列表';
      } else if (error?.response?.status === 403) {
        errorMsg = '权限不足';
        suggestion = '需要管理员权限才能删除';
      } else if (error?.response?.status === 400) {
        if (error?.response?.data?.detail?.includes('foreign key')) {
          errorMsg = '无法删除';
          suggestion = '该供应商有关联的模型数据，请先删除关联数据';
        } else {
          errorMsg = error.response.data.detail || '请求参数错误';
          suggestion = '请检查输入数据';
        }
      } else if (error?.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error?.message?.includes('Network Error')) {
        errorMsg = '网络连接失败';
        suggestion = '请检查网络连接';
      }

      message.error({
        content: (
          <div>
            <div>{errorMsg}</div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
              {suggestion}
            </div>
          </div>
        ),
        duration: 5,
      });
    }
  };

  const handleHealthCheck = async (id: number) => {
    try {
      const data = await providerApi.healthCheck(id);
      if (data?.providers?.[0]) {
        setHealthStatus(prev => ({ ...prev, [id]: data.providers[0] }));
      }
    } catch (error: any) {
      let errorMsg = '健康检查失败';
      let suggestion = '请检查供应商配置是否正确';

      if (error?.response?.status === 404) {
        errorMsg = '供应商不存在';
        suggestion = '该供应商可能已被删除，请刷新列表';
      } else if (error?.response?.status === 403) {
        errorMsg = '权限不足';
        suggestion = '需要管理员权限';
      } else if (error?.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error?.message?.includes('Network Error')) {
        errorMsg = '网络连接失败';
        suggestion = '请检查网络连接';
      }

      message.error({
        content: (
          <div>
            <div>{errorMsg}</div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
              {suggestion}
            </div>
          </div>
        ),
        duration: 5,
      });
    }
  };

  const handleVerify = async (id: number, name: string) => {
    try {
      setVerifyingIds(prev => ({ ...prev, [id]: true }));
      message.loading({ content: `正在验证模型供应商 ${name}...`, key: `verify_${id}` });

      const data = await providerApi.healthCheck(id);

      if (data?.providers?.[0]) {
        setHealthStatus(prev => ({ ...prev, [id]: data.providers[0] }));

        if (data.providers[0].is_healthy) {
          message.success({
            content: `模型供应商 ${name} 验证成功！延迟: ${data.providers[0].latency_ms || 0}ms`,
            key: `verify_${id}`,
            duration: 3,
          });
        } else {
          message.error({
            content: `模型供应商 ${name} 验证失败：${data.providers[0].error_message || '连接异常'}`,
            key: `verify_${id}`,
            duration: 5,
          });
        }
      } else {
        message.error({
          content: `模型供应商 ${name} 验证失败：无法获取健康状态`,
          key: `verify_${id}`,
          duration: 3,
        });
      }
    } catch (error: any) {
      message.error({
        content: `模型供应商验证失败：${error?.message || '网络异常'}`,
        key: `verify_${id}`,
        duration: 3,
      });
    } finally {
      setVerifyingIds(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();

      // Extract model_ids from form values
      const { model_ids, api_key, ...providerData } = values;

      let providerId: number;

      if (editingProvider?.id) {
        // Update existing provider
        // Only include api_key if user provided a new value
        const updateData = api_key ? { ...providerData, api_key } : providerData;
        await providerApi.update?.(editingProvider.id, updateData);
        providerId = editingProvider.id;

        // Delete all existing models for this provider
        const existingModels = providerModels[editingProvider.id] || [];
        for (const model of existingModels) {
          try {
            await providerApi.deleteModel?.(editingProvider.id, model.id);
          } catch (error) {
            console.error(`Failed to delete model ${model.model_id}:`, error);
          }
        }

        message.success('更新成功');
      } else {
        // Create new provider (api_key is required)
        const newProvider = await providerApi.create({ ...providerData, api_key });
        providerId = newProvider.id;
        message.success('创建成功');
      }

      // Parse and save models if model_ids provided
      if (model_ids && typeof model_ids === 'string' && model_ids.trim()) {
        const modelIdList = model_ids.split('/').map((id: string) => id.trim()).filter((id: string) => id);

        for (const modelId of modelIdList) {
          try {
            await providerApi.createModel?.(providerId, {
              model_id: modelId,
              name: modelId, // Use model_id as name by default
              context_window: 4096,
              input_price_per_1k: 0,
              output_price_per_1k: 0,
              is_active: true,
            });
          } catch (error) {
            console.error(`Failed to save model ${modelId}:`, error);
          }
        }
      }

      setModalVisible(false);
      await fetchProviders();
    } catch (error: any) {
      // Extract error details from response
      let errorMessage = '保存失败';
      let suggestion = '请检查输入信息是否正确';

      if (error?.response?.data?.detail) {
        const detail = error.response.data.detail;
        errorMessage = detail;

        // Provide specific suggestions based on error type
        if (detail.includes('duplicate key') || detail.includes('already exists')) {
          suggestion = '供应商名称可能已存在，请更换名称后重试';
        } else if (detail.includes('foreign key') || detail.includes('constraint')) {
          suggestion = '数据关联错误，请联系管理员检查数据库配置';
        } else if (detail.includes('validation') || detail.includes('required')) {
          suggestion = '请填写所有必填项，确保格式正确';
        } else if (detail.includes('connection') || detail.includes('timeout')) {
          suggestion = '网络连接失败，请检查网络或稍后重试';
        } else if (detail.includes('authentication') || detail.includes('unauthorized')) {
          suggestion = '权限验证失败，请检查管理员 API Key 是否正确';
        }
      } else if (error?.message) {
        errorMessage = error.message;
        if (error.message.includes('Network Error')) {
          suggestion = '无法连接到服务器，请检查网络连接';
        } else if (error.message.includes('timeout')) {
          suggestion = '请求超时，请稍后重试';
        }
      }

      message.error({
        content: (
          <div>
            <div>{errorMessage}</div>
            <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
              {suggestion}
            </div>
          </div>
        ),
        duration: 5,
      });
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
      title: '供应商名称',
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
      title: 'Base URL',
      dataIndex: 'base_url',
      key: 'base_url',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const { color, text } = getStatusTag(status);
        return <Tag color={color}>{text}</Tag>;
      },
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
      title: '模型列表',
      key: 'models',
      width: 200,
      ellipsis: true,
      render: (_: any, record: Provider) => {
        const models = providerModels[record.id] || [];
        if (models.length === 0) {
          return <span style={{ color: '#999' }}>-</span>;
        }
        const modelNames = models.map(m => m.name || m.model_id).join(' / ');
        return <span title={modelNames}>{modelNames}</span>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 230,
      render: (_: any, record: Provider) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<CheckCircleOutlined />}
            loading={verifyingIds[record.id]}
            onClick={() => handleVerify(record.id, record.name)}
          >
            验证
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个模型供应商吗？"
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
    const models = providerModels[record.id] || [];

    return (
      <div style={{ padding: '16px' }}>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Statistic
              title="连接延迟"
              value={health?.latency_ms || '-'}
              suffix="ms"
              valueStyle={{ color: health?.is_healthy ? '#3f8600' : '#cf1322' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="支持模型"
              value={models.length}
              suffix="个"
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={8}>
            <div style={detailStyle}>
              <p>Base URL: {record.base_url}</p>
              <p>超时: {record.timeout}s | 重试: {record.max_retries}次</p>
            </div>
          </Col>
        </Row>

        {models.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <div style={{
              fontSize: 13,
              color: '#8c8c8c',
              marginBottom: '12px',
              fontWeight: 500
            }}>
              支持的模型：
            </div>
            <Table
              columns={[
                {
                  title: '模型ID',
                  dataIndex: 'model_id',
                  key: 'model_id',
                  width: 200,
                  ellipsis: true,
                },
                {
                  title: '模型名称',
                  dataIndex: 'name',
                  key: 'name',
                  ellipsis: true,
                },
                {
                  title: '上下文窗口',
                  dataIndex: 'context_window',
                  key: 'context_window',
                  width: 100,
                  render: (tokens: number) => `${(tokens / 1024).toFixed(1)}K`,
                },
                {
                  title: '输入价格',
                  dataIndex: 'input_price_per_1k',
                  key: 'input_price',
                  width: 100,
                  render: (price: number) => `$${price}`,
                },
                {
                  title: '输出价格',
                  dataIndex: 'output_price_per_1k',
                  key: 'output_price',
                  width: 100,
                  render: (price: number) => `$${price}`,
                },
                {
                  title: '状态',
                  dataIndex: 'is_active',
                  key: 'is_active',
                  width: 80,
                  render: (active: boolean) => (
                    <Tag color={active ? 'green' : 'default'}>
                      {active ? '启用' : '禁用'}
                    </Tag>
                  ),
                },
              ]}
              dataSource={models}
              rowKey="model_id"
              pagination={false}
              size="small"
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <Title level={2}>模型供应商</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleAdd}
        >
          添加模型供应商
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

      <Card style={{ marginTop: '24px' }} title="模型列表汇总">
        <Table
          columns={[
            {
              title: '供应商',
              dataIndex: 'providerName',
              key: 'providerName',
              width: 150,
            },
            {
              title: '模型ID',
              dataIndex: 'model_id',
              key: 'model_id',
              width: 200,
              ellipsis: true,
            },
            {
              title: '模型名称',
              dataIndex: 'name',
              key: 'name',
              ellipsis: true,
            },
            {
              title: '上下文窗口',
              dataIndex: 'context_window',
              key: 'context_window',
              width: 120,
              render: (tokens: number) => `${(tokens / 1024).toFixed(1)}K`,
            },
            {
              title: '输入价格',
              dataIndex: 'input_price_per_1k',
              key: 'input_price',
              width: 100,
              render: (price: number) => `$${price}`,
            },
            {
              title: '输出价格',
              dataIndex: 'output_price_per_1k',
              key: 'output_price',
              width: 100,
              render: (price: number) => `$${price}`,
            },
            {
              title: '状态',
              dataIndex: 'is_active',
              key: 'is_active',
              width: 80,
              render: (active: boolean) => (
                <Tag color={active ? 'green' : 'default'}>
                  {active ? '启用' : '禁用'}
                </Tag>
              ),
            },
          ]}
          dataSource={Object.entries(providerModels).flatMap(([providerId, models]) =>
            models.map(m => ({
              ...m,
              providerName: providers.find(p => p.id === Number(providerId))?.name || '-',
            }))
          )}
          rowKey={(record) => `${record.providerName}-${record.model_id}`}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个模型`,
          }}
        />
      </Card>

      <Modal
        title={editingProvider?.id ? '编辑模型供应商' : '添加模型供应商'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="供应商名称"
            rules={[{ required: true, message: '请输入供应商名称' }]}
          >
            <Input placeholder="例如: openai" />
          </Form.Item>

          <Form.Item
            name="provider_type"
            label="类型"
            rules={[{ required: true, message: '请选择供应商类型' }]}
          >
            <Select style={{ width: '100%' }}>
              <Select.Option value="openai">OpenAI</Select.Option>
              <Select.Option value="anthropic">Anthropic</Select.Option>
              <Select.Option value="custom">Custom</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={editingProvider?.id ? [] : [{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password placeholder={editingProvider?.id ? "留空则不更新" : "请输入 API Key"} />
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
            name="model_ids"
            label="支持的模型"
            rules={[{ required: true, message: '请输入支持的模型' }]}
          >
            <Input placeholder="例如: gpt-3.5-turbo / gpt-4 / gpt-4-turbo" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
