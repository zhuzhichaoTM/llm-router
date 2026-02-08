import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Steps, Input, Button, Form, message, Typography, Alert, Row, Col } from 'antd';
import { CheckCircleOutlined, KeyOutlined, RocketOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useConfig } from '@/hooks/useConfig';

const { Title, Paragraph, Text } = Typography;

export default function QuickStart() {
  console.log('QuickStart: Component rendering START');

  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const { setApiKey: saveApiKey } = useConfig();
  const navigate = useNavigate();

  console.log('QuickStart: State initialized, currentStep =', currentStep);

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
    {
      title: '完成',
      icon: <CheckCircleOutlined />,
      description: '开始使用 LLM Router',
    },
  ];

  const handleSaveApiKey = async () => {
    const values = await form.validateFields();
    if (values.apiKey) {
      saveApiKey(values.apiKey);
      setCurrentStep(1);
      message.success('API Key 已保存');
    }
  };

  const handleNextStep = () => {
    setCurrentStep(currentStep + 1);
  };

  const containerStyle: React.CSSProperties = {
    maxWidth: '900px',
    margin: '0 auto',
  };

  const codeStyle: React.CSSProperties = {
    background: '#f5f5f5',
    padding: '16px',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '14px',
    overflow: 'auto',
  };

  const centerStyle: React.CSSProperties = {
    textAlign: 'center',
    padding: '40px 0',
  };

  const iconStyle: React.CSSProperties = {
    fontSize: '64px',
    color: '#52c41a',
    marginBottom: '24px',
  };

  const jsCode = `import axios from 'axios';

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
});`;

  const curlCode = `curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`;

  return (
    <div style={containerStyle}>
      <Title level={1} style={{ textAlign: 'center', marginBottom: '32px' }}>快速开始</Title>

      <Steps current={currentStep} style={{ marginBottom: '32px' }}>
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
            style={{ marginBottom: '16px' }}
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

          <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
            <Col xs={24} md={12}>
              <Card
                type="inner"
                title="开发环境"
                extra={<Button type="link">查看文档</Button>}
              >
                <ul style={{ paddingLeft: '20px', margin: 0 }}>
                  <li style={{ marginBottom: '8px' }}>Base URL: <Text code>http://localhost:8000</Text></li>
                  <li style={{ marginBottom: '8px' }}>支持 CORS</li>
                  <li>实时日志</li>
                </ul>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card
                type="inner"
                title="生产环境"
                extra={<Button type="link">查看文档</Button>}
              >
                <ul style={{ paddingLeft: '20px', margin: 0 }}>
                  <li style={{ marginBottom: '8px' }}>Base URL: <Text code>https://your-domain.com</Text></li>
                  <li style={{ marginBottom: '8px' }}>HTTPS 支持</li>
                  <li style={{ marginBottom: '8px' }}>负载均衡</li>
                  <li>自动重试</li>
                </ul>
              </Card>
            </Col>
          </Row>

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

          <Card style={{ marginBottom: '16px' }} title="JavaScript">
            <div style={codeStyle}>{jsCode}</div>
          </Card>

          <Card style={{ marginBottom: '16px' }} title="cURL">
            <div style={codeStyle}>{curlCode}</div>
          </Card>

          <Button
            type="primary"
            size="large"
            block
            icon={<ArrowRightOutlined />}
            onClick={handleNextStep}
            style={{ marginBottom: '16px' }}
          >
            完成
          </Button>

          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <Button
              type="primary"
              size="large"
              onClick={() => navigate('/api-docs')}
            >
              查看完整 API 文档
            </Button>
          </div>
        </Card>
      )}

      {currentStep === 3 && (
        <Card>
          <div style={centerStyle}>
            <CheckCircleOutlined style={iconStyle} />
            <Title level={2}>恭喜！</Title>
            <Paragraph style={{ fontSize: '18px' }}>
              您已完成快速开始向导。现在可以开始使用 LLM Router 了。
            </Paragraph>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '24px' }}>
              <Button
                type="primary"
                size="large"
                onClick={() => navigate('/api-docs')}
              >
                查看 API 文档
              </Button>
              <Button
                size="large"
                onClick={() => navigate('/dashboard')}
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
