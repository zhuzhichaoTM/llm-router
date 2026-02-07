import React, { useState, useEffect } from 'react';
import { Card, Tabs, Typography, Code, Button, Alert } from 'antd';
import { CopyOutlined, ApiOutlined } from '@ant-design/icons';
import type { ModelInfo } from '@/types';
import { chatApi } from '@/api/client';

const { Title, Paragraph, Text } = Typography;

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
    <div className="p-6">
      <Title level={1} className="mb-6">API 文档</Title>

      <Alert
        message="在开始使用 API 之前，请先设置您的 API Key"
        type="info"
        showIcon
        className="mb-6"
      />

      <Card title="可用模型" className="mb-6" loading={loading}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((model) => (
            <Card
              key={model.id}
              size="small"
              className="hover:shadow-md transition-shadow"
              title={
                <div>
                  <div className="font-medium">{model.name}</div>
                  <div className="text-sm text-gray-500">{model.provider}</div>
                </div>
              }
            >
              <div className="space-y-2">
                <div>
                  <Text type="secondary">Context Window:</Text>
                  <Text strong>{model.context_window.toLocaleString()}</Text>
                </div>
                <div>
                  <Text type="secondary">Input Price:</Text>
                  <Text strong>${model.input_price_per_1k}/1K tokens</Text>
                </div>
                <div>
                  <Text type="secondary">Output Price:</Text>
                  <Text strong>${model.output_price_per_1k}/1K tokens</Text>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      <Card title="API 端点" className="mb-6">
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
                  className="mb-2"
                >
                  <div className="flex items-center gap-4 mb-2">
                    <Text code className="!bg-blue-100 text-blue-800">
                      {endpoint.method}
                    </Text>
                    <Text strong className="text-lg">{endpoint.path}</Text>
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
                  <Code language="bash" className="mb-4">pip install axios</Code>

                  <Title level={5}>发送聊天请求</Title>
                  <Code language="python" className="mb-4">{`import asyncio
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
`}</Code>
                </div>
              ),
            },
            {
              key: 'javascript',
              label: 'JavaScript 示例',
              children: (
                <div>
                  <Title level={5}>发送聊天请求</Title>
                  <Code language="javascript" className="mb-4">{`import axios from 'axios';

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
`}</Code>
                </div>
              ),
            },
            {
              key: 'curl',
              label: 'cURL 示例',
              children: (
                <div>
                  <Title level={5}>发送聊天请求</Title>
                  <div className="mb-4">
                    <Code language="bash" className="mb-2">{`curl -X POST http://localhost:8000/api/v1/chat/completions \\\
  -H "Authorization: Bearer YOUR_API_KEY" \\\
  -H "Content-Type: application/json" \\\
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`}</Code>
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

      <Card title="错误码说明" className="mb-6">
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-left p-3 border-b">状态码</th>
              <th className="text-left p-3 border-b">说明</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="p-3"><Text code>200</Text></td>
              <td className="p-3">请求成功</td>
            </tr>
            <tr>
              <td className="p-3"><Text code>400</Text></td>
              <td className="p-3">请求参数错误</td>
            </tr>
            <tr>
              <td className="p-3"><Text code>401</Text></td>
              <td className="p-3">API Key 无效或未提供</td>
            </tr>
            <tr>
              <td className="p-3"><Text code>403</Text></td>
              <td className="p-3">无权限（需要管理员 API Key）</td>
            </tr>
            <tr>
              <td className="p-3"><Text code>429</Text></td>
              <td className="p-3">请求过于频繁，请稍后重试</td>
            </tr>
            <tr>
              <td className="p-3"><Text code>500</Text></td>
              <td className="p-3">服务器内部错误</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
}
