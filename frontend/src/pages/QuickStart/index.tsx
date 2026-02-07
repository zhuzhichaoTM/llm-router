import React, { useState, useEffect } from 'react';
import { Card, Steps, Input, Button, Form, message, Typography, Alert } from 'antd';
import { CheckCircleOutlined, KeyOutlined, RocketOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { setApiKey } from '@/api/client';

const { Title, Paragraph, Text } = Typography;

export default function QuickStart() {
  const [apiKey, setApiKeyInput] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  const steps = [
    {
      title: '获取 API Key',
      icon: <KeyOutlined />,
      description: '在管理控制台中创建或获取您的 API Key',
    },
    {
      title: '配置环境',
      icon: <RocketOutlined />,
      description: '配置您的开发环境或生产环境',
    },
    {
      title: '发送请求',
      icon: <CheckCircleOutlined />,
      description: '使用 API Key 发送您的第一个请求',
    },
  ];

  const handleSaveApiKey = async () => {
    const values = await form.validateFields();
    if (values.apiKey) {
      setApiKey(values.apiKey);
      setCurrentStep(1);
      message.success('API Key 已保存');
    }
  };

  const handleNextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const isStepComplete = (stepIndex: number) => {
    return stepIndex < currentStep;
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Title level={1} className="text-center mb-8">快速开始</Title>

      <Steps current={currentStep} className="mb-8">
        {steps.map((step, index) => (
          <Steps.Step
            key={index}
            title={step.title}
            description={step.description}
            icon={step.icon}
            status={index < currentStep ? 'finish' : index === currentStep ? 'process' : 'wait'}
          />
        ))}
      </Steps>

      {currentStep === 0 && (
        <Card>
          <Title level={3}>步骤 1: 设置 API Key</Title>
          <Paragraph type="secondary">
            输入您的 API Key 来开始使用 LLM Router。如果您还没有 API Key，
            请联系管理员获取。
          </Paragraph>

          <Alert
            message="API Key 将保存在本地浏览器中，请勿在公共设备上使用"
            type="warning"
            showIcon
            className="mb-4"
          />

          <Form form={form} layout="vertical" onFinish={handleSaveApiKey}>
            <Form.Item
              name="apiKey"
              label="API Key"
              rules={[{ required: true, message: '请输入 API Key' }]}
            >
              <Input.Password
                placeholder="llm_xxxxxxxxxxxxxxxxxx"
                prefix={<KeyOutlined />}
                size="large"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                icon={<ArrowRightOutlined />}
              >
                继续
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {currentStep === 1 && (
        <Card>
          <Title level={3}>步骤 2: 配置环境</Title>
          <Paragraph type="secondary">
            根据您的使用场景选择合适的配置。
          </Paragraph>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <Card
              type="inner"
              title="开发环境"
              extra={<Button type="link">查看文档</Button>}
            >
              <ul className="space-y-2">
                <li>Base URL: <Text code>http://localhost:8000</Text></li>
                <li>支持 CORS</li>
                <li>实时日志</li>
              </ul>
            </Card>
            <Card
              type="inner"
              title="生产环境"
              extra={<Button type="link">查看文档</Button>}
            >
              <ul className="space-y-2">
                <li>Base URL: <Text code>https://your-domain.com</Text></li>
                <li>HTTPS 支持</li>
                <li>负载均衡</li>
                <li>自动重试</li>
              </ul>
            </Card>
          </div>

          <Button
            type="primary"
            size="large"
            block
            icon={<ArrowRightOutlined />}
            onClick={handleNextStep}
          >
            下一步
          </Button>
        </Card>
      )}

      {currentStep === 2 && (
        <Card>
          <Title level={3}>步骤 3: 发送请求</Title>
          <Paragraph type="secondary">
            您现在可以使用 API 发送请求了。以下是快速开始示例。
          </Paragraph>

          <div className="space-y-4">
            <Card
              type="inner"
              title="JavaScript"
            >
              <Code language="javascript" className="mb-2">{`import axios from 'axios';

const API_KEY = 'YOUR_API_KEY';

axios.post('http://localhost:8000/api/v1/chat/completions', {
  model: 'gpt-3.5-turbo',
  messages: [
    { role: 'user', content: 'Hello!' }
  ]
}, {
  headers: {
    'Authorization': \`Bearer \${API_KEY}\`
  }
}).then(response => {
  console.log(response.data);
}).catch(error => {
  console.error(error);
});`}</Code>
            </Card>

            <Card
              type="inner"
              title="cURL"
            >
              <Code language="bash">{`curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`}</Code>
            </Card>
          </div>

          <div className="text-center mt-6">
            <Button
              type="primary"
              size="large"
              onClick={() => window.location.href = '/api-docs'}
            >
              查看完整 API 文档
            </Button>
          </div>
        </Card>
      )}

      {currentStep === 3 && (
        <Card>
          <div className="text-center py-8">
            <div className="mb-4">
              <CheckCircleOutlined className="text-6xl text-green-500" />
            </div>
            <Title level={2}>恭喜！</Title>
            <Paragraph className="text-lg">
              您已完成快速开始向导。现在可以开始使用 LLM Router 了。
            </Paragraph>

            <div className="flex justify-center gap-4 mt-6">
              <Button
                type="primary"
                size="large"
                onClick={() => window.location.href = '/api-docs'}
              >
                查看 API 文档
              </Button>
              <Button
                size="large"
                onClick={() => window.location.href = '/dashboard'}
              >
                进入仪表盘
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
