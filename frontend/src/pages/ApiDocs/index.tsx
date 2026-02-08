import React, { useState, useEffect } from 'react';
import { Card, Tabs, Typography, Button, Alert, Row, Col } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import type { ModelInfo } from '@/types';
import { chatApi } from '@/api/client';

const { Title, Paragraph, Text } = Typography;

const codeBlockStyle: React.CSSProperties = {
  background: '#f5f5f5',
  padding: '12px',
  borderRadius: '4px',
  fontFamily: 'monospace',
  fontSize: '13px',
  whiteSpace: 'pre-wrap',
  overflow: 'auto',
  marginBottom: '16px',
};

const containerStyle: React.CSSProperties = {
  padding: '24px',
};

export default function ApiDocs() {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const data = await chatApi.listModels();
      if (data) {
        setModels(data);
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(''), 2000);
  };

  const apiEndpoints = [
    {
      method: 'POST',
      path: '/api/v1/chat/completions',
      description: '聊天完成接口，用于发送对话请求到 LLM 模型',
    },
    {
      method: 'GET',
      path: '/api/v1/chat/models',
      description: '获取所有可用的模型列表',
    },
    {
      method: 'POST',
      path: '/api/v1/router/toggle',
      description: '切换智能路由开关（需要管理员权限）',
    },
    {
      method: 'GET',
      path: '/api/v1/router/status',
      description: '获取当前路由开关状态',
    },
    {
      method: 'GET',
      path: '/api/v1/cost/current',
      description: '获取当前实时成本统计',
    },
    {
      method: 'GET',
      path: '/api/v1/cost/daily',
      description: '获取每日成本统计数据',
    },
  ];

  return (
    <div style={containerStyle}>
      <Title level={1} style={{ marginBottom: '24px' }}>API 文档</Title>

      <Alert
        message="在开始使用 API 之前，请先设置您的 API Key"
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Card title="可用模型" style={{ marginBottom: '24px' }} loading={loading}>
        <Row gutter={[16, 16]}>
          {models.map((model) => (
            <Col xs={24} sm={12} lg={8} key={model.id}>
              <Card
                size="small"
                title={
                  <div>
                    <div style={{ fontWeight: 500 }}>{model.name}</div>
                    <div style={{ fontSize: '12px', color: '#999' }}>{model.provider}</div>
                  </div>
                }
              >
                <div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text type="secondary">Context Window:</Text>
                    <Text strong> {model.context_window.toLocaleString()}</Text>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text type="secondary">Input Price:</Text>
                    <Text strong> ${model.input_price_per_1k}/1K tokens</Text>
                  </div>
                  <div>
                    <Text type="secondary">Output Price:</Text>
                    <Text strong> ${model.output_price_per_1k}/1K tokens</Text>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      <Card title="API 端点" style={{ marginBottom: '24px' }}>
        <Tabs
          defaultActiveKey="endpoints"
          items={[
            {
              key: 'endpoints',
              label: '端点列表',
              children: apiEndpoints.map((endpoint, index) => (
                <Card
                  key={index}
                  size="small"
                  style={{ marginBottom: '8px' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                    <Text code style={{ background: '#e6f7ff', color: '#1890ff' }}>
                      {endpoint.method}
                    </Text>
                    <Text strong style={{ fontSize: '16px' }}>{endpoint.path}</Text>
                  </div>
                  <Paragraph type="secondary">{endpoint.description}</Paragraph>
                </Card>
              )),
            },
            {
              key: 'python',
              label: 'Python 示例',
              children: (
                <div>
                  <Title level={5}>安装依赖</Title>
                  <div style={codeBlockStyle}>pip install aiohttp</div>

                  <Title level={5}>发送聊天请求</Title>
                  <div style={codeBlockStyle}>{`import asyncio
import aiohttp

async def chat_completion():
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": "Bearer YOUR_API_KEY",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        }

        async with session.post(
            "http://localhost:8000/api/v1/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            data = await response.json()
            print("Response:", data)

asyncio.run(chat_completion())
`}</div>
                </div>
              ),
            },
            {
              key: 'javascript',
              label: 'JavaScript 示例',
              children: (
                <div>
                  <Title level={5}>发送聊天请求</Title>
                  <div style={codeBlockStyle}>{`import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

async function chatCompletion() {
    try {
        const response = await axios.post(
            \`\${API_BASE_URL}/api/v1/chat/completions\`,
            {
                model: 'gpt-3.5-turbo',
                messages: [
                    { role: 'user', content: 'Hello!' }
                ]
            },
            {
                headers: {
                    'Authorization': 'Bearer YOUR_API_KEY',
                    'Content-Type': 'application/json'
                }
            }
        );

        console.log('Response:', response.data);
    } catch (error) {
        console.error('Error:', error);
    }
}

chatCompletion();
`}</div>
                </div>
              ),
            },
            {
              key: 'curl',
              label: 'cURL 示例',
              children: (
                <div>
                  <Title level={5}>发送聊天请求</Title>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={codeBlockStyle}>{`curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`}</div>
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => copyToClipboard('curl -X POST http://localhost:8000/api/v1/chat/completions \\  -H "Authorization: Bearer YOUR_API_KEY" \\  -H "Content-Type: application/json" \\  -d \'{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello!"}]}\'')}
                    >
                      {copied === '...' ? '已复制' : '复制'}
                    </Button>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Card title="错误码说明" style={{ marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '12px', borderBottom: '1px solid #f0f0f0' }}>状态码</th>
              <th style={{ textAlign: 'left', padding: '12px', borderBottom: '1px solid #f0f0f0' }}>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ padding: '12px' }}><Text code>200</Text></td>
              <td style={{ padding: '12px' }}>请求成功</td>
            </tr>
            <tr>
              <td style={{ padding: '12px' }}><Text code>400</Text></td>
              <td style={{ padding: '12px' }}>请求参数错误</td>
            </tr>
            <tr>
              <td style={{ padding: '12px' }}><Text code>401</Text></td>
              <td style={{ padding: '12px' }}>API Key 无效或未提供</td>
            </tr>
            <tr>
              <td style={{ padding: '12px' }}><Text code>403</Text></td>
              <td style={{ padding: '12px' }}>无权限（需要管理员 API Key）</td>
            </tr>
            <tr>
              <td style={{ padding: '12px' }}><Text code>429</Text></td>
              <td style={{ padding: '12px' }}>请求过于频繁，请稍后重试</td>
            </tr>
            <tr>
              <td style={{ padding: '12px' }}><Text code>500</Text></td>
              <td style={{ padding: '12px' }}>服务器内部错误</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
}
